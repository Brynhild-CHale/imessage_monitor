"""Tests for outbound messaging functionality."""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch

from imessage_monitor.outbound import (
    AppleScriptSender, 
    ShortcutsSender, 
    OutboundMessageSender,
    RateLimiter,
    OutboundStats
)
from imessage_monitor.config import Config, OutboundConfig
from imessage_monitor.exceptions import OutboundMessageError


class TestAppleScriptSender:
    """Test AppleScript sender functionality."""
    
    @pytest.fixture
    def sender(self):
        """Create AppleScript sender instance."""
        return AppleScriptSender(timeout=10)
    
    def test_escape_applescript_string(self, sender):
        """Test AppleScript string escaping."""
        # Test basic escaping
        assert sender._escape_applescript_string('hello') == 'hello'
        
        # Test quote escaping
        assert sender._escape_applescript_string('say "hello"') == 'say \\"hello\\"'
        
        # Test backslash escaping
        assert sender._escape_applescript_string('path\\to\\file') == 'path\\\\to\\\\file'
        
        # Test newline escaping
        assert sender._escape_applescript_string('line1\nline2') == 'line1\\nline2'
    
    def test_build_text_script(self, sender):
        """Test text message script building."""
        script = sender.build_text_script("+1234567890", "Hello World")
        
        assert 'tell application "Messages"' in script
        assert '+1234567890' in script
        assert 'Hello World' in script
        assert 'iMessage' in script
        assert 'SMS' in script  # Should have fallback
    
    def test_build_attachment_script(self, sender):
        """Test attachment script building."""
        test_file = Path("/tmp/test.txt")
        script = sender.build_attachment_script("+1234567890", test_file)
        
        assert 'tell application "Messages"' in script
        assert '+1234567890' in script
        assert str(test_file.absolute()) in script
        assert 'Pictures' in script  # Should use Pictures folder method
        assert 'cp' in script  # Should copy file first
        assert 'rm' in script  # Should clean up
    
    @pytest.mark.asyncio
    async def test_pictures_folder_access(self, sender):
        """Test Pictures folder read/write access using AppleScript."""
        try:
            # This is the main test - verify Pictures folder access works
            success = await sender.test_pictures_folder_access()
            assert success is True
        except OutboundMessageError as e:
            pytest.skip(f"Pictures folder access test failed - may need permissions: {e}")


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    def test_rate_limiter_basic(self):
        """Test basic rate limiter functionality."""
        limiter = RateLimiter(max_per_minute=5)
        
        # Should not be rate limited initially
        assert not limiter.is_rate_limited()
        
        # Record several sends
        for _ in range(4):
            limiter.record_send()
        
        # Should not be rate limited yet
        assert not limiter.is_rate_limited()
        
        # One more should trigger rate limiting
        limiter.record_send()
        assert limiter.is_rate_limited()
    
    def test_rate_limiter_cleanup(self):
        """Test timestamp cleanup."""
        limiter = RateLimiter(max_per_minute=2)
        
        # Add old timestamp manually
        import time
        limiter.sent_timestamps = [time.time() - 70]  # 70 seconds ago
        
        # Check rate limiting - should clean up old timestamp
        assert not limiter.is_rate_limited()
        assert len(limiter.sent_timestamps) == 0


class TestOutboundStats:
    """Test statistics tracking."""
    
    def test_stats_tracking(self):
        """Test statistics increment and retrieval."""
        stats = OutboundStats()
        
        # Test initial state
        assert stats.messages_sent == 0
        assert stats.attachments_sent == 0
        
        # Test increments
        stats.increment_messages_sent()
        stats.increment_attachments_sent()
        stats.increment_failures()
        
        assert stats.messages_sent == 1
        assert stats.attachments_sent == 1
        assert stats.send_failures == 1
        
        # Test get_stats
        stats_dict = stats.get_stats()
        assert stats_dict['messages_sent'] == 1
        assert stats_dict['attachments_sent'] == 1
        assert stats_dict['send_failures'] == 1
        
        # Test reset
        stats.reset()
        assert stats.messages_sent == 0
        assert stats.attachments_sent == 0
        assert stats.send_failures == 0


class TestOutboundMessageSender:
    """Test main outbound message sender."""
    
    @pytest.fixture
    def config(self):
        """Create test config."""
        return Config(
            apple=Mock(),
            monitoring=Mock(),
            contacts=Mock(),
            date_range=Mock(),
            outbound=OutboundConfig(
                method="applescript",
                rate_limit_per_minute=30
            )
        )
    
    @pytest.fixture
    def sender(self, config):
        """Create outbound message sender."""
        return OutboundMessageSender(config)
    
    def test_validate_recipient_phone(self, sender):
        """Test phone number validation."""
        # Valid phone numbers
        assert sender.validate_recipient("+1234567890")
        assert sender.validate_recipient("1234567890")
        assert sender.validate_recipient("(123) 456-7890")
        assert sender.validate_recipient("+44 20 1234 5678")
        
        # Invalid recipients
        assert not sender.validate_recipient("")
        assert not sender.validate_recipient("abc")
        assert not sender.validate_recipient("123")  # Too short
    
    def test_validate_recipient_email(self, sender):
        """Test email validation."""
        # Valid emails
        assert sender.validate_recipient("test@example.com")
        assert sender.validate_recipient("user.name+tag@domain.co.uk")
        
        # Invalid emails
        assert not sender.validate_recipient("invalid.email")
        assert not sender.validate_recipient("@domain.com")
        assert not sender.validate_recipient("user@")


class TestShortcutsSender:
    """Test Shortcuts sender functionality."""
    
    @pytest.fixture
    def sender(self):
        """Create Shortcuts sender instance."""
        return ShortcutsSender(timeout=10)
    
    def test_validate_shortcuts_available(self, sender):
        """Test shortcuts availability check."""
        # This test may pass or fail depending on system setup
        # Just ensure it doesn't crash
        result = sender.validate_shortcuts_available()
        assert isinstance(result, bool)



if __name__ == "__main__":
    # Run the Pictures folder test directly
    async def run_pictures_test():
        sender = AppleScriptSender()
        try:
            print("Testing Pictures folder access...")
            success = await sender.test_pictures_folder_access()
            print(f"Pictures folder test result: {'✅ PASSED' if success else '❌ FAILED'}")
        except Exception as e:
            print(f"❌ Pictures folder test error: {e}")
    
    asyncio.run(run_pictures_test())