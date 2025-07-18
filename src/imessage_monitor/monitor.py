"""Core iMessage Monitor class for extracting and monitoring messages."""

import asyncio
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from .message_parser import get_recent_messages
from .config import Config
from .utils import to_json, to_toml


class iMessageMonitor:
    """Main iMessage Monitor class for extracting and monitoring messages."""
    
    def __init__(self, config_path: str = None):
        """Initialize the iMessage Monitor.
        
        Args:
            config_path: Path to config file. If None, uses default config.
        """
        if config_path:
            self.config = Config.from_file(Path(config_path))
        else:
            self.config = Config.default()
        self._is_running = False
        self._monitor_task = None
        self._db_path = str(Path.home() / "Library" / "Messages" / "chat.db")
        self._last_message_id = 0
        self._message_callback = None
        
        # Validate database exists
        if not Path(self._db_path).exists():
            raise FileNotFoundError(f"Messages database not found at {self._db_path}")
    
    def start(self, message_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """Start monitoring for new messages.
        
        Args:
            message_callback: Optional callback function to handle new messages
        
        Returns:
            List of all recent messages (initial data)
        """
        if self._is_running:
            raise RuntimeError("Monitor is already running")
        
        self._is_running = True
        self._message_callback = message_callback
        
        # Get initial messages
        limit = getattr(self.config, 'initial_message_limit', 100)
        messages = get_recent_messages(self._db_path, limit)
        
        # Set the last message ID to track new messages
        if messages:
            self._last_message_id = messages[0]['message_id']
        
        # Start monitoring task if callback provided
        if message_callback:
            self._monitor_task = asyncio.create_task(self._monitor_loop())
        
        return messages
    
    def stop(self):
        """Stop monitoring for messages."""
        if not self._is_running:
            return
        
        self._is_running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            self._monitor_task = None
        
        self._message_callback = None
    
    def get_recent_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent messages without starting monitoring.
        
        Args:
            limit: Number of recent messages to retrieve
            
        Returns:
            List of message dictionaries with full parsing
        """
        return get_recent_messages(self._db_path, limit)
    
    def get_messages_since(self, message_id: int) -> List[Dict[str, Any]]:
        """Get all messages since a specific message ID.
        
        Args:
            message_id: The message ID to start from
            
        Returns:
            List of new messages
        """
        try:
            conn = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            
            # Simple query to get messages newer than the specified ID
            cursor.execute("""
                SELECT ROWID FROM message 
                WHERE ROWID > ? 
                ORDER BY date DESC 
                LIMIT 1000
            """, (message_id,))
            
            new_message_ids = cursor.fetchall()
            conn.close()
            
            if not new_message_ids:
                return []
            
            # Get the newest message ID to determine how many new messages we have
            newest_id = new_message_ids[0][0]
            message_count = len(new_message_ids)
            
            # Get full message data for all new messages
            return get_recent_messages(self._db_path, message_count)
            
        except Exception as e:
            print(f"Error getting messages since {message_id}: {e}")
            return []
    
    async def _monitor_loop(self):
        """Internal monitoring loop for new messages."""
        polling_interval = getattr(self.config, 'polling_interval', 3)
        
        while self._is_running:
            try:
                # Check for new messages
                new_messages = self.get_messages_since(self._last_message_id)
                
                if new_messages:
                    # Update last message ID
                    self._last_message_id = new_messages[0]['message_id']
                    
                    # Process each new message
                    for message in reversed(new_messages):  # Process in chronological order
                        if self._message_callback:
                            try:
                                self._message_callback(message)
                            except Exception as e:
                                print(f"Error in message callback: {e}")
                
                # Sleep until next poll
                await asyncio.sleep(polling_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in monitor loop: {e}")
                await asyncio.sleep(polling_interval)
    
    def is_running(self) -> bool:
        """Check if monitor is currently running."""
        return self._is_running
    
    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        return {
            'is_running': self._is_running,
            'last_message_id': self._last_message_id,
            'db_path': self._db_path,
            'has_callback': self._message_callback is not None
        }
    
    # Utility methods for data conversion
    def to_json(self, messages: List[Dict[str, Any]], filename: str = None) -> str:
        """Convert messages to JSON format."""
        return to_json(messages, filename)
    
    def to_toml(self, messages: List[Dict[str, Any]], filename: str = None) -> str:
        """Convert messages to TOML format."""
        return to_toml(messages, filename)
    
    # Context manager support
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self.stop()