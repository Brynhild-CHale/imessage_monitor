#!/usr/bin/env python3
"""
Real-time file watcher debugging test script.
This script tests file watching capabilities for the Messages database
using a thread-safe queue approach for reliable event detection.
"""

import asyncio
import sqlite3
import time
import threading
import queue
from datetime import datetime
from pathlib import Path
from typing import Callable
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler, FileSystemEvent


class DebugMessageDatabaseWatcher(FileSystemEventHandler):
    """Enhanced file system event handler with thread-safe queue communication."""
    
    def __init__(self, message_queue: queue.Queue, name: str = "FileWatcher"):
        """Initialize the watcher with a message queue for thread-safe communication.
        
        Args:
            message_queue: Thread-safe queue for communicating with main loop
            name: Name for this watcher instance (for logging)
        """
        super().__init__()
        self.message_queue = message_queue
        self.name = name
        self._last_modification_time = 0
        self._debounce_interval = 0.1  # Reduced debounce for better responsiveness
        self._event_count = 0
        self._queue_puts = 0
        self._start_time = time.time()
        
        print(f"🔧 [{self.name}] Watcher initialized")
        print(f"   Debounce interval: {self._debounce_interval}s")
        print(f"   Thread: {threading.current_thread().name}")
        print(f"   Queue-based communication: ✅")
    
    def on_any_event(self, event):
        """Log all file system events for debugging."""
        self._event_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        event_type = event.event_type
        is_dir = "DIR" if event.is_directory else "FILE"
        path = event.src_path
        
        print(f"📁 [{timestamp}] {event_type.upper()} {is_dir}: {path}")
        
        # Process ALL event types for database files, not just 'modified'
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
            
            print(f"💾 [{self.name}] DB file {event.event_type}: {file_name}")
            print(f"   Time since last: {time_since_last:.3f}s")
            print(f"   Debounce threshold: {self._debounce_interval}s")
            
            # Check file size for additional validation
            try:
                file_size = Path(file_path).stat().st_size if Path(file_path).exists() else 0
                print(f"   File size: {file_size} bytes")
            except Exception as e:
                print(f"   File size check failed: {e}")
            
            # Debounce rapid consecutive events
            if time_since_last >= self._debounce_interval:
                self._last_modification_time = current_time
                self._queue_puts += 1
                
                print(f"🚀 [{self.name}] Queuing database change event #{self._queue_puts}")
                print(f"   Event type: {event.event_type}")
                print(f"   Thread: {threading.current_thread().name}")
                
                try:
                    # Put event in queue with timestamp - this is thread-safe
                    event_data = {
                        'timestamp': current_time,
                        'file_name': file_name,
                        'event_type': event.event_type,
                        'event_id': self._queue_puts
                    }
                    self.message_queue.put_nowait(event_data)
                    print(f"✅ [{self.name}] Event queued successfully")
                    
                except queue.Full:
                    print(f"⚠️ [{self.name}] Queue is full, dropping event")
                except Exception as e:
                    print(f"❌ [{self.name}] Queue error: {e}")
            else:
                print(f"⏸️ [{self.name}] Event debounced (too soon)")

    def on_modified(self, event: FileSystemEvent):
        """Handle file modification events - now handled by _check_database_file_event."""
        pass  # All processing moved to _check_database_file_event
    
    def on_created(self, event: FileSystemEvent):
        """Handle file creation events."""
        pass  # All processing moved to _check_database_file_event
    
    def on_deleted(self, event: FileSystemEvent):
        """Handle file deletion events."""
        pass  # All processing moved to _check_database_file_event
    
    def on_moved(self, event: FileSystemEvent):
        """Handle file move events."""
        pass  # All processing moved to _check_database_file_event
    
    def get_stats(self):
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


