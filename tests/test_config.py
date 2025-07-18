"""Tests for configuration management."""
import pytest
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

from imessage_monitor.config import (
    Config, ConfigManager, DatabaseConfig, AppleConfig, MonitoringConfig,
    ContactFilter, DateRange, OutboundConfig,
    init_config, get_config, load_config_from_file, create_default_config
)


class TestDateRange:
    """Test DateRange functionality."""

    def test_date_range_creation(self):
        """Test basic DateRange creation."""
        start = datetime(2023, 1, 1)
        end = datetime(2023, 1, 31)
        dr = DateRange(start_date=start, end_date=end)
        
        assert dr.start_date == start
        assert dr.end_date == end

    def test_date_range_from_hours_back(self):
        """Test DateRange.from_hours_back."""
        hours = 24
        dr = DateRange.from_hours_back(hours)
        
        assert dr.start_date is not None
        assert dr.end_date is not None
        assert dr.end_date > dr.start_date
        
        # Should be approximately 24 hours difference
        diff = dr.end_date - dr.start_date
        assert abs(diff.total_seconds() - (hours * 3600)) < 10  # Within 10 seconds

    def test_date_range_from_days_back(self):
        """Test DateRange.from_days_back."""
        days = 7
        dr = DateRange.from_days_back(days)
        
        assert dr.start_date is not None
        assert dr.end_date is not None
        assert dr.end_date > dr.start_date
        
        # Should be approximately 7 days difference
        diff = dr.end_date - dr.start_date
        assert abs(diff.total_seconds() - (days * 24 * 3600)) < 10  # Within 10 seconds

    def test_date_range_none_dates(self):
        """Test DateRange with None dates."""
        dr = DateRange()
        assert dr.start_date is None
        assert dr.end_date is None


class TestDatabaseConfig:
    """Test DatabaseConfig functionality."""

    def test_database_config_creation(self):
        """Test DatabaseConfig creation."""
        config = DatabaseConfig(
            url="postgresql://user:pass@localhost/db",
            pool_size=5,
            max_overflow=10,
            pool_timeout=15
        )
        
        assert config.url == "postgresql://user:pass@localhost/db"
        assert config.pool_size == 5
        assert config.max_overflow == 10
        assert config.pool_timeout == 15

    def test_database_config_defaults(self):
        """Test DatabaseConfig with defaults."""
        config = DatabaseConfig(url="postgresql://localhost/db")
        
        assert config.url == "postgresql://localhost/db"
        assert config.pool_size == 10
        assert config.max_overflow == 20
        assert config.pool_timeout == 30


class TestAppleConfig:
    """Test AppleConfig functionality."""

    def test_apple_config_creation(self):
        """Test AppleConfig creation."""
        config = AppleConfig(
            chat_db_path="/path/to/chat.db",
            attachments_path="/path/to/attachments",
            permissions_check=False
        )
        
        assert config.chat_db_path == "/path/to/chat.db"
        assert config.attachments_path == "/path/to/attachments"
        assert config.permissions_check is False

    def test_apple_config_defaults(self):
        """Test AppleConfig with defaults."""
        config = AppleConfig(
            chat_db_path="/path/to/chat.db",
            attachments_path="/path/to/attachments"
        )
        
        assert config.permissions_check is True


class TestMonitoringConfig:
    """Test MonitoringConfig functionality."""

    def test_monitoring_config_creation(self):
        """Test MonitoringConfig creation."""
        config = MonitoringConfig(
            poll_interval_seconds=5,
            startup_lookback_hours=12,
            max_batch_size=50,
            enable_real_time=False
        )
        
        assert config.poll_interval_seconds == 5
        assert config.startup_lookback_hours == 12
        assert config.max_batch_size == 50
        assert config.enable_real_time is False

    def test_monitoring_config_defaults(self):
        """Test MonitoringConfig with defaults."""
        config = MonitoringConfig()
        
        assert config.poll_interval_seconds == 3
        assert config.startup_lookback_hours == 24
        assert config.max_batch_size == 100
        assert config.enable_real_time is True


class TestContactFilter:
    """Test ContactFilter functionality."""

    def test_contact_filter_creation(self):
        """Test ContactFilter creation."""
        config = ContactFilter(
            phone_numbers=["+15551234567", "+15559876543"],
            include_unknown=False,
            group_chats=False
        )
        
        assert config.phone_numbers == ["+15551234567", "+15559876543"]
        assert config.include_unknown is False
        assert config.group_chats is False

    def test_contact_filter_defaults(self):
        """Test ContactFilter with defaults."""
        config = ContactFilter(phone_numbers=["+15551234567"])
        
        assert config.include_unknown is True
        assert config.group_chats is True


