"""Custom exceptions for iMessage Monitor."""


class iMessageMonitorError(Exception):
    """Base exception for iMessage Monitor."""
    pass


class ConfigurationError(iMessageMonitorError):
    """Configuration-related errors."""
    pass


class AppleDatabaseError(iMessageMonitorError):
    """Apple database access errors."""
    pass


class PermissionError(iMessageMonitorError):
    """macOS permission errors."""
    pass


class MessageProcessingError(iMessageMonitorError):
    """Message processing errors."""
    pass


class StorageError(iMessageMonitorError):
    """Storage/database errors."""
    pass


class OutboundMessageError(iMessageMonitorError):
    """Outbound message sending errors."""
    pass


class MonitoringError(iMessageMonitorError):
    """General monitoring errors."""
    pass