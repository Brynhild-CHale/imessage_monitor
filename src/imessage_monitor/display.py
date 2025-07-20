"""Display and formatting functions for iMessage Monitor."""
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from .config import Config
from .utils import format_apple_timestamp_for_display, is_supported_file_type, resolve_attachment_file_path

# Constants
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic', '.heif'}

# iMessage reaction type mappings
REACTION_EMOJIS = {
    2000: "❤️",    # Love
    2001: "👍",    # Like  
    2002: "👎",    # Dislike
    2003: "😂",    # Laugh
    2004: "‼️",    # Emphasis
    2005: "❓",    # Question
    3000: "💔",    # Remove Love
    3001: "👎",    # Remove Like
    3002: "👍",    # Remove Dislike
    3003: "😐",    # Remove Laugh
    3004: "📍",    # Remove Emphasis
    3005: "❔",    # Remove Question
}

# TODO: Implement live message logging functionality for CLI
# - format_message_for_log() for terminal display of incoming/outgoing messages
# - format_attachment_for_log() for attachment transfers
# - format_system_event() and format_error_message() for daemon events


# Terminal Width Helpers
def get_terminal_width() -> int:
    """Get current terminal width."""
    import shutil
    try:
        return shutil.get_terminal_size().columns
    except:
        return 80  # Fallback if terminal size detection fails


def get_optimal_ascii_width() -> int:
    """Get optimal ASCII art width (80% of terminal)."""
    terminal_width = get_terminal_width()
    return max(30, int(terminal_width * 0.8))


def get_optimal_text_width() -> int:
    """Get optimal text bubble width (60% of terminal)."""
    terminal_width = get_terminal_width()
    return max(40, int(terminal_width * 0.6))


def format_attachment_for_bubble(
    image_attachments: List[Dict[str, Any]], 
    max_content_width: int,
    left_padding: str,
    show_ascii_art: bool = False
) -> List[str]:
    """Format image attachments for bubble display.
    
    Args:
        image_attachments: List of image attachment dictionaries
        max_content_width: Maximum width for content
        left_padding: Left padding string for alignment
        show_ascii_art: Whether to show ASCII art for images
        
    Returns:
        List of formatted lines for the bubble
    """
    if not image_attachments:
        return []
    
    lines = []
    lines.append(left_padding + '│' + ' ' * (max_content_width + 2) + '│')
    
    # Show first image only
    for attachment in image_attachments[:1]:
        ascii_art = get_ascii_art_for_attachment(attachment, enable_ascii=show_ascii_art)
        art_lines = ascii_art.split('\n')
        
        for art_line in art_lines:
            # Truncate if line is too long
            if len(art_line) > max_content_width:
                art_line = art_line[:max_content_width]
            
            # Calculate padding for this line
            art_padding = max_content_width - len(art_line)
            lines.append(left_padding + '│ ' + art_line + ' ' * art_padding + ' │')
    
    return lines


def convert_heic_to_temp_png(file_path: Path) -> str:
    """Convert HEIC/HEIF file to temporary PNG.
    
    Args:
        file_path: Path to HEIC/HEIF file
        
    Returns:
        Path to temporary PNG file
        
    Raises:
        ImportError: If pillow-heif not available
        Exception: If conversion fails
    """
    try:
        import pillow_heif
        from PIL import Image
        import tempfile
        
        # Register HEIF opener with Pillow
        pillow_heif.register_heif_opener()
        
        # Open HEIC file and convert to RGB
        with Image.open(str(file_path)) as img:
            rgb_img = img.convert('RGB')
            
            # Create temporary PNG file
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                rgb_img.save(temp_file.name, 'PNG')
                return temp_file.name
                
    except ImportError:
        raise ImportError("pillow-heif not available for HEIC conversion - install with: uv add pillow-heif")
    except Exception as e:
        raise Exception(f"HEIC conversion error: {str(e)}")


def generate_ascii_art(file_path: Path, columns: int) -> str:
    """Generate ASCII art from image file.
    
    Args:
        file_path: Path to image file
        columns: Width in characters for ASCII art
        
    Returns:
        Empty string (ASCII art is printed to terminal)
        
    Raises:
        ImportError: If ascii_magic not available
        Exception: If ASCII generation fails
    """
    try:
        from ascii_magic import AsciiArt
        
        my_art = AsciiArt.from_image(str(file_path))
        my_art.to_terminal(columns=columns)
        return ""
        
    except ImportError:
        raise ImportError("ascii_magic not available - install with: uv add ascii-magic")
    except Exception as e:
        raise Exception(f"Error generating ASCII art: {str(e)}")


def get_ascii_art_for_attachment(attachment: Dict[str, Any], columns: int = None, enable_ascii: bool = False) -> str:
    """Convert image attachment to ASCII art (orchestrator function).
    
    Args:
        attachment: Attachment dictionary with filename and file path
        columns: Width of ASCII art in characters (None for auto-detect)
        enable_ascii: Whether to generate ASCII art (default: False)
        
    Returns:
        ASCII art string, file info, or error message
    """
    filename = attachment.get('filename', '')
    if not filename:
        return "[No filename available]"
    
    # If ASCII art is disabled, return simple file info
    if not enable_ascii:
        file_ext = Path(filename).suffix.upper()
        return f"[📷 {file_ext} Image: {Path(filename).name}]"
    
    # Use optimal width if not specified
    if columns is None:
        columns = get_optimal_ascii_width()
    
    # Check if it's a supported image format
    if not is_supported_file_type(filename, IMAGE_EXTENSIONS):
        return f"[Non-image file: {filename}]"
    
    try:
        # Resolve file path
        file_path = resolve_attachment_file_path(filename)
        
        # Handle HEIC/HEIF files with conversion
        file_ext = Path(filename).suffix.lower()
        temp_file_to_cleanup = None
        
        if file_ext in {'.heic', '.heif'}:
            try:
                temp_png_path = convert_heic_to_temp_png(file_path)
                temp_file_to_cleanup = temp_png_path
                file_path = Path(temp_png_path)
            except (ImportError, Exception) as e:
                return f"[{str(e)}]"
        
        # Generate ASCII art
        try:
            generate_ascii_art(file_path, columns)
            return ""
        except (ImportError, Exception) as e:
            return f"[{str(e)}]"
        finally:
            # Clean up temporary file if created
            if temp_file_to_cleanup:
                Path(temp_file_to_cleanup).unlink(missing_ok=True)
                
    except FileNotFoundError as e:
        return f"[{str(e)}]"
    except Exception as e:
        return f"[Error processing attachment: {str(e)}]"


# Pretty Print Types
def pretty_print_bubble(message: Dict[str, Any], width: int = None, show_ascii_art: bool = False) -> str:
    """Format message as a chat bubble for terminal display.
    
    Args:
        message: Message dictionary from iMessageMonitor
        width: Maximum width of the bubble (None for auto-detect at 60% of terminal)
        show_ascii_art: Whether to show ASCII art for image attachments (default: False)
        
    Returns:
        Formatted bubble string
    """
    # Use optimal text width if not specified
    if width is None:
        width = get_optimal_text_width()
    # Extract message info
    content = message.get('message_text') or message.get('decoded_attributed_body') or '[No content]'
    is_from_me = message.get('is_from_me', False)
    handle_id = message.get('handle_id_str', 'Unknown')
    timestamp = message.get('date', 0)
    
    # Format timestamp (convert from Apple timestamp if needed)
    time_str = format_apple_timestamp_for_display(timestamp)
    
    # Prepare content lines
    content_lines = []
    for line in str(content).split('\n'):
        while len(line) > width - 4:  # Account for bubble padding
            content_lines.append(line[:width-4])
            line = line[width-4:]
        if line:
            content_lines.append(line)
    
    if not content_lines:
        content_lines = ['[Empty message]']
    
    # Check for image attachments
    attachments = message.get('parsed_attachments', [])
    image_attachments = []
    for attachment in attachments:
        if attachment.get('filename'):
            if is_supported_file_type(attachment['filename'], IMAGE_EXTENSIONS):
                image_attachments.append(attachment)
    
    # Build bubble
    bubble_lines = []
    
    if is_from_me:
        # Right-aligned bubble (outgoing)
        max_len = max(len(line) for line in content_lines)
        padding = width - max_len - 4
        
        # Top of bubble
        bubble_lines.append(' ' * padding + '┌' + '─' * (max_len + 2) + '┐')
        
        # Content lines
        for line in content_lines:
            line_padding = max_len - len(line)
            bubble_lines.append(' ' * padding + '│ ' + line + ' ' * line_padding + ' │')
        
        # Add ASCII art for image attachments
        if image_attachments:
            attachment_lines = format_attachment_for_bubble(
                image_attachments, max_len, ' ' * padding, show_ascii_art
            )
            bubble_lines.extend(attachment_lines)
        
        # Bottom with tail
        bubble_lines.append(' ' * padding + '└' + '─' * (max_len + 2) + '┘')
        bubble_lines.append(' ' * (padding + max_len + 2) + '\\')
        
        # Sender info (right-aligned)
        sender_info = f"You • {time_str}"
        info_padding = width - len(sender_info)
        bubble_lines.append(' ' * info_padding + sender_info)
        
    else:
        # Left-aligned bubble (incoming)
        max_len = max(len(line) for line in content_lines)
        
        # Sender info (left-aligned)
        sender_info = f"{handle_id} • {time_str}"
        bubble_lines.append(sender_info)
        
        # Top with tail
        bubble_lines.append('/')
        bubble_lines.append('┌' + '─' * (max_len + 2) + '┐')
        
        # Content lines
        for line in content_lines:
            line_padding = max_len - len(line)
            bubble_lines.append('│ ' + line + ' ' * line_padding + ' │')
        
        # Add ASCII art for image attachments
        if image_attachments:
            attachment_lines = format_attachment_for_bubble(
                image_attachments, max_len, '', show_ascii_art
            )
            bubble_lines.extend(attachment_lines)
        
        # Bottom of bubble
        bubble_lines.append('└' + '─' * (max_len + 2) + '┘')
    
    return '\n'.join(bubble_lines)


def pretty_print_reaction(message: Dict[str, Any]) -> str:
    """Format message reaction for terminal display.
    
    Args:
        message: Message dictionary from iMessageMonitor
        
    Returns:
        Formatted reaction string
    """
    # Extract reaction info
    associated_type = message.get('associated_message_type', 0)
    handle_id = message.get('handle_id_str', 'Unknown')
    is_from_me = message.get('is_from_me', False)
    timestamp = message.get('date', 0)
    
    # Format timestamp
    time_str = format_apple_timestamp_for_display(timestamp)
    
    # Get reaction emoji from constants
    reaction_emoji = REACTION_EMOJIS.get(associated_type, "🔄")
    is_removal = associated_type >= 3000
    action = "removed" if is_removal else "added"
    sender = "You" if is_from_me else handle_id
    
    # Format reaction display
    reaction_line = f"   {reaction_emoji} {sender} {action} a reaction"
    time_line = f"      {time_str}"
    
    return f"{reaction_line}\n{time_line}"


def pretty_print_sticker(message: Dict[str, Any], show_ascii_art: bool = False) -> str:
    """Format sticker message for terminal display.
    
    Args:
        message: Message dictionary from iMessageMonitor
        show_ascii_art: Whether to show ASCII art for sticker images (default: False)
        
    Returns:
        Formatted sticker string
    """
    # Extract sticker info
    handle_id = message.get('handle_id_str', 'Unknown')
    is_from_me = message.get('is_from_me', False)
    timestamp = message.get('date', 0)
    balloon_bundle_id = message.get('balloon_bundle_id', '')
    
    # Check for sticker attachments
    attachments = message.get('parsed_attachments', [])
    sticker_attachments = [a for a in attachments if a.get('is_sticker', False)]
    
    # Format timestamp
    time_str = format_apple_timestamp_for_display(timestamp)
    
    sender = "You" if is_from_me else handle_id
    
    # Determine sticker type
    sticker_type = "User"
    if balloon_bundle_id:
        if "animoji" in balloon_bundle_id.lower():
            sticker_type = "Animoji"
        elif "memoji" in balloon_bundle_id.lower():
            sticker_type = "Memoji"
        elif "sticker" in balloon_bundle_id.lower():
            sticker_type = "Sticker"
    
    # Build sticker display
    lines = []
    sticker_content = []
    
    # If we have a sticker image attachment, show ASCII art
    if sticker_attachments:
        attachment = sticker_attachments[0]
        ascii_art = get_ascii_art_for_attachment(attachment, enable_ascii=show_ascii_art)
        
        if not ascii_art.startswith('['):  # If ASCII art generation was successful
            sticker_content.append("┌─────────────────────┐")
            sticker_content.append("│   Sticker Image:    │")
            sticker_content.append("└─────────────────────┘")
            
            # Add ASCII art
            art_lines = ascii_art.split('\n')
            for art_line in art_lines:
                sticker_content.append(art_line)
            
            # Add attachment info
            filename = attachment.get('filename', 'Unknown')
            size = attachment.get('size', 0)
            if size:
                size_str = get_file_size_human(size)
                sticker_content.append(f"📎 {filename} ({size_str})")
        else:
            # Fallback to box display if ASCII art failed
            sticker_content.append("┌─────────────────────┐")
            sticker_content.append("│                     │")
            sticker_content.append("│        🎭           │")  # Sticker icon
            sticker_content.append("│                     │")
            sticker_content.append(f"│  {sticker_type} Sticker       │")
            sticker_content.append("│                     │")
            sticker_content.append("└─────────────────────┘")
            
            # Add attachment info
            filename = attachment.get('filename', 'Unknown')
            size = attachment.get('size', 0)
            if size:
                size_str = get_file_size_human(size)
                sticker_content.append(f"   📎 {filename} ({size_str})")
            sticker_content.append(f"   {ascii_art}")  # Show error message
    else:
        # No attachment, show generic sticker box
        sticker_content.append("┌─────────────────────┐")
        sticker_content.append("│                     │")
        sticker_content.append("│        🎭           │")  # Sticker icon
        sticker_content.append("│                     │")
        sticker_content.append(f"│  {sticker_type} Sticker       │")
        sticker_content.append("│                     │")
        sticker_content.append("└─────────────────────┘")
    
    # Apply alignment based on sender
    if is_from_me:
        # Right-align for stickers from me
        terminal_width = get_terminal_width()
        max_content_width = max(len(line) for line in sticker_content)
        
        # Add sender and time (right-aligned)
        sender_info = f"{sender} • {time_str}"
        info_padding = terminal_width - len(sender_info)
        lines.append(' ' * info_padding + sender_info)
        
        # Add sticker content (right-aligned)
        for line in sticker_content:
            line_padding = terminal_width - len(line)
            lines.append(' ' * line_padding + line)
    else:
        # Left-align for stickers from others
        # Add sender and time (left-aligned)
        lines.append(f"{sender} • {time_str}")
        
        # Add sticker content (left-aligned)
        lines.extend(sticker_content)
    
    return '\n'.join(lines)


# Message Display Functions
def format_message_for_log(
    contact: str, 
    content: str, 
    timestamp: datetime, 
    is_incoming: bool,
    message_type: str = "text",
    is_group: bool = False,
    group_name: str = None,
    has_attachments: bool = False,
    is_read: bool = False,
    is_delivered: bool = False,
    apple_rowid: int = None,
    thread_id: str = None
) -> str:
    """Format message for terminal logging with detailed information."""
    # Direction indicator
    direction = "📥" if is_incoming else "📤"
    
    # Time formatting
    time_str = format_message_time(timestamp)
    
    # Contact/group formatting
    if is_group and group_name:
        contact_display = f"{group_name} ({contact})"
        group_indicator = "[GROUP] "
    else:
        contact_display = contact
        group_indicator = ""
    
    # Message type indicator
    type_indicators = {
        "text": "",
        "reaction": "[REACTION] ",
        "media": "[MEDIA] ",
        "voice": "[VOICE] ",
        "location": "[LOCATION] ",
        "sticker": "[STICKER] ",
        "game": "[GAME] ",
        "payment": "[PAYMENT] ",
        "system": "[SYSTEM] "
    }
    type_indicator = type_indicators.get(message_type, "")
    
    # Status indicators
    status_parts = []
    if has_attachments:
        status_parts.append("ATTACH")
    if is_delivered and not is_incoming:
        status_parts.append("DELIVERED")
    if is_read and not is_incoming:
        status_parts.append("READ")
    
    status_str = " [" + ", ".join(status_parts) + "]" if status_parts else ""
    
    # Content formatting
    truncated_content = truncate_for_log(content or "[No content]", 120)
    
    # Additional info
    info_parts = []
    if apple_rowid:
        info_parts.append(f"ID:{apple_rowid}")
    if thread_id and thread_id != "unknown_thread":
        thread_short = thread_id[-8:] if len(thread_id) > 8 else thread_id
        info_parts.append(f"T:{thread_short}")
    
    info_str = f" ({', '.join(info_parts)})" if info_parts else ""
    
    return f"{time_str} {direction} {group_indicator}{type_indicator}{contact_display}: {truncated_content}{status_str}{info_str}"


def format_attachment_for_log(
    contact: str, 
    filename: str, 
    file_size: int, 
    is_incoming: bool,
    mime_type: str = None,
    is_sticker: bool = False,
    apple_rowid: int = None
) -> str:
    """Format attachment transfer for terminal logging."""
    direction = "📥" if is_incoming else "📤"
    size_str = get_file_size_human(file_size)
    
    # File type indicator
    type_indicator = "[STICKER] " if is_sticker else "[ATTACHMENT] "
    
    # MIME type info
    mime_info = f" ({mime_type})" if mime_type else ""
    
    # Additional info
    info_parts = []
    if apple_rowid:
        info_parts.append(f"ID:{apple_rowid}")
    
    info_str = f" ({', '.join(info_parts)})" if info_parts else ""
    
    return f"📎 {direction} {type_indicator}{contact}: {filename} [{size_str}]{mime_info}{info_str}"


def format_system_event(event: str, timestamp: Optional[datetime] = None) -> str:
    """Format system events for terminal logging."""
    if timestamp:
        time_str = format_message_time(timestamp)
        return f"{time_str} ⚙️  {event}"
    else:
        now = datetime.now()
        time_str = format_message_time(now)
        return f"{time_str} ⚙️  {event}"


def format_error_message(error: str, timestamp: Optional[datetime] = None) -> str:
    """Format error messages for terminal logging."""
    if timestamp:
        time_str = format_message_time(timestamp)
        return f"{time_str} ❌ {error}"
    else:
        now = datetime.now()
        time_str = format_message_time(now)
        return f"{time_str} ❌ {error}"


# Pretty Print Functions
def truncate_for_log(text: str, max_len: int = 100) -> str:
    """Truncate long messages for terminal display."""
    if len(text) <= max_len:
        return text
    return text[:max_len-3] + "..."


def get_file_size_human(size_bytes: int) -> str:
    """Format file sizes (1.2MB, 34KB)."""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f}MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f}GB"


def format_message_time(dt: datetime) -> str:
    """Human-readable timestamp for logging."""
    return dt.strftime("%H:%M:%S")


def format_duration(seconds: float) -> str:
    """Format duration for display (1m 30s, 2h 15m)."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        return f"{minutes}m {remaining_seconds}s"
    else:
        hours = int(seconds // 3600)
        remaining_minutes = int((seconds % 3600) // 60)
        return f"{hours}h {remaining_minutes}m"


# Configuration Display
def display_config_section(title: str, config_dict: Dict[str, Any]) -> str:
    """Display a configuration section with formatting."""
    output = f"[{title}]\n"
    for key, value in config_dict.items():
        output += f"  {key} = {value}\n"
    return output


def format_config_for_display(config) -> str:
    """Format entire configuration for readable display."""
    output = "=== iMessage Monitor Configuration ===\n\n"
    
    output += display_config_section("apple", {
        "chat_db_path": config.apple.chat_db_path,
        "attachments_path": config.apple.attachments_path,
        "permissions_check": config.apple.permissions_check
    })
    output += "\n"
    
    output += display_config_section("monitoring", {
        "poll_interval_seconds": config.monitoring.poll_interval_seconds,
        "max_batch_size": config.monitoring.max_batch_size,
        "enable_real_time": config.monitoring.enable_real_time
    })
    output += "\n"
    
    output += display_config_section("contacts", {
        "outbound_behavior": config.contacts.outbound_behavior,
        "outbound_ids": config.contacts.outbound_ids,
        "inbound_behavior": config.contacts.inbound_behavior,
        "inbound_ids": config.contacts.inbound_ids
    })
    output += "\n"
    
    output += display_config_section("date_range", {
        "start_date": config.date_range.start_date,
        "end_date": config.date_range.end_date
    })
    output += "\n"
    
    output += display_config_section("outbound", {
        "method": config.outbound.method,
        "rate_limit_per_minute": config.outbound.rate_limit_per_minute,
    })
    
    return output


def format_validation_report(validation_results: Dict[str, bool]) -> str:
    """Format validation results for display."""
    output = "\n=== Configuration Validation Report ===\n\n"
    
    for check, passed in validation_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        output += f"{status} - {check}\n"
    
    overall_status = all(validation_results.values())
    output += f"\nOverall Status: {'✅ Valid' if overall_status else '❌ Invalid'}\n"
    
    return output


def display_database_config(db_config) -> str:
    """Format database configuration section."""
    return display_config_section("database", {
        "url": db_config.url,
        "pool_size": db_config.pool_size,
        "max_overflow": db_config.max_overflow,
        "pool_timeout": db_config.pool_timeout
    })


def display_monitoring_config(monitoring_config) -> str:
    """Format monitoring configuration section."""
    return display_config_section("monitoring", {
        "poll_interval_seconds": monitoring_config.poll_interval_seconds,
        "max_batch_size": monitoring_config.max_batch_size,
        "enable_real_time": monitoring_config.enable_real_time
    })


def display_apple_config(apple_config) -> str:
    """Format Apple configuration section."""
    return display_config_section("apple", {
        "chat_db_path": apple_config.chat_db_path,
        "attachments_path": apple_config.attachments_path,
        "permissions_check": apple_config.permissions_check
    })


def display_outbound_config(outbound_config) -> str:
    """Format outbound configuration section."""
    return display_config_section("outbound", {
        "method": outbound_config.method,
        "rate_limit_per_minute": outbound_config.rate_limit_per_minute,
    })