class TestOutboundConfig:
    """Test OutboundConfig functionality."""

    def test_outbound_config_creation(self):
        """Test OutboundConfig creation."""
        config = OutboundConfig(
            method="shortcuts",
            rate_limit_per_minute=60,
            enable_auto_reply=True,
            auto_reply_triggers=["help", "status"]
        )
        
        assert config.method == "shortcuts"
        assert config.rate_limit_per_minute == 60
        assert config.enable_auto_reply is True
        assert config.auto_reply_triggers == ["help", "status"]

    def test_outbound_config_defaults(self):
        """Test OutboundConfig with defaults."""
        config = OutboundConfig()
        
        assert config.method == "applescript"
        assert config.rate_limit_per_minute == 30
        assert config.enable_auto_reply is False
        assert config.auto_reply_triggers is None


class TestConfig:
    """Test main Config functionality."""

    def test_config_default(self):
        """Test Config.default()."""
        config = Config.default()
        
        assert isinstance(config.database, DatabaseConfig)
        assert isinstance(config.apple, AppleConfig)
        assert isinstance(config.monitoring, MonitoringConfig)
        assert isinstance(config.contacts, ContactFilter)
        assert isinstance(config.date_range, DateRange)
        assert isinstance(config.outbound, OutboundConfig)
        
        # Check some specific defaults
        assert config.monitoring.poll_interval_seconds == 3
        assert config.apple.permissions_check is True
        assert config.outbound.method == "applescript"

    def test_config_from_file_valid_toml(self):
        """Test Config.from_file with valid TOML."""
        toml_content = """
[database]
url = "postgresql://user:pass@localhost/test_db"
pool_size = 5

[apple]
chat_db_path = "/test/path/chat.db"
attachments_path = "/test/path/attachments"
permissions_check = false

[monitoring]
poll_interval_seconds = 5
startup_lookback_hours = 12
max_batch_size = 50
enable_real_time = false

[contacts]
phone_numbers = ["+15551234567", "+15559876543"]
include_unknown = false
group_chats = false

[date_range]
start_date = "2023-01-01T00:00:00"
end_date = "2023-01-31T23:59:59"

[outbound]
method = "shortcuts"
rate_limit_per_minute = 60
enable_auto_reply = true
auto_reply_triggers = ["help", "status"]
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(toml_content)
            f.flush()
            
            try:
                config = Config.from_file(Path(f.name))
                
                assert config.database.url == "postgresql://user:pass@localhost/test_db"
                assert config.database.pool_size == 5
                assert config.apple.chat_db_path == "/test/path/chat.db"
                assert config.apple.permissions_check is False
                assert config.monitoring.poll_interval_seconds == 5
                assert config.contacts.phone_numbers == ["+15551234567", "+15559876543"]
                assert config.outbound.method == "shortcuts"
                
                # Check date parsing
                assert config.date_range.start_date == datetime(2023, 1, 1, 0, 0, 0)
                assert config.date_range.end_date == datetime(2023, 1, 31, 23, 59, 59)
                
            finally:
                os.unlink(f.name)

    def test_config_from_file_missing_dates(self):
        """Test Config.from_file with missing date range."""
        toml_content = """
[database]
url = "postgresql://user:pass@localhost/test_db"

[apple]
chat_db_path = "/test/path/chat.db"
attachments_path = "/test/path/attachments"

[monitoring]
poll_interval_seconds = 5
startup_lookback_hours = 12
max_batch_size = 50
enable_real_time = false

[contacts]
phone_numbers = []
include_unknown = true
group_chats = true

[date_range]
# No dates specified

