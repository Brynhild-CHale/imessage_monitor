# iMessage Monitor

A Python library for monitoring and extracting iMessage data with real-time capabilities and beautiful terminal display.

## Features

- = **Real-time monitoring** of incoming iMessages
- =� **Pretty-printed chat bubbles** with proper left/right alignment
- <� **Sticker and reaction support** with emoji display
- =� **ASCII art generation** for image attachments (optional)
- =� **Attachment handling** including HEIC conversion
- =� **Outbound messaging** via AppleScript or Shortcuts
- =� **Safe database access** with read-only mode

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

print(pretty_print_reaction(message))  # Shows d, =M, =, etc.
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