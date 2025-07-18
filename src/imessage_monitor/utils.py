"""Utility functions for data conversion and serialization."""

import json
import base64
import copy
from datetime import datetime, timedelta
from typing import Dict, List, Any


# Date/Time Conversion
def apple_timestamp_to_datetime(apple_ts: int) -> datetime:
    """Convert Apple's timestamp format (nanoseconds since 2001-01-01)."""
    # Apple Core Data timestamp: nanoseconds since 2001-01-01 00:00:00 UTC
    # Convert to seconds and add to epoch
    apple_epoch = datetime(2001, 1, 1)
    seconds = apple_ts / 1_000_000_000  # Convert nanoseconds to seconds
    return apple_epoch + timedelta(seconds=seconds)


def datetime_to_apple_timestamp(dt: datetime) -> int:
    """Reverse conversion for queries."""
    # Convert datetime to Apple timestamp format
    apple_epoch = datetime(2001, 1, 1)
    diff = dt - apple_epoch
    return int(diff.total_seconds() * 1_000_000_000)  # Convert to nanoseconds


def prepare_data_for_serialization(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Prepare data for serialization by converting non-serializable types."""
    
    def clean_value(value):
        """Recursively clean values to make them serializable."""
        if isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, bytes):
            # Convert bytes to base64
            return base64.b64encode(value).decode('utf-8')
        elif value is None:
            # Convert None to empty string for TOML compatibility
            return ""
        elif hasattr(value, '__dict__') and hasattr(value, '__class__'):
            # Handle objects like UID, etc.
            if hasattr(value, '__str__'):
                return str(value)
            else:
                return str(type(value).__name__)
        elif isinstance(value, dict):
            # Recursively clean dictionary values
            return {k: clean_value(v) for k, v in value.items()}
        elif isinstance(value, (list, tuple)):
            # Recursively clean list/tuple values
            return [clean_value(item) for item in value]
        else:
            return value
    
    # Create a deep copy to avoid modifying original data
    serializable_messages = copy.deepcopy(messages)
    
    for msg in serializable_messages:
        for key, value in msg.items():
            msg[key] = clean_value(value)
    
    return serializable_messages


def to_json(messages: List[Dict[str, Any]], filename: str = None) -> str:
    """Convert messages to JSON format.
    
    Args:
        messages: List of message dictionaries
        filename: Optional filename to save to. If None, returns JSON string.
    
    Returns:
        JSON string representation of messages
    """
    serializable_data = prepare_data_for_serialization(messages)
    json_str = json.dumps(serializable_data, indent=2, default=str)
    
    if filename:
        with open(filename, 'w') as f:
            f.write(json_str)
        print(f"Messages saved to {filename}")
    
    return json_str


def to_toml(messages: List[Dict[str, Any]], filename: str = None) -> str:
    """Convert messages to TOML format.
    
    Args:
        messages: List of message dictionaries
        filename: Optional filename to save to. If None, returns TOML string.
    
    Returns:
        TOML string representation of messages
    """
    try:
        import tomli_w
    except ImportError:
        raise ImportError("tomli_w is required for TOML export. Install with: pip install tomli-w")
    
    serializable_data = prepare_data_for_serialization(messages)
    
    # TOML requires a top-level dictionary, so wrap the messages list
    toml_data = {"messages": serializable_data}
    
    if filename:
        with open(filename, 'wb') as f:
            tomli_w.dump(toml_data, f)
        print(f"Messages saved to {filename}")
        
        # Also return as string for consistency
        import io
        toml_bytes = io.BytesIO()
        tomli_w.dump(toml_data, toml_bytes)
        return toml_bytes.getvalue().decode('utf-8')
    else:
        # Return as string
        import io
        toml_bytes = io.BytesIO()
        tomli_w.dump(toml_data, toml_bytes)
        return toml_bytes.getvalue().decode('utf-8')