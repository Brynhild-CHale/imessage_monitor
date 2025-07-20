"""Real-time monitoring strategies for iMessage database changes."""

import asyncio
import queue
import time
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Dict, Any, Optional
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler, FileSystemEvent


class RealtimeStrategy(ABC):
    """Abstract base class for real-time monitoring strategies."""
    
    @abstractmethod
    def start(self, db_path: str, callback: Callable[[], None]) -> bool:
        """Start real-time monitoring.
        
        Args:
            db_path: Path to the Messages database
            callback: Function to call when database changes are detected
            
        Returns:
            True if started successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """Stop real-time monitoring."""
        pass
    
    @abstractmethod
    def is_active(self) -> bool:
        """Check if real-time monitoring is active."""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        pass


class QueueBasedMessageWatcher(FileSystemEventHandler):
    """Thread-safe file system event handler using a queue for communication."""
    
    def __init__(self, message_queue: queue.Queue, name: str = "QueueWatcher"):
        """Initialize the watcher with a message queue.
        
        Args:
            message_queue: Thread-safe queue for communicating with main loop
            name: Name for this watcher instance (for logging)
        """
        super().__init__()
        self.message_queue = message_queue
        self.name = name
        self._last_modification_time = 0
        self._debounce_interval = 0.1  # 100ms debounce to avoid duplicate events
        self._event_count = 0
        self._queue_puts = 0
        self._start_time = time.time()
    
    def on_any_event(self, event: FileSystemEvent):
        """Process all file system events."""
        self._event_count += 1
        
        # Process all event types for database files, not just 'modified'
        if not event.is_directory:
            self._check_database_file_event(event)
    
    def _check_database_file_event(self, event: FileSystemEvent):
        """Check if this event is for a database file and process it."""
        file_path = str(event.src_path)
        file_name = Path(file_path).name
        
        # Check if this is a Messages database related file
        db_files = ['chat.db', 'chat.db-wal', 'chat.db-shm', 'chat.db-journal']
        is_db_file = any(file_name == db_file for db_file in db_files)
        
        if is_db_file:
            current_time = time.time()
            time_since_last = current_time - self._last_modification_time
            
            # Debounce rapid consecutive events
            if time_since_last >= self._debounce_interval:
                self._last_modification_time = current_time
                self._queue_puts += 1
                
                try:
                    # Put event in queue with timestamp - this is thread-safe
                    event_data = {
                        'timestamp': current_time,
                        'file_name': file_name,
                        'event_type': event.event_type,
                        'event_id': self._queue_puts
                    }
                    self.message_queue.put_nowait(event_data)
                    
                except queue.Full:
                    # Queue is full, silently drop event to prevent blocking
                    pass
                except Exception:
                    # Other queue errors, silently handle to prevent crashes
                    pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get debugging statistics."""
        runtime = time.time() - self._start_time
        return {
            'name': self.name,
            'runtime_seconds': runtime,
            'total_events': self._event_count,
            'queue_puts': self._queue_puts,
            'events_per_second': self._event_count / runtime if runtime > 0 else 0,
            'queue_puts_per_second': self._queue_puts / runtime if runtime > 0 else 0
        }