[outbound]
method = "applescript"
rate_limit_per_minute = 30
enable_auto_reply = false
auto_reply_triggers = []
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(toml_content)
            f.flush()
            
            try:
                config = Config.from_file(Path(f.name))
                
                # Date range should have None values
                assert config.date_range.start_date is None
                assert config.date_range.end_date is None
                
            finally:
                os.unlink(f.name)

    @patch('builtins.open', side_effect=FileNotFoundError())
    def test_config_from_file_not_found(self, mock_file):
        """Test Config.from_file with missing file."""
        with pytest.raises(FileNotFoundError):
            Config.from_file(Path("/nonexistent/config.toml"))

    def test_config_validation_basic(self):
        """Test basic config validation."""
        config = Config.default()
        
        # Default config should validate (though may fail on file paths)
        results = config.get_validation_results()
        
        # Check that we get expected validation keys
        expected_keys = [
            "Poll interval is positive",
            "Startup lookback is positive", 
            "Max batch size is positive",
            "Outbound method is valid",
            "Rate limit is positive",
            "Database URL is not empty",
            "Database pool settings are valid",
            "Phone numbers list is valid"
        ]
        
        for key in expected_keys:
            assert key in results
            assert results[key] is True

    def test_config_validation_invalid_settings(self):
        """Test config validation with invalid settings."""
        config = Config.default()
        
        # Make some settings invalid
        config.monitoring.poll_interval_seconds = 0
        config.monitoring.startup_lookback_hours = -1
        config.monitoring.max_batch_size = 0
        config.outbound.method = "invalid_method"
        config.outbound.rate_limit_per_minute = -1
        config.database.url = ""
        config.database.pool_size = 0
        
        results = config.get_validation_results()
        
        assert results["Poll interval is positive"] is False
        assert results["Startup lookback is positive"] is False
        assert results["Max batch size is positive"] is False
        assert results["Outbound method is valid"] is False
        assert results["Rate limit is positive"] is False
        assert results["Database URL is not empty"] is False
        assert results["Database pool settings are valid"] is False

    def test_config_validate_method(self):
        """Test config.validate() method."""
        config = Config.default()
        
        # Mock file system checks to return True
        with patch.object(config, '_test_database_readability', return_value=True):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('pathlib.Path.is_file', return_value=True):
                    with patch('pathlib.Path.is_dir', return_value=True):
                        assert config.validate() is True

    def test_config_validate_method_false(self):
        """Test config.validate() method returning False."""
        config = Config.default()
        
        # Make one setting invalid
        config.monitoring.poll_interval_seconds = 0
        
        assert config.validate() is False

    @patch('builtins.open', mock_open(read_data=b"SQLite format 3"))
    def test_test_database_readability_success(self):
        """Test _test_database_readability with successful read."""
        config = Config.default()
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.is_file', return_value=True):
                result = config._test_database_readability(Path("/fake/path"))
                assert result is True

    @patch('builtins.open', side_effect=PermissionError())
    def test_test_database_readability_permission_error(self, mock_file):
        """Test _test_database_readability with permission error."""
        config = Config.default()
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.is_file', return_value=True):
                result = config._test_database_readability(Path("/fake/path"))
                assert result is False

    def test_test_database_readability_file_not_exists(self):
        """Test _test_database_readability with non-existent file."""
        config = Config.default()
        
        with patch('pathlib.Path.exists', return_value=False):
            result = config._test_database_readability(Path("/fake/path"))
            assert result is False

    def test_config_save(self):
        """Test config.save() method."""
        config = Config.default()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "subdir" / "config.toml"
            
            # Should create directory
            config.save(config_path)
            
            # Directory should exist
            assert config_path.parent.exists()
            assert config_path.parent.is_dir()


class TestConfigManager:
    """Test ConfigManager functionality."""

    def test_config_manager_init_default_path(self):
        """Test ConfigManager initialization with default path."""
        manager = ConfigManager()
        
        expected_path = Path.home() / ".imessage_monitor" / "config.toml"
        assert manager.config_path == expected_path
        assert manager.config is None

    def test_config_manager_init_custom_path(self):
        """Test ConfigManager initialization with custom path."""
        custom_path = Path("/custom/path/config.toml")
        manager = ConfigManager(custom_path)
        
        assert manager.config_path == custom_path
        assert manager.config is None

    def test_config_manager_load_config_file_exists(self):
        """Test ConfigManager.load_config with existing file."""
        toml_content = """
[database]
url = "postgresql://user:pass@localhost/test_db"

[apple]
chat_db_path = "/test/path/chat.db"
attachments_path = "/test/path/attachments"

[monitoring]
poll_interval_seconds = 5
startup_lookback_hours = 12
max_batch_size = 50
enable_real_time = false

[contacts]
phone_numbers = []
include_unknown = true
group_chats = true

[date_range]

[outbound]
method = "applescript"
rate_limit_per_minute = 30
enable_auto_reply = false
auto_reply_triggers = []
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(toml_content)
            f.flush()
            
            try:
                manager = ConfigManager(Path(f.name))
                config = manager.load_config()
                
                assert config.database.url == "postgresql://user:pass@localhost/test_db"
                assert config.monitoring.poll_interval_seconds == 5
                assert manager.config == config
                
            finally:
                os.unlink(f.name)

    def test_config_manager_load_config_file_not_exists(self):
        """Test ConfigManager.load_config with non-existent file."""
        manager = ConfigManager(Path("/nonexistent/config.toml"))
        config = manager.load_config()
        
        # Should return default config
        assert isinstance(config, Config)
        assert config.monitoring.poll_interval_seconds == 3  # Default value
        assert manager.config == config

    def test_config_manager_load_and_validate_config_valid(self):
        """Test ConfigManager.load_and_validate_config with valid config."""
        manager = ConfigManager(Path("/nonexistent/config.toml"))
        
        # Mock validation to return True
        with patch.object(Config, 'validate', return_value=True):
            config = manager.load_and_validate_config()
            assert isinstance(config, Config)

    def test_config_manager_load_and_validate_config_invalid(self):
        """Test ConfigManager.load_and_validate_config with invalid config."""
        manager = ConfigManager(Path("/nonexistent/config.toml"))
        
        # Mock validation to return False
        with patch.object(Config, 'validate', return_value=False):
            with pytest.raises(ValueError, match="Invalid configuration"):
                manager.load_and_validate_config()

    def test_config_manager_create_default_config(self):
        """Test ConfigManager.create_default_config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"
            manager = ConfigManager(config_path)
            
            config = manager.create_default_config()
            
            assert isinstance(config, Config)
            assert manager.config == config
            assert config.monitoring.poll_interval_seconds == 3  # Default value

    @patch('builtins.open', mock_open(read_data=b"test"))
    def test_config_manager_validate_permissions_success(self):
        """Test ConfigManager.validate_permissions with success."""
        manager = ConfigManager()
        manager.config = Config.default()
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.is_file', return_value=True):
                result = manager.validate_permissions()
                assert result is True

    @patch('builtins.open', side_effect=PermissionError())
    def test_config_manager_validate_permissions_permission_error(self, mock_file):
        """Test ConfigManager.validate_permissions with permission error."""
        manager = ConfigManager()
        manager.config = Config.default()
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.is_file', return_value=True):
                result = manager.validate_permissions()
                assert result is False

    def test_config_manager_validate_permissions_no_config(self):
        """Test ConfigManager.validate_permissions with no config loaded."""
        manager = ConfigManager()
        result = manager.validate_permissions()
        assert result is False

    def test_config_manager_get_apple_db_path(self):
        """Test ConfigManager.get_apple_db_path."""
        manager = ConfigManager()
        manager.config = Config.default()
        
        result = manager.get_apple_db_path()
        expected = Path.home() / "Library" / "Messages" / "chat.db"
        assert result == expected

    def test_config_manager_get_apple_db_path_no_config(self):
        """Test ConfigManager.get_apple_db_path with no config."""
        manager = ConfigManager()
        
        with pytest.raises(ValueError, match="Config not loaded"):
            manager.get_apple_db_path()


class TestGlobalConfigFunctions:
    """Test global configuration functions."""

    def test_init_config_default_path(self):
        """Test init_config with default path."""
        # Clean up any existing global config
        import imessage_monitor.config as config_module
        config_module._config_manager = None
        config_module._current_config = None
        
        with patch('pathlib.Path.exists', return_value=False):
            config = init_config()
            
            assert isinstance(config, Config)
            assert config.monitoring.poll_interval_seconds == 3  # Default value

    def test_init_config_custom_path(self):
        """Test init_config with custom path."""
        # Clean up any existing global config
        import imessage_monitor.config as config_module
        config_module._config_manager = None
        config_module._current_config = None
        
        custom_path = Path("/custom/config.toml")
        
        with patch('pathlib.Path.exists', return_value=False):
            config = init_config(custom_path)
            
            assert isinstance(config, Config)

    def test_get_config_initialized(self):
        """Test get_config after initialization."""
        # Clean up any existing global config
        import imessage_monitor.config as config_module
        config_module._config_manager = None
        config_module._current_config = None
        
        with patch('pathlib.Path.exists', return_value=False):
            init_config()
            config = get_config()
            
            assert isinstance(config, Config)

    def test_get_config_not_initialized(self):
        """Test get_config without initialization."""
        # Clean up any existing global config
        import imessage_monitor.config as config_module
        config_module._config_manager = None
        config_module._current_config = None
        
        with pytest.raises(ValueError, match="Config not initialized"):
            get_config()

    def test_load_config_from_file(self):
        """Test load_config_from_file function."""
        toml_content = """
[database]
url = "postgresql://user:pass@localhost/test_db"

[apple]
chat_db_path = "/test/path/chat.db"
attachments_path = "/test/path/attachments"

[monitoring]
poll_interval_seconds = 5
startup_lookback_hours = 12
max_batch_size = 50
enable_real_time = false

[contacts]
phone_numbers = []
include_unknown = true
group_chats = true

[date_range]

[outbound]
method = "applescript"
rate_limit_per_minute = 30
enable_auto_reply = false
auto_reply_triggers = []
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(toml_content)
            f.flush()
            
            try:
                config = load_config_from_file(Path(f.name))
                
                assert config.database.url == "postgresql://user:pass@localhost/test_db"
                assert config.monitoring.poll_interval_seconds == 5
                
            finally:
                os.unlink(f.name)

    def test_create_default_config_no_save(self):
        """Test create_default_config without saving."""
        config = create_default_config()
        
        assert isinstance(config, Config)
        assert config.monitoring.poll_interval_seconds == 3  # Default value

    def test_create_default_config_with_save(self):
        """Test create_default_config with saving."""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "config.toml"
            
            config = create_default_config(save_path)
            
            assert isinstance(config, Config)
            # Directory should be created
            assert save_path.parent.exists()