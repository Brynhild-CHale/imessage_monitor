"""iMessage Monitor - A focused library for extracting and monitoring iMessage data."""

from .monitor import iMessageMonitor
from .utils import to_json, to_toml
from .config import Config
from .outbound import OutboundMessageSender, ImessageOutbound
from .exceptions import iMessageMonitorError, ConfigurationError

__version__ = "0.1.0"
__all__ = [
    "iMessageMonitor",
    "to_json", 
    "to_toml",
    "Config",
    "OutboundMessageSender",
    "ImessageOutbound",
    "iMessageMonitorError",
    "ConfigurationError"
]