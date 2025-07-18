"""Configuration management for iMessage Monitor."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict
import tomllib


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    url: str
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    enable_storage: bool = False


@dataclass
class AppleConfig:
    """Apple iMessage database configuration."""
    chat_db_path: str
    attachments_path: str
    permissions_check: bool = True


@dataclass
class MonitoringConfig:
    """Message monitoring configuration."""
    poll_interval_seconds: int = 3
    startup_lookback_hours: int = 24
    max_batch_size: int = 100
    enable_real_time: bool = True


@dataclass
class ContactFilter:
    """Contact filtering configuration."""
    phone_numbers: List[str]
    include_unknown: bool = True
    group_chats: bool = True


@dataclass
class DateRange:
    """Date range filtering configuration."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    @classmethod
    def from_hours_back(cls, hours: int) -> 'DateRange':
        """Create date range from hours back to now."""
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=hours)
        return cls(start_date=start_date, end_date=end_date)
    
    @classmethod
    def from_days_back(cls, days: int) -> 'DateRange':
        """Create date range from days back to now."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        return cls(start_date=start_date, end_date=end_date)


@dataclass
class OutboundConfig:
    """Outbound messaging configuration."""
    method: str = "applescript"  # "applescript", "shortcuts"
    rate_limit_per_minute: int = 30
    enable_auto_reply: bool = False
    auto_reply_triggers: Optional[List[str]] = None


@dataclass
class Config:
    """Main configuration class."""
    database: DatabaseConfig
    apple: AppleConfig
    monitoring: MonitoringConfig
    contacts: ContactFilter
    date_range: DateRange
    outbound: OutboundConfig
    
    @classmethod
    def from_file(cls, config_path: Path) -> 'Config':
        """Load configuration from TOML file."""
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
        
        # Parse date range
        date_range_data = data.get("date_range", {})
        start_date = None
        end_date = None
        if "start_date" in date_range_data:
            start_date = datetime.fromisoformat(date_range_data["start_date"])
        if "end_date" in date_range_data:
            end_date = datetime.fromisoformat(date_range_data["end_date"])
        
        return cls(
            database=DatabaseConfig(**data["database"]),
            apple=AppleConfig(**data["apple"]),
            monitoring=MonitoringConfig(**data["monitoring"]),
            contacts=ContactFilter(**data["contacts"]),
            date_range=DateRange(start_date=start_date, end_date=end_date),
            outbound=OutboundConfig(**data["outbound"])
        )
    
    @classmethod
    def default(cls) -> 'Config':
        """Create default configuration."""
        return cls(
            database=DatabaseConfig(
                url="postgresql://user:pass@localhost/imessage_db"
            ),
            apple=AppleConfig(
                chat_db_path=str(Path.home() / "Library" / "Messages" / "chat.db"),
                attachments_path=str(Path.home() / "Library" / "Messages" / "Attachments")
            ),
            monitoring=MonitoringConfig(),
            contacts=ContactFilter(phone_numbers=[]),
            date_range=DateRange(),
            outbound=OutboundConfig(auto_reply_triggers=[])
        )
    
    def validate(self) -> bool:
        """Validate configuration settings."""
        validation_results = self.get_validation_results()
        return all(validation_results.values())
    
    def get_validation_results(self) -> Dict[str, bool]:
        """Get detailed validation results for each check."""
        results = {}
        
        # Apple database path validation
        apple_db_path = Path(self.apple.chat_db_path).expanduser()
        results["Apple chat.db exists"] = apple_db_path.exists()
        results["Apple chat.db is file"] = apple_db_path.exists() and apple_db_path.is_file()
        
        # Test actual readability (Full Disk Access requirement)
        results["Apple chat.db is readable"] = self._test_database_readability(apple_db_path)
        
        # Apple attachments path validation
        attachments_path = Path(self.apple.attachments_path).expanduser()
        results["Apple attachments directory exists"] = attachments_path.exists()
        results["Apple attachments directory is accessible"] = attachments_path.exists() and attachments_path.is_dir()
        
        # Monitoring configuration validation
        results["Poll interval is positive"] = self.monitoring.poll_interval_seconds > 0
        results["Startup lookback is positive"] = self.monitoring.startup_lookback_hours >= 0
        results["Max batch size is positive"] = self.monitoring.max_batch_size > 0
        
        # Outbound configuration validation
        results["Outbound method is valid"] = self.outbound.method in ["applescript", "shortcuts"]
        results["Rate limit is positive"] = self.outbound.rate_limit_per_minute > 0
        
        # Database URL validation (basic)
        results["Database URL is not empty"] = bool(self.database.url.strip())
        results["Database pool settings are valid"] = (
            self.database.pool_size > 0 and 
            self.database.max_overflow >= 0 and 
            self.database.pool_timeout > 0
        )
        
        # Contact filter validation
        results["Phone numbers list is valid"] = isinstance(self.contacts.phone_numbers, list)
        
        return results
    
    def _test_database_readability(self, db_path: Path) -> bool:
        """Test if we can actually read the database file (requires Full Disk Access)."""
        if not db_path.exists() or not db_path.is_file():
            return False
        
        try:
            # Simple test: try to read first 10 bytes of the file
            with open(db_path, 'rb') as f:
                data = f.read(10)
                # Should read some data (SQLite files start with "SQLite format 3")
                return len(data) > 0
        except (PermissionError, OSError):
            # Permission denied or other file access error
            return False
        except Exception:
            # Any other error still means we could open the file
            return True
    
    def save(self, config_path: Path) -> None:
        """Save configuration to TOML file."""
        # Note: This would require a TOML writer library
        # For now, just create the directory
        config_path.parent.mkdir(parents=True, exist_ok=True)


class ConfigManager:
    """Manages configuration loading and validation."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path.home() / ".imessage_monitor" / "config.toml"
        self.config: Optional[Config] = None
    
    def load_config(self) -> Config:
        """Load configuration (validation is separate)."""
        if self.config_path.exists():
            self.config = Config.from_file(self.config_path)
        else:
            self.config = Config.default()
        
        return self.config
    
    def load_and_validate_config(self) -> Config:
        """Load and validate configuration, raising exception on failure."""
        config = self.load_config()
        if not config.validate():
            raise ValueError("Invalid configuration")
        return config
    
    def create_default_config(self) -> Config:
        """Create and save default configuration."""
        self.config = Config.default()
        self.config.save(self.config_path)
        return self.config
    
    def validate_permissions(self) -> bool:
        """Validate required macOS permissions."""
        if not self.config:
            return False
        
        # Check if we can read the Apple database
        db_path = Path(self.config.apple.chat_db_path).expanduser()
        if not db_path.exists() or not db_path.is_file():
            return False
        
        try:
            # Try to open the database file
            with open(db_path, 'rb') as f:
                f.read(1)
            return True
        except PermissionError:
            return False
    
    def get_apple_db_path(self) -> Path:
        """Get Apple iMessage database path."""
        if not self.config:
            raise ValueError("Config not loaded")
        return Path(self.config.apple.chat_db_path).expanduser()


# Global config instance for easy access across modules
_config_manager: Optional[ConfigManager] = None
_current_config: Optional[Config] = None


def init_config(config_path: Optional[Path] = None) -> Config:
    """Initialize global configuration."""
    global _config_manager, _current_config
    _config_manager = ConfigManager(config_path)
    _current_config = _config_manager.load_config()
    return _current_config


def get_config() -> Config:
    """Get current configuration."""
    if _current_config is None:
        raise ValueError("Config not initialized. Call init_config() first.")
    return _current_config


def load_config_from_file(config_path: Path) -> Config:
    """Load configuration from specific file."""
    return Config.from_file(config_path)


def create_default_config(save_path: Optional[Path] = None) -> Config:
    """Create default configuration."""
    config = Config.default()
    if save_path:
        config.save(save_path)
    return config