class QueueBasedRealtimeStrategy(RealtimeStrategy):
    """Queue-based real-time monitoring strategy."""
    
    def __init__(self):
        """Initialize the queue-based strategy."""
        self.observer: Optional[PollingObserver] = None
        self.watcher: Optional[QueueBasedMessageWatcher] = None
        self.message_queue: Optional[queue.Queue] = None
        self._queue_processor_task: Optional[asyncio.Task] = None
        self._is_running = False
        self._callback: Optional[Callable[[], None]] = None
        self._queue_events_processed = 0
    
    def start(self, db_path: str, callback: Callable[[], None]) -> bool:
        """Start queue-based real-time monitoring.
        
        Args:
            db_path: Path to the Messages database
            callback: Function to call when database changes are detected
            
        Returns:
            True if started successfully, False otherwise
        """
        if self.observer:
            return False  # Already running
        
        try:
            # Set up queue and callback
            self.message_queue = queue.Queue(maxsize=100)  # Prevent memory issues
            self._callback = callback
            
            # Set up file watching
            db_path_obj = Path(db_path)
            watch_directory = db_path_obj.parent
            
            if not watch_directory.exists():
                return False
            
            # Create watcher and PollingObserver for reliable SQLite detection
            self.watcher = QueueBasedMessageWatcher(self.message_queue, "RealtimeQueue")
            self.observer = PollingObserver(timeout=0.1)  # Poll every 100ms
            self.observer.schedule(self.watcher, str(watch_directory), recursive=False)
            self.observer.start()
            
            # Start queue processor
            self._is_running = True
            self._queue_processor_task = asyncio.create_task(self._queue_processor())
            
            print(f"📁 PollingObserver started for {watch_directory}")
            print(f"   Polling interval: 100ms (stat-based detection)")
            print(f"🔄 Queue processor task started")
            return True
            
        except Exception as e:
            print(f"Failed to start real-time monitoring: {e}")
            self.stop()
            return False
    
    def stop(self) -> None:
        """Stop queue-based real-time monitoring."""
        # Stop the running flag first
        self._is_running = False
        
        # Stop queue processor
        if self._queue_processor_task:
            self._queue_processor_task.cancel()
            self._queue_processor_task = None
        
        # Stop file observer
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5)
            self.observer = None
        
        # Clear queue
        if self.message_queue:
            while not self.message_queue.empty():
                try:
                    self.message_queue.get_nowait()
                    self.message_queue.task_done()
                except queue.Empty:
                    break
            self.message_queue = None
        
        self.watcher = None
        self._callback = None
    
    def is_active(self) -> bool:
        """Check if real-time monitoring is active."""
        return (self.observer is not None and 
                self.observer.is_alive() if self.observer else False)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        stats = {
            'strategy': 'queue_based',
            'is_active': self.is_active(),
            'queue_events_processed': self._queue_events_processed,
            'queue_size': self.message_queue.qsize() if self.message_queue else 0
        }
        
        if self.watcher:
            watcher_stats = self.watcher.get_stats()
            stats.update(watcher_stats)
        
        return stats
    
    async def _queue_processor(self):
        """Process database change events from the queue in the main async loop."""
        print(f"🔄 Queue processor started - waiting for events...")
        while self._is_running:
            try:
                # Non-blocking check for queue items
                event_data = self.message_queue.get_nowait()
                
                self._queue_events_processed += 1
                print(f"🔔 Real-time event #{self._queue_events_processed}: {event_data['file_name']} ({event_data['event_type']})")
                
                # Call the callback function immediately
                if self._callback:
                    try:
                        await self._callback()
                        print(f"✅ Real-time callback completed")
                    except Exception as e:
                        print(f"❌ Error in real-time callback: {e}")
                
                # Mark queue task as done
                self.message_queue.task_done()
                
            except queue.Empty:
                # No items in queue, sleep briefly and continue
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"❌ Error processing real-time queue: {e}")
                await asyncio.sleep(0.1)


class RealtimeMonitor:
    """Manager for real-time monitoring with backup polling support."""
    
    def __init__(self):
        """Initialize the real-time monitor."""
        self.strategy: Optional[RealtimeStrategy] = None
        self._backup_polling_used = False
    
    def start(self, db_path: str, callback: Callable[[], None]) -> bool:
        """Start real-time monitoring (primary method) with polling as backup.
        
        Args:
            db_path: Path to the Messages database
            callback: Async function to call when database changes are detected
            
        Returns:
            True if real-time monitoring started successfully, False if fallback to polling needed
        """
        if self.strategy:
            return False  # Already running
        
        # Try queue-based strategy first (this is the PRIMARY method)
        queue_strategy = QueueBasedRealtimeStrategy()
        if queue_strategy.start(db_path, callback):
            self.strategy = queue_strategy
            return True
        
        # If real-time fails, caller should fall back to polling-only mode
        return False
    
    def stop(self) -> None:
        """Stop real-time monitoring."""
        if self.strategy:
            self.strategy.stop()
            self.strategy = None
        self._backup_polling_used = False
    
    def is_active(self) -> bool:
        """Check if real-time monitoring is active (primary method working)."""
        return self.strategy is not None and self.strategy.is_active()
    
    def mark_backup_polling_used(self) -> None:
        """Mark that backup polling caught messages the real-time system missed."""
        if not self._backup_polling_used:
            print("⚠️  Backup polling caught message(s) - file watcher may have missed them")
            self._backup_polling_used = True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        if self.strategy:
            stats = self.strategy.get_stats()
            stats['backup_polling_used'] = self._backup_polling_used
            return stats
        
        return {
            'strategy': 'none',
            'is_active': False,
            'backup_polling_used': self._backup_polling_used
        }