class RealTimeTest:
    """Test harness for real-time message monitoring using thread-safe queue approach."""
    
    def __init__(self):
        self.db_path = Path.home() / "Library" / "Messages" / "chat.db"
        self.watch_directory = self.db_path.parent
        self.observer = None
        self.watcher = None
        self.last_message_id = 0
        self.message_count = 0
        self.callback_events_count = 0
        self.message_queue = queue.Queue(maxsize=100)  # Prevent memory issues
        self._is_running = False
        self._queue_processor_task = None
        
        print("🧪 RealTime Test Initialized (Version 4 - Enhanced File Detection)")
        print(f"   Database path: {self.db_path}")
        print(f"   Watch directory: {self.watch_directory}")
        print(f"   Database exists: {self.db_path.exists()}")
        print(f"   Watch dir exists: {self.watch_directory.exists()}")
        print(f"   Queue max size: {self.message_queue.maxsize}")
        
        # Test permissions
        self._test_permissions()
    
    def _test_permissions(self):
        """Test various permission levels."""
        print("\n🔐 Testing Permissions:")
        
        # Test database read permission
        try:
            with open(self.db_path, 'rb') as f:
                f.read(10)
            print("✅ Database read permission: OK")
        except Exception as e:
            print(f"❌ Database read permission: {e}")
        
        # Test directory listing
        try:
            files = list(self.watch_directory.iterdir())
            print(f"✅ Directory listing: OK ({len(files)} files)")
        except Exception as e:
            print(f"❌ Directory listing: {e}")
        
        # Test if we can detect SQLite files
        db_files = ['chat.db', 'chat.db-wal', 'chat.db-shm', 'chat.db-journal']
        for db_file in db_files:
            file_path = self.watch_directory / db_file
            exists = file_path.exists()
            print(f"   {db_file}: {'✅ exists' if exists else '❌ missing'}")
    
    async def _queue_processor(self):
        """Process database change events from the queue in the main async loop."""
        print(f"🔄 Queue processor started in thread: {threading.current_thread().name}")
        
        while self._is_running:
            try:
                # Non-blocking check for queue items
                event_data = self.message_queue.get_nowait()
                
                self.callback_events_count += 1
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                
                print(f"\n🔔 [{timestamp}] Processing queued database change")
                print(f"   Event ID: {event_data['event_id']}")
                print(f"   File: {event_data['file_name']}")
                print(f"   Event type: {event_data['event_type']}")
                print(f"   Queue latency: {time.time() - event_data['timestamp']:.3f}s")
                print(f"   Processor thread: {threading.current_thread().name}")
                print(f"   Total callbacks processed: {self.callback_events_count}")
                
                # Process the database change
                await self._check_new_messages()
                
                # Mark queue task as done
                self.message_queue.task_done()
                
            except queue.Empty:
                # No items in queue, sleep briefly
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"❌ Error processing queue: {e}")
                await asyncio.sleep(0.1)
    
    def _check_new_messages_sync(self):
        """Synchronous version of message checking."""
        try:
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            
            # Get latest message ID
            cursor.execute("SELECT MAX(ROWID) FROM message")
            result = cursor.fetchone()
            latest_id = result[0] if result[0] is not None else 0
            
            conn.close()
            
            if latest_id > self.last_message_id:
                new_messages = latest_id - self.last_message_id
                self.message_count += new_messages
                print(f"📨 New messages detected: {new_messages} (total: {self.message_count})")
                self.last_message_id = latest_id
            else:
                print("📭 No new messages")
                
        except Exception as e:
            print(f"❌ Error checking messages: {e}")
    
    async def _check_new_messages(self):
        """Async version of message checking."""
        print("🔍 Checking for new messages (async)...")
        self._check_new_messages_sync()
    
    def start_file_watcher(self, use_polling=True):
        """Start the file watcher with enhanced detection."""
        if self.observer:
            print("⚠️ File watcher already running")
            return
        
        observer_type = "PollingObserver" if use_polling else "Standard Observer"
        print(f"\n🚀 Starting {observer_type} for SQLite file detection...")
        
        try:
            self.watcher = DebugMessageDatabaseWatcher(self.message_queue, "PollingV4")
            
            # Use PollingObserver for reliable SQLite file detection
            if use_polling:
                self.observer = PollingObserver(timeout=0.5)  # Poll every 500ms
                print(f"📊 Using PollingObserver with 500ms polling interval")
            else:
                self.observer = Observer()
                print(f"📊 Using standard Observer (OS file events)")
            
            # Watch the directory non-recursively
            self.observer.schedule(self.watcher, str(self.watch_directory), recursive=False)
            self.observer.start()
            
            print(f"✅ File watcher started successfully")
            print(f"   Watching: {self.watch_directory}")
            print(f"   Communication: Thread-safe queue")
            print(f"   Observer thread: {self.observer.name}")
            print(f"   Observer type: {type(self.observer).__name__}")
            print(f"   Debounce interval: {self.watcher._debounce_interval}s")
            print(f"   Detection method: {'stat() polling' if use_polling else 'OS file events'}")
            
            # Test if watcher is actually working by creating a test file
            self._test_file_watcher()
            
        except Exception as e:
            print(f"❌ Failed to start file watcher: {e}")
            import traceback
            traceback.print_exc()
            self.observer = None
            self.watcher = None
    
    def _test_file_watcher(self):
        """Test if the file watcher is working by creating a test file."""
        try:
            test_file = self.watch_directory / "test_watcher.tmp"
            print(f"\n🧪 Testing file watcher with: {test_file}")
            
            # Create test file
            test_file.write_text("test")
            time.sleep(0.2)
            
            # Modify test file
            test_file.write_text("test modified")
            time.sleep(0.2)
            
            # Delete test file
            test_file.unlink()
            
            print(f"✅ File watcher test completed")
            
        except Exception as e:
            print(f"⚠️ File watcher test failed: {e}")
    
    def stop_file_watcher(self):
        """Stop the file watcher and queue processor."""
        print("\n🛑 Stopping file watcher...")
        
        # Stop the running flag first
        self._is_running = False
        
        # Stop queue processor
        if self._queue_processor_task:
            self._queue_processor_task.cancel()
            try:
                # Wait a bit for graceful cancellation
                pass
            except asyncio.CancelledError:
                pass
            self._queue_processor_task = None
        
        # Stop file observer
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5)
            
            if self.watcher:
                stats = self.watcher.get_stats()
                print("📊 File watcher statistics:")
                for key, value in stats.items():
                    print(f"   {key}: {value}")
            
            self.observer = None
            self.watcher = None
        
        # Clear any remaining queue items
        queue_size = self.message_queue.qsize()
        if queue_size > 0:
            print(f"🗑️ Clearing {queue_size} remaining queue items")
            while not self.message_queue.empty():
                try:
                    self.message_queue.get_nowait()
                    self.message_queue.task_done()
                except queue.Empty:
                    break
        
        print("✅ File watcher stopped")
    
    async def start_queue_processor(self):
        """Start the queue processor task."""
        if self._queue_processor_task:
            print("⚠️ Queue processor already running")
            return
        
        self._is_running = True
        self._queue_processor_task = asyncio.create_task(self._queue_processor())
        print("🔄 Queue processor started")
    
    def get_status(self):
        """Get current test status."""
        print(f"\n📋 Test Status:")
        print(f"   File watcher active: {self.observer is not None and self.observer.is_alive() if self.observer else False}")
        print(f"   Queue processor running: {self._is_running}")
        print(f"   Queue size: {self.message_queue.qsize()}")
        print(f"   Last message ID: {self.last_message_id}")
        print(f"   Total new messages: {self.message_count}")
        print(f"   Queue events processed: {self.callback_events_count}")
        
        if self.watcher:
            stats = self.watcher.get_stats()
            print(f"   File events: {stats['total_events']}")
            print(f"   Queue puts: {stats['queue_puts']}")


async def main():
    """Main test function."""
    print("🧪 Real-Time File Watcher Test - Version 4 (PollingObserver)")
    print("=" * 60)
    
    test = RealTimeTest()
    
    # Initialize last message ID
    test._check_new_messages_sync()
    
    print(f"\n📋 Instructions:")
    print(f"   1. File watcher will start in 3 seconds")
    print(f"   2. Send some iMessages to trigger database changes")
    print(f"   3. Watch the output for file events and message detection")
    print(f"   4. Press Ctrl+C to stop")
    
    await asyncio.sleep(3)
    
    print(f"\n" + "="*40)
    print(f"Testing PollingObserver Version 4")
    print("="*40)
    
    # Start file watcher
    test.start_file_watcher()
    
    if test.observer:
        try:
            # Start queue processor
            await test.start_queue_processor()
            
            print(f"\n⏰ Testing for 20 seconds... (send messages now!)")
            print(f"   PollingObserver active (stat() based detection)")
            print(f"   File watcher thread: {test.observer.name}")
            print(f"   Main thread: {threading.current_thread().name}")
            print(f"   Polling interval: 500ms")
            print(f"   Watching for ALL event types on database files")
            
            # Wait for 20 seconds while processing events
            await asyncio.sleep(20)
            
            test.get_status()
            test.stop_file_watcher()
            
        except KeyboardInterrupt:
            print(f"\n⌨️ Interrupted by user")
            test.stop_file_watcher()
    else:
        print(f"❌ File watcher failed to start")
    
    print(f"\n🏁 Test completed!")
    print(f"📊 Final Results:")
    print(f"   Messages detected: {test.message_count}")
    print(f"   Queue events processed: {test.callback_events_count}")
    print(f"   PollingObserver: {'✅ SUCCESS' if test.callback_events_count > 0 else '⚠️ No events detected'}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n👋 Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test error: {e}")
