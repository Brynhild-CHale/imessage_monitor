# iMessage Monitor

A Python library for monitoring and extracting iMessage data with real-time capabilities and beautiful terminal display.

## Features

- **Real-time monitoring** of incoming iMessages
- **Pretty-printed chat bubbles** with proper left/right alignment
- **Sticker and reaction support** with emoji display
- **ASCII art generation** for image attachments (optional)
- **Attachment handling** including HEIC conversion
- **Outbound messaging** via AppleScript or Shortcuts
- **Safe database access** with read-only mode

## Requirements

- **macOS only** (requires access to Messages database)
- **Python 3.11+**
- **Full Disk Access** permission for terminal/IDE

## Installation

```bash
pip install imessage-monitor

or

uv add imessage-monitor
```


## Quick Start

### Real-time Monitoring

```python
from imessage_monitor import iMessageMonitor
from imessage_monitor.display import pretty_print_bubble

def handle_message(message):
    """Handle new messages with pretty printing."""
    print(pretty_print_bubble(message, show_ascii_art=True))

# Start monitoring
monitor = iMessageMonitor()
monitor.start(message_callback=handle_message)

# Keep running (in practice, you'd run this in an async loop)
input("Press Enter to stop...")
monitor.stop()
```

### Message Retrieval

```python
from imessage_monitor import iMessageMonitor, to_json

# Get recent messages
monitor = iMessageMonitor()
messages = monitor.get_recent_messages(limit=50)

# Convert to JSON
json_data = to_json(messages)
print(json_data)
```

### Sending Messages

```python
from imessage_monitor import ImessageOutbound

# Send via AppleScript
outbound = ImessageOutbound()
success = outbound.send_message_applescript("+1234567890", "Hello!")

# Send attachment
success = outbound.send_attachment_applescript("+1234567890", "/path/to/file.jpg")
```

## Display Options

The library provides three pretty-print formats:

### Chat Bubbles
```python
from imessage_monitor.display import pretty_print_bubble

# Basic bubble (no ASCII art)
print(pretty_print_bubble(message))

# With ASCII art for images
print(pretty_print_bubble(message, show_ascii_art=True))
```

### Reactions
```python
from imessage_monitor.display import pretty_print_reaction

print(pretty_print_reaction(message))  # Shows ❤️, 👍, 👎, etc.
```

### Stickers
```python
from imessage_monitor.display import pretty_print_sticker

print(pretty_print_sticker(message, show_ascii_art=True))
```

## Data Conversion

```python
from imessage_monitor import to_json, to_toml

# Convert messages to different formats
json_str = to_json(messages)
toml_str = to_toml(messages)

# Save to files
to_json(messages, "messages.json")
to_toml(messages, "messages.toml")
```

## Configuration

The library uses sensible defaults but can be configured:

```python
from imessage_monitor.config import Config

# Create custom config
config = Config.default()
config.monitoring.poll_interval_seconds = 1  # Faster polling

monitor = iMessageMonitor(config_path="path/to/config.toml")
```

### Contact Filtering

Filter messages by specific contacts with whitelist/blacklist functionality:

```python
from imessage_monitor import iMessageMonitor
from imessage_monitor.config import ContactFilter

# Create contact filter
contact_filter = ContactFilter(
    outbound_behavior="whitelist",  # Only include outbound messages to these contacts
    outbound_ids=["+1234567890", "friend@example.com"],
    inbound_behavior="blacklist",   # Exclude inbound messages from these contacts
    inbound_ids=["spam@example.com", "+9876543210"]
)

# Apply filter to message retrieval
config = Config.default()
config.contacts = contact_filter
monitor = iMessageMonitor()
filtered_messages = monitor.get_recent_messages(limit=100)
```

Contact filtering supports:
- **Chat-level filtering**: Group chats can be whitelisted/blacklisted by chat ID
- **Individual-level filtering**: Individual contacts filtered by phone/email
- **Precedence**: Chat-level filtering takes precedence over individual-level
- **Directional filtering**: Separate rules for inbound vs outbound messages

### Date Range Filtering

Filter messages by date range (applies to manual queries only, not monitoring):

```python
from imessage_monitor.config import DateRange
from datetime import datetime

# Custom date range
date_range = DateRange(
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31)
)

# Quick helpers
date_range = DateRange.from_days_back(7)    # Last 7 days
date_range = DateRange.from_hours_back(24)  # Last 24 hours

config = Config.default()
config.date_range = date_range
monitor = iMessageMonitor()
recent_messages = monitor.get_recent_messages(limit=100)
```

### Example TOML Configuration

```toml
[apple]
chat_db_path = "~/Library/Messages/chat.db"
attachments_path = "~/Library/Messages/Attachments"
permissions_check = true

[monitoring]
poll_interval_seconds = 20 # Used as backup if enable_real_time=true
max_batch_size = 1000
enable_real_time = true

[contacts]
outbound_behavior = "whitelist" # "whitelist" | "blacklist" | "none"
outbound_ids = ["+1234567890", "friend@example.com"]
inbound_behavior = "blacklist" # "whitelist" | "blacklist" | "none"  
inbound_ids = ["spam@example.com", "+9876543210"]

[date_range] # Ignored when monitoring
start_date = "2024-01-01T00:00:00"
end_date = "2024-12-31T23:59:59"

[outbound]
method = "applescript"
rate_limit_per_minute = 30
```

## Permissions

### Required: Full Disk Access

1. Open **System Preferences** � **Security & Privacy** � **Privacy**
2. Select **Full Disk Access** 
3. Add your terminal application (Terminal.app, iTerm2, etc.)
4. Add your IDE if running from there (VS Code, PyCharm, etc.)

### Optional: Shortcuts (for outbound messaging)

For Shortcuts-based messaging, create these shortcuts in the Shortcuts app:
- "Send Message" - Not Yet Implemented
- "Send Attachment" - Not Yet Implemented

## Platform Support

- **macOS**: Supported
- **Windows/Linux**: Not supported L (requires macOS Messages database)


## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request


## Troubleshooting

### "Database not found" error
- Ensure you're running on macOS
- Check Full Disk Access permissions
- Verify Messages app has been used at least once

### "Permission denied" error  
- Add Full Disk Access for your terminal/IDE
- Restart terminal after adding permissions

### ASCII art not showing
- Ensure `ascii-magic` is installed
- Enable with `show_ascii_art=True` parameter
- Check image file accessibility

## Examples

See `example_usage.py` for a complete real-time monitoring application.

## Security Note

This library accesses your Messages database in read-only mode for monitoring. It does not modify or delete any messages. Outbound messaging requires explicit function calls and uses standard macOS APIs.