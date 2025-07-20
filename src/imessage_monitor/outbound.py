"""Outbound message sending interface."""
import subprocess
import asyncio
import time
import re
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
from .config import Config
from .exceptions import OutboundMessageError


class OutboundMessageSender:
    """Handles sending outbound messages via AppleScript or Shortcuts."""
    
    def __init__(self, config: Config):
        self.config = config
        self.method = config.outbound.method
        self.rate_limiter = RateLimiter(config.outbound.rate_limit_per_minute)
        self.applescript_sender = AppleScriptSender()
        self.shortcuts_sender = ShortcutsSender()
        self.logger = logging.getLogger(__name__)
        self.stats = OutboundStats()
    
    async def send_message(self, recipient: str, content: str) -> bool:
        """Send message using configured method."""
        try:
            if not self.validate_recipient(recipient):
                raise OutboundMessageError(f"Invalid recipient format: {recipient}")
            
            await self.rate_limiter.wait_if_needed()
            
            success = False
            if self.method == "applescript":
                success = await self.send_message_applescript(recipient, content)
                if success:
                    self.stats.increment_applescript_sends()
            elif self.method == "shortcuts":
                success = await self.send_message_shortcuts(recipient, content)
                if success:
                    self.stats.increment_shortcuts_sends()
            else:
                raise OutboundMessageError(f"Unknown outbound method: {self.method}")
            
            if success:
                self.rate_limiter.record_send()
                self.stats.increment_messages_sent()
                self.logger.info(f"Message sent successfully to {recipient} via {self.method}")
            else:
                self.stats.increment_failures()
                
            return success
            
        except Exception as e:
            self.stats.increment_failures()
            self.logger.error(f"Failed to send message to {recipient}: {e}")
            raise
    
    async def send_attachment(self, recipient: str, file_path: Path) -> bool:
        """Send file attachment."""
        try:
            if not self.validate_recipient(recipient):
                raise OutboundMessageError(f"Invalid recipient format: {recipient}")
            
            if not file_path.exists():
                raise OutboundMessageError(f"File not found: {file_path}")
            
            await self.rate_limiter.wait_if_needed()
            
            success = False
            if self.method == "applescript":
                success = await self.send_attachment_applescript(recipient, file_path)
                if success:
                    self.stats.increment_applescript_sends()
            elif self.method == "shortcuts":
                success = await self.send_attachment_shortcuts(recipient, file_path)
                if success:
                    self.stats.increment_shortcuts_sends()
            else:
                raise OutboundMessageError(f"Unknown outbound method: {self.method}")
            
            if success:
                self.rate_limiter.record_send()
                self.stats.increment_attachments_sent()
                self.logger.info(f"Attachment sent successfully to {recipient} via {self.method}: {file_path.name}")
            else:
                self.stats.increment_failures()
                
            return success
            
        except Exception as e:
            self.stats.increment_failures()
            self.logger.error(f"Failed to send attachment to {recipient}: {e}")
            raise
    
    async def send_message_applescript(self, recipient: str, content: str) -> bool:
        """Send message using AppleScript."""
        return await self.applescript_sender.send_text_message(recipient, content)
    
    async def send_message_shortcuts(self, recipient: str, content: str) -> bool:
        """Send message using Apple Shortcuts."""
        return await self.shortcuts_sender.send_text_message(recipient, content)
    
    async def send_attachment_applescript(self, recipient: str, file_path: Path) -> bool:
        """Send attachment using AppleScript."""
        return await self.applescript_sender.send_file_attachment(recipient, file_path)
    
    async def send_attachment_shortcuts(self, recipient: str, file_path: Path) -> bool:
        """Send attachment using Apple Shortcuts."""
        return await self.shortcuts_sender.send_file_attachment(recipient, file_path)
    
    def validate_recipient(self, recipient: str) -> bool:
        """Validate recipient phone number format."""
        if not recipient or not recipient.strip():
            return False
        
        # Remove whitespace
        recipient = recipient.strip()
        
        # Check for email format (iMessage)
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(email_pattern, recipient):
            return True
        
        # Check for phone number format
        # Remove common formatting characters
        phone_digits = re.sub(r'[\s\-\(\)\+\.]', '', recipient)
        
        # Check if it's all digits and reasonable length
        if phone_digits.isdigit() and 10 <= len(phone_digits) <= 15:
            return True
        
        # Check for international format starting with +
        if recipient.startswith('+') and phone_digits[1:].isdigit() and 10 <= len(phone_digits) <= 15:
            return True
        
        return False
    
    def escape_applescript_string(self, text: str) -> str:
        """Escape string for AppleScript safety."""
        return self._escape_applescript_string(text)
    
    def _escape_applescript_string(self, text: str) -> str:
        """Internal method to escape string for AppleScript safety."""
        # Handle backslashes first
        text = text.replace('\\', '\\\\')
        # Handle quotes
        text = text.replace('"', '\\"')
        # Handle newlines and tabs
        text = text.replace('\n', '\\n')
        text = text.replace('\r', '\\r')
        text = text.replace('\t', '\\t')
        return text


class AppleScriptSender:
    """AppleScript-based message sending."""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
    
    def _escape_applescript_string(self, text: str) -> str:
        """Escape string for AppleScript safety."""
        # Handle backslashes first
        text = text.replace('\\', '\\\\')
        # Handle quotes
        text = text.replace('"', '\\"')
        # Handle newlines and tabs
        text = text.replace('\n', '\\n')
        text = text.replace('\r', '\\r')
        text = text.replace('\t', '\\t')
        return text
    
    async def send_text_message(self, recipient: str, message: str) -> bool:
        """Send text message via AppleScript."""
        try:
            script = self.build_text_script(recipient, message)
            return await self.execute_applescript(script)
        except Exception as e:
            raise OutboundMessageError(f"Failed to send text message: {e}")
    
    async def send_file_attachment(self, recipient: str, file_path: Path) -> bool:
        """Send file attachment via AppleScript."""
        try:
            if not file_path.exists():
                raise OutboundMessageError(f"File not found: {file_path}")
            
            script = self.build_attachment_script(recipient, file_path)
            return await self.execute_applescript(script)
        except Exception as e:
            raise OutboundMessageError(f"Failed to send attachment: {e}")
    
    def build_text_script(self, recipient: str, message: str) -> str:
        """Build AppleScript for text message."""
        safe_recipient = self._escape_applescript_string(recipient)
        safe_message = self._escape_applescript_string(message)
        
        return f'''
        tell application "Messages"
            try
                set targetService to 1st service whose service type = iMessage
                set targetBuddy to buddy "{safe_recipient}" of targetService
                send "{safe_message}" to targetBuddy
                return "success"
            on error errorMessage
                try
                    set smsService to 1st service whose service type = SMS
                    set smsBuddy to buddy "{safe_recipient}" of smsService
                    send "{safe_message}" to smsBuddy
                    return "success"
                on error smsError
                    return "error: " & errorMessage & " (SMS fallback failed: " & smsError & ")"
                end try
            end try
        end tell
        '''
    
    def build_attachment_script(self, recipient: str, file_path: Path) -> str:
        """Build AppleScript for file attachment using Pictures folder method."""
        safe_recipient = self._escape_applescript_string(recipient)
        safe_source_path = self._escape_applescript_string(str(file_path.absolute()))
        
        # Use just the filename for the Pictures folder
        filename = file_path.name
        safe_filename = self._escape_applescript_string(filename)
        
        return f'''
        -- Copy file to Pictures folder first (most reliable method)
        do shell script "cp '{safe_source_path}' ~/Pictures/"
        
        -- Get the full path to the Pictures folder file
        set picturesPath to (path to pictures folder as text) & "{safe_filename}"
        set picturesFile to picturesPath as alias
        
        tell application "Messages"
            try
                set targetService to 1st service whose service type = iMessage
                set targetBuddy to buddy "{safe_recipient}" of targetService
                send picturesFile to targetBuddy
                
                -- Clean up: remove file from Pictures folder
                do shell script "rm ~/Pictures/{safe_filename}"
                return "success"
            on error errorMessage
                -- Clean up even if sending fails
                try
                    do shell script "rm ~/Pictures/{safe_filename}"
                end try
                return "error: " & errorMessage
            end try
        end tell
        '''
    
    async def test_pictures_folder_access(self) -> bool:
        """Test read/write access to Pictures folder using AppleScript."""
        test_filename = "imessage_monitor_test.txt"
        test_content = "This is a test file for iMessage Monitor attachment functionality."
        
        script = f'''
        set testFileName to "{test_filename}"
        set testContent to "{test_content}"
        
        try
            -- Step 1: Write test file to Pictures folder
            do shell script "echo '" & testContent & "' > ~/Pictures/" & testFileName
            
            -- Step 2: Verify file exists and read content
            set readContent to do shell script "cat ~/Pictures/" & testFileName
            
            if readContent does not contain testContent then
                return "error: File content verification failed"
            end if
            
            -- Step 3: Remove test file
            do shell script "rm ~/Pictures/" & testFileName
            
            -- Step 4: Verify file is removed
            try
                do shell script "test -f ~/Pictures/" & testFileName
                return "error: File removal verification failed - file still exists"
            on error
                -- This is expected - file should not exist
            end try
            
            return "success"
            
        on error errorMessage
            -- Clean up test file if it exists
            try
                do shell script "rm ~/Pictures/" & testFileName
            end try
            return "error: " & errorMessage
        end try
        '''
        
        try:
            process = await asyncio.create_subprocess_exec(
                '/usr/bin/osascript', '-',
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=script.encode('utf-8')),
                timeout=self.timeout
            )
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='replace').strip()
                raise OutboundMessageError(f"Pictures folder test failed: {error_msg}")
            
            result = stdout.decode('utf-8', errors='replace').strip()
            if result.startswith('error:'):
                raise OutboundMessageError(f"Pictures folder access test failed: {result}")
            
            self.logger.info("Pictures folder access test passed successfully")
            return True
            
        except asyncio.TimeoutError:
            raise OutboundMessageError(f"Pictures folder test timed out after {self.timeout} seconds")
        except Exception as e:
            raise OutboundMessageError(f"Pictures folder test error: {e}")

    async def execute_applescript(self, script: str) -> bool:
        """Execute AppleScript and return success status."""
        try:
            process = await asyncio.create_subprocess_exec(
                '/usr/bin/osascript', '-',
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=script.encode('utf-8')),
                timeout=self.timeout
            )
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='replace').strip()
                raise OutboundMessageError(f"AppleScript execution failed: {error_msg}")
            
            result = stdout.decode('utf-8', errors='replace').strip()
            if result.startswith('error:'):
                raise OutboundMessageError(f"AppleScript returned error: {result}")
            
            return True
            
        except asyncio.TimeoutError:
            raise OutboundMessageError(f"AppleScript execution timed out after {self.timeout} seconds")
        except Exception as e:
            raise OutboundMessageError(f"AppleScript execution error: {e}")


class ShortcutsSender:
    """Apple Shortcuts-based message sending."""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
    
    async def send_text_message(self, recipient: str, message: str) -> bool:
        """Send text message via Shortcuts."""
        try:
            if not self.validate_shortcuts_available():
                raise OutboundMessageError("Shortcuts app not available or not configured")
            
            # Use the "Send Message" shortcut with input data
            input_data = {
                "recipient": recipient,
                "message": message
            }
            
            return await self.execute_shortcut("Send Message", input_data)
            
        except Exception as e:
            raise OutboundMessageError(f"Failed to send message via Shortcuts: {e}")
    
    async def send_file_attachment(self, recipient: str, file_path: Path) -> bool:
        """Send file attachment via Shortcuts."""
        try:
            if not self.validate_shortcuts_available():
                raise OutboundMessageError("Shortcuts app not available or not configured")
            
            if not file_path.exists():
                raise OutboundMessageError(f"File not found: {file_path}")
            
            # Use the "Send Attachment" shortcut with file input
            input_data = {
                "recipient": recipient,
                "file_path": str(file_path.absolute())
            }
            
            return await self.execute_shortcut("Send Attachment", input_data)
            
        except Exception as e:
            raise OutboundMessageError(f"Failed to send attachment via Shortcuts: {e}")
    
    async def execute_shortcut(self, shortcut_name: str, input_data: Dict[str, Any]) -> bool:
        """Execute named shortcut with input data."""
        try:
            # Prepare input as JSON for the shortcut
            import json
            input_json = json.dumps(input_data)
            
            process = await asyncio.create_subprocess_exec(
                '/usr/bin/shortcuts', 'run', shortcut_name,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=input_json.encode('utf-8')),
                timeout=self.timeout
            )
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='replace').strip()
                raise OutboundMessageError(f"Shortcut execution failed: {error_msg}")
            
            return True
            
        except asyncio.TimeoutError:
            raise OutboundMessageError(f"Shortcut execution timed out after {self.timeout} seconds")
        except Exception as e:
            raise OutboundMessageError(f"Shortcut execution error: {e}")
    
    def validate_shortcuts_available(self) -> bool:
        """Check if Shortcuts app is available and configured."""
        try:
            # Check if shortcuts command is available
            import subprocess
            result = subprocess.run(
                ['/usr/bin/shortcuts', 'list'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return False
            
            # Check if required shortcuts exist
            shortcuts_list = result.stdout.strip().split('\n')
            required_shortcuts = ['Send Message', 'Send Attachment']
            
            for required in required_shortcuts:
                if required not in shortcuts_list:
                    # Log missing shortcuts but don't fail validation
                    # User might have custom shortcut names
                    logging.getLogger(__name__).warning(
                        f"Recommended shortcut '{required}' not found. "
                        f"Available shortcuts: {shortcuts_list}"
                    )
            
            return True
            
        except Exception:
            return False



class RateLimiter:
    """Rate limiter for outbound messages."""
    
    def __init__(self, max_per_minute: int):
        self.max_per_minute = max_per_minute
        self.sent_timestamps: List[float] = []
    
    async def wait_if_needed(self) -> None:
        """Wait if rate limit would be exceeded."""
        self.cleanup_old_timestamps()
        
        if len(self.sent_timestamps) >= self.max_per_minute:
            # Calculate how long to wait
            oldest_timestamp = min(self.sent_timestamps)
            wait_time = 60.0 - (time.time() - oldest_timestamp)
            
            if wait_time > 0:
                await asyncio.sleep(wait_time)
    
    def is_rate_limited(self) -> bool:
        """Check if currently rate limited."""
        self.cleanup_old_timestamps()
        return len(self.sent_timestamps) >= self.max_per_minute
    
    def record_send(self) -> None:
        """Record that a message was sent."""
        self.sent_timestamps.append(time.time())
        self.cleanup_old_timestamps()
    
    def cleanup_old_timestamps(self) -> None:
        """Remove timestamps older than 1 minute."""
        cutoff_time = time.time() - 60.0
        self.sent_timestamps = [ts for ts in self.sent_timestamps if ts > cutoff_time]


class OutboundStats:
    """Statistics for outbound message sending."""
    
    def __init__(self):
        self.messages_sent = 0
        self.attachments_sent = 0
        self.send_failures = 0
        self.rate_limit_delays = 0
        self.applescript_sends = 0
        self.shortcuts_sends = 0
    
    def increment_messages_sent(self) -> None:
        """Increment messages sent count."""
        self.messages_sent += 1
    
    def increment_attachments_sent(self) -> None:
        """Increment attachments sent count."""
        self.attachments_sent += 1
    
    
    def increment_failures(self) -> None:
        """Increment send failures count."""
        self.send_failures += 1
    
    def increment_rate_limit_delays(self) -> None:
        """Increment rate limit delays count."""
        self.rate_limit_delays += 1
    
    def increment_applescript_sends(self) -> None:
        """Increment AppleScript sends count."""
        self.applescript_sends += 1
    
    def increment_shortcuts_sends(self) -> None:
        """Increment Shortcuts sends count."""
        self.shortcuts_sends += 1
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics dictionary."""
        return {
            "messages_sent": self.messages_sent,
            "attachments_sent": self.attachments_sent,
            "send_failures": self.send_failures,
            "rate_limit_delays": self.rate_limit_delays,
            "applescript_sends": self.applescript_sends,
            "shortcuts_sends": self.shortcuts_sends
        }
    
    def reset(self) -> None:
        """Reset all statistics."""
        self.messages_sent = 0
        self.attachments_sent = 0
        self.send_failures = 0
        self.rate_limit_delays = 0
        self.applescript_sends = 0
        self.shortcuts_sends = 0


class ImessageOutbound:
    """Simple interface for sending iMessage messages and attachments."""
    
    def __init__(self, config=None):
        """Initialize the outbound interface.
        
        Args:
            config: Optional config to use for contact filtering. If None, uses default config.
        """
        if config is None:
            from .config import Config
            config = Config.default()
        self.config = config
        self.applescript_sender = AppleScriptSender()
        self.shortcuts_sender = ShortcutsSender()
    
    def _check_outbound_allowed(self, recipient: str) -> tuple[bool, str]:
        """Check if outbound message to recipient is allowed by contact filter.
        
        Args:
            recipient: Phone number or email address
            
        Returns:
            Tuple of (is_allowed, reason_if_blocked)
        """
        contact_filter = self.config.contacts
        
        # If no filtering is enabled, allow all
        if contact_filter.outbound_behavior == "none":
            return True, ""
        
        # Check whitelist
        if contact_filter.outbound_behavior == "whitelist":
            if recipient not in contact_filter.outbound_ids:
                return False, f"Recipient '{recipient}' not in outbound whitelist"
            return True, ""
        
        # Check blacklist
        if contact_filter.outbound_behavior == "blacklist":
            if recipient in contact_filter.outbound_ids:
                return False, f"Recipient '{recipient}' is in outbound blacklist"
            return True, ""
        
        return True, ""
    
    def send_message_applescript(self, recipient: str, message: str) -> bool:
        """Send message using AppleScript.
        
        Args:
            recipient: Phone number or email address
            message: Message content to send
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            OutboundMessageError: If sending fails or blocked by contact filter
        """
        # Check contact filter first
        allowed, reason = self._check_outbound_allowed(recipient)
        if not allowed:
            raise OutboundMessageError(f"Message blocked by contact filter: {reason}")
        
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(
                self.applescript_sender.send_text_message(recipient, message)
            )
        except Exception as e:
            raise OutboundMessageError(f"Failed to send message via AppleScript: {e}")
    
    def send_message_shortcuts(self, recipient: str, message: str) -> bool:
        """Send message using Apple Shortcuts.
        
        Args:
            recipient: Phone number or email address
            message: Message content to send
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            OutboundMessageError: If sending fails, shortcut not found, or blocked by contact filter
        """
        # Check contact filter first
        allowed, reason = self._check_outbound_allowed(recipient)
        if not allowed:
            raise OutboundMessageError(f"Message blocked by contact filter: {reason}")
        
        try:
            # Check if shortcuts are available first
            if not self.shortcuts_sender.validate_shortcuts_available():
                raise OutboundMessageError(
                    "Shortcuts not available or 'Send Message' shortcut not found. "
                    "Please refer to the README to set up the required shortcuts."
                )
            
            import asyncio
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(
                self.shortcuts_sender.send_text_message(recipient, message)
            )
        except Exception as e:
            if "shortcut" in str(e).lower():
                raise OutboundMessageError(
                    f"Shortcut error: {e}. Please refer to the README to set up the required shortcuts."
                )
            raise OutboundMessageError(f"Failed to send message via Shortcuts: {e}")
    
    def send_attachment_applescript(self, recipient: str, file_path: str) -> bool:
        """Send attachment using AppleScript.
        
        Args:
            recipient: Phone number or email address
            file_path: Path to file to send
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            OutboundMessageError: If sending fails or blocked by contact filter
        """
        # Check contact filter first
        allowed, reason = self._check_outbound_allowed(recipient)
        if not allowed:
            raise OutboundMessageError(f"Attachment blocked by contact filter: {reason}")
        
        try:
            from pathlib import Path
            path_obj = Path(file_path)
            
            if not path_obj.exists():
                raise OutboundMessageError(f"File not found: {file_path}")
            
            import asyncio
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(
                self.applescript_sender.send_file_attachment(recipient, path_obj)
            )
        except Exception as e:
            raise OutboundMessageError(f"Failed to send attachment via AppleScript: {e}")
    
    def send_attachment_shortcuts(self, recipient: str, file_path: str) -> bool:
        """Send attachment using Apple Shortcuts.
        
        Args:
            recipient: Phone number or email address
            file_path: Path to file to send
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            OutboundMessageError: If sending fails, shortcut not found, or blocked by contact filter
        """
        # Check contact filter first
        allowed, reason = self._check_outbound_allowed(recipient)
        if not allowed:
            raise OutboundMessageError(f"Attachment blocked by contact filter: {reason}")
        
        try:
            from pathlib import Path
            path_obj = Path(file_path)
            
            if not path_obj.exists():
                raise OutboundMessageError(f"File not found: {file_path}")
            
            # Check if shortcuts are available first
            if not self.shortcuts_sender.validate_shortcuts_available():
                raise OutboundMessageError(
                    "Shortcuts not available or 'Send Attachment' shortcut not found. "
                    "Please refer to the README to set up the required shortcuts."
                )
            
            import asyncio
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(
                self.shortcuts_sender.send_file_attachment(recipient, path_obj)
            )
        except Exception as e:
            if "shortcut" in str(e).lower():
                raise OutboundMessageError(
                    f"Shortcut error: {e}. Please refer to the README to set up the required shortcuts."
                )
            raise OutboundMessageError(f"Failed to send attachment via Shortcuts: {e}")