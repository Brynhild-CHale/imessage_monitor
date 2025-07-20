# iMessage Automation on Mac: Complete Python Guide

**Apple has significantly restricted iMessage automation capabilities in recent macOS versions, removing many previously available features**. This comprehensive guide covers all viable approaches for automating iMessage on Mac using Python, including critical limitations and workarounds.

## AppleScript limitations and current capabilities

**Critical Limitation**: AppleScript does **NOT** support message reactions (thumbs up, heart, laugh, etc.) or tapbacks. These are user-interface features that cannot be automated programmatically. Reading individual message content and accessing message history is also severely limited in macOS 12+.

### Basic iMessage sending operations

**Send message to phone number:**
```

## Receiving and accessing attachments

**Critical limitation**: AppleScript cannot directly access received attachments. However, you can access them through the SQLite database and file system.

### Database structure for attachments

iMessage stores attachment metadata in the database and actual files in `~/Library/Messages/Attachments/`:

**Key tables:**
- `attachment`: Contains attachment metadata and file paths
- `message_attachment_join`: Links messages to their attachments  
- `message`: Has `cache_has_attachments` flag indicating attachment presence

**Important columns:**
- `attachment.filename`: Full path to the attachment file on disk
- `attachment.mime_type`: File type (image/jpeg, video/mp4, etc.)
- `attachment.total_bytes`: File size in bytes
- `message.cache_has_attachments`: 1 if message has attachments, 0 if not

### Python methods for accessing received attachments

**Method 1: Direct database query for attachments:**
```python
import sqlite3
import shutil
import os
from pathlib import Path

def get_attachments_for_contact(contact_id, limit=10):
    """Get recent attachments from a specific contact"""
    db_path = Path.home() / "Library" / "Messages" / "chat.db"
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        query = """
        SELECT 
            m.ROWID as message_id,
            datetime(m.date/1000000000 + strftime('%s', '2001-01-01'), 'unixepoch', 'localtime') as message_date,
            h.id as sender,
            a.filename as attachment_path,
            a.mime_type,
            a.total_bytes,
            m.text as message_text
        FROM message m
        JOIN handle h ON m.handle_id = h.ROWID
        JOIN message_attachment_join maj ON m.ROWID = maj.message_id
        JOIN attachment a ON maj.attachment_id = a.ROWID
        WHERE h.id = ?
        ORDER BY m.date DESC
        LIMIT ?
        """
        
        cursor.execute(query, (contact_id, limit))
        attachments = cursor.fetchall()
        conn.close()
        
        return [
            {
                "message_id": row[0],
                "date": row[1],
                "sender": row[2],
                "attachment_path": row[3],
                "mime_type": row[4],
                "file_size": row[5],
                "message_text": row[6]
            }
            for row in attachments
        ]
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []

# Get attachments from a specific phone number
attachments = get_attachments_for_contact("+1234567890", 5)
for att in attachments:
    print(f"Attachment: {att['attachment_path']}")
    print(f"Type: {att['mime_type']}, Size: {att['file_size']} bytes")
```

**Method 2: Copy attachments to a working directory:**
```python
import sqlite3
import shutil
import os
from pathlib import Path

def copy_recent_attachments(destination_dir, days_back=7):
    """Copy recent attachments to a destination directory"""
    db_path = Path.home() / "Library" / "Messages" / "chat.db"
    dest_path = Path(destination_dir)
    dest_path.mkdir(exist_ok=True)
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Get attachments from last N days
        query = """
        SELECT DISTINCT
            a.filename,
            a.mime_type,
            datetime(m.date/1000000000 + strftime('%s', '2001-01-01'), 'unixepoch', 'localtime') as date,
            h.id as sender
        FROM attachment a
        JOIN message_attachment_join maj ON a.ROWID = maj.attachment_id
        JOIN message m ON maj.message_id = m.ROWID
        JOIN handle h ON m.handle_id = h.ROWID
        WHERE m.date > (strftime('%s', 'now') - strftime('%s', '2001-01-01') - ? * 86400) * 1000000000
        ORDER BY m.date DESC
        """
        
        cursor.execute(query, (days_back,))
        attachments = cursor.fetchall()
        conn.close()
        
        copied_files = []
        for filename, mime_type, date, sender in attachments:
            if filename and os.path.exists(filename):
                # Create safe filename
                file_path = Path(filename)
                safe_sender = "".join(c for c in sender if c.isalnum() or c in (' ', '-', '_')).rstrip()
                new_name = f"{date}_{safe_sender}_{file_path.name}"
                
                try:
                    dest_file = dest_path / new_name
                    shutil.copy2(filename, dest_file)
                    copied_files.append({
                        "original": filename,
                        "copied_to": str(dest_file),
                        "sender": sender,
                        "date": date,
                        "mime_type": mime_type
                    })
                except Exception as e:
                    print(f"Failed to copy {filename}: {e}")
        
        return copied_files
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []

# Copy recent attachments to Desktop
copied = copy_recent_attachments("~/Desktop/iMessage_Attachments", days_back=7)
for file_info in copied:
    print(f"Copied: {file_info['original']} -> {file_info['copied_to']}")
```

**Method 3: Monitor for new attachments:**
```python
import sqlite3
import time
import os
from pathlib import Path

class AttachmentMonitor:
    """Monitor for new iMessage attachments"""
    
    def __init__(self, callback_function=None):
        self.db_path = Path.home() / "Library" / "Messages" / "chat.db"
        self.last_check = time.time()
        self.callback = callback_function or self.default_callback
        
    def default_callback(self, attachment_info):
        """Default callback for new attachments"""
        print(f"New attachment: {attachment_info['filename']}")
        print(f"From: {attachment_info['sender']}")
        print(f"Type: {attachment_info['mime_type']}")
        
    def check_for_new_attachments(self):
        """Check for attachments newer than last check"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Convert last_check to Apple timestamp format
            apple_timestamp = (self.last_check - 978307200) * 1000000000
            
            query = """
            SELECT 
                a.filename,
                a.mime_type,
                a.total_bytes,
                h.id as sender,
                m.text,
                m.date
            FROM attachment a
            JOIN message_attachment_join maj ON a.ROWID = maj.attachment_id
            JOIN message m ON maj.message_id = m.ROWID
            JOIN handle h ON m.handle_id = h.ROWID
            WHERE m.date > ?
            ORDER BY m.date ASC
            """
            
            cursor.execute(query, (apple_timestamp,))
            new_attachments = cursor.fetchall()
            conn.close()
            
            for att in new_attachments:
                if att[0] and os.path.exists(att[0]):  # Check file exists
                    attachment_info = {
                        "filename": att[0],
                        "mime_type": att[1],
                        "file_size": att[2],
                        "sender": att[3],
                        "message_text": att[4],
                        "timestamp": att[5]
                    }
                    self.callback(attachment_info)
            
            self.last_check = time.time()
            return len(new_attachments)
            
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return 0

# Usage example
def process_new_attachment(att_info):
    """Custom processing for new attachments"""
    print(f"Processing: {att_info['filename']}")
    
    # Copy to processing directory
    if att_info['mime_type'].startswith('image/'):
        dest_dir = Path("~/Desktop/New_Images").expanduser()
        dest_dir.mkdir(exist_ok=True)
        
        try:
            shutil.copy2(att_info['filename'], dest_dir)
            print(f"Copied image to {dest_dir}")
        except Exception as e:
            print(f"Copy failed: {e}")

monitor = AttachmentMonitor(process_new_attachment)

# Check every 30 seconds for new attachments
while True:
    new_count = monitor.check_for_new_attachments()
    if new_count > 0:
        print(f"Found {new_count} new attachments")
    time.sleep(30)
```

**Method 4: Using imessage-reader library:**
```python
# First install: pip install imessage-reader
from imessage_reader import fetch_data

# Initialize with database path
DB_PATH = "~/Library/Messages/chat.db"
fd = fetch_data.FetchData(DB_PATH)

# Get all messages and attachments
messages = fd.get_messages()

# Filter for messages with attachments
attachment_messages = [msg for msg in messages if hasattr(msg, 'attachments') and msg.attachments]

for msg in attachment_messages:
    print(f"From: {msg.phone_number}")
    print(f"Date: {msg.date}")
    if hasattr(msg, 'attachments'):
        for attachment in msg.attachments:
            print(f"  Attachment: {attachment}")
```

### Working with specific attachment types

**Image processing example:**
```python
from PIL import Image
import sqlite3
from pathlib import Path

def process_recent_images(days_back=1):
    """Process recent image attachments"""
    db_path = Path.home() / "Library" / "Messages" / "chat.db"
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        query = """
        SELECT DISTINCT a.filename, h.id as sender
        FROM attachment a
        JOIN message_attachment_join maj ON a.ROWID = maj.attachment_id
        JOIN message m ON maj.message_id = m.ROWID
        JOIN handle h ON m.handle_id = h.ROWID
        WHERE a.mime_type LIKE 'image/%'
        AND m.date > (strftime('%s', 'now') - strftime('%s', '2001-01-01') - ? * 86400) * 1000000000
        """
        
        cursor.execute(query, (days_back,))
        image_attachments = cursor.fetchall()
        conn.close()
        
        for filename, sender in image_attachments:
            if filename and os.path.exists(filename):
                try:
                    # Open and process image
                    with Image.open(filename) as img:
                        print(f"Image from {sender}: {img.size} pixels, {img.format}")
                        
                        # Example: Create thumbnail
                        img.thumbnail((200, 200))
                        thumb_path = f"~/Desktop/thumb_{Path(filename).name}"
                        img.save(Path(thumb_path).expanduser())
                        
                except Exception as e:
                    print(f"Failed to process image {filename}: {e}")
                    
    except sqlite3.Error as e:
        print(f"Database error: {e}")

# Process recent images
process_recent_images(1)  # Last 1 dayapplescript
tell application "Messages"
    set targetBuddy to "+1234567890"
    set targetService to id of 1st service whose service type = iMessage
    set textMessage to "Hello, this is a test message"
    set theBuddy to buddy targetBuddy of service id targetService
    send textMessage to theBuddy
end tell
```

**Send message with service detection and fallback:**
```applescript
tell application "Messages"
    set phoneNumber to "+1234567890"
    set messageText to "Your message here"
    
    -- Try iMessage first, fall back to SMS
    try
        set iMessageService to id of 1st service whose service type = iMessage
        set iMessageBuddy to buddy phoneNumber of service id iMessageService
        send messageText to iMessageBuddy
    on error
        try
            set smsService to id of 1st service whose service type = SMS
            set smsBuddy to buddy phoneNumber of service id smsService
            send messageText to smsBuddy
        on error
            display dialog "Failed to send message"
        end try
    end try
end tell
```

**Send message with attachment:**
```applescript
tell application "Messages"
    set targetBuddy to "+1234567890"
    set targetService to id of 1st service whose service type = iMessage
    set theFile to POSIX file "/Users/username/Pictures/image.jpg"
    set theBuddy to buddy targetBuddy of service id targetService
    send theFile to theBuddy
end tell
```

### What AppleScript cannot do

- **Message reactions/tapbacks**: Not supported programmatically
- **Reading specific message content**: Severely limited in recent macOS versions
- **Advanced chat manipulation**: Most chat properties are read-only or inaccessible
- **Message received handlers**: Largely removed in macOS 12+
- **Individual message targeting**: Cannot access specific message IDs
- **Receiving/accessing attachments**: Cannot read received attachments through AppleScript

## Python integration approaches

### Method 1: subprocess with osascript (most reliable)

**Basic implementation with comprehensive error handling:**
```python
import subprocess
import logging

class iMessageAutomator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def send_message(self, recipient, message):
        """Send iMessage with comprehensive error handling"""
        try:
            # Escape quotes in message
            safe_message = message.replace('"', '\\"')
            safe_recipient = recipient.replace('"', '\\"')
            
            applescript = f'''
            tell application "Messages"
                set targetService to 1st service whose service type = iMessage
                set targetBuddy to buddy "{safe_recipient}" of targetService
                send "{safe_message}" to targetBuddy
            end tell
            '''
            
            result = subprocess.run(
                ['/usr/bin/osascript', '-'],
                input=applescript,
                text=True,
                capture_output=True,
                timeout=30
            )
            
            if result.returncode != 0:
                self.logger.error(f"AppleScript error: {result.stderr}")
                raise Exception(f"Failed to send message: {result.stderr}")
                
            return True
            
        except subprocess.TimeoutExpired:
            self.logger.error("AppleScript execution timed out")
            raise Exception("Message sending timed out")
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            raise

# Usage
automator = iMessageAutomator()
automator.send_message("+1234567890", "Hello from Python!")
```

**Advanced Unicode and special character handling:**
```python
import subprocess
import unicodedata

def safe_applescript_string(text):
    """Safely encode string for AppleScript"""
    # Normalize Unicode
    text = unicodedata.normalize('NFC', text)
    
    # Handle special characters
    text = text.replace('\\', '\\\\')
    text = text.replace('"', '\\"')
    text = text.replace('\n', '\\n')
    text = text.replace('\r', '\\r')
    text = text.replace('\t', '\\t')
    
    return text

def send_unicode_message(recipient, message):
    """Send message with proper Unicode handling"""
    safe_message = safe_applescript_string(message)
    safe_recipient = safe_applescript_string(recipient)
    
    applescript = f'''
    tell application "Messages"
        set targetService to 1st service whose service type = iMessage
        set targetBuddy to buddy "{safe_recipient}" of targetService
        send "{safe_message}" to targetBuddy
    end tell
    '''
    
    result = subprocess.run(
        ['/usr/bin/osascript', '-'],
        input=applescript.encode('utf-8'),
        capture_output=True,
        timeout=30
    )
    
    if result.returncode != 0:
        error_msg = result.stderr.decode('utf-8', errors='replace')
        raise Exception(f"AppleScript error: {error_msg}")
    
    return result.stdout.decode('utf-8', errors='replace')

# Test with emoji and special characters
send_unicode_message("+1234567890", "Hello 👋 with émojis and spëcial chars!")
```

### Method 2: PyObjC integration (built-in macOS)

```python
from Foundation import NSAppleScript

def run_applescript_pyobjc(script_text):
    """Execute AppleScript using PyObjC"""
    myScript = NSAppleScript.initWithSource_(NSAppleScript.alloc(), script_text)
    results, err = myScript.executeAndReturnError_(None)
    if err:
        raise Exception(f"AppleScript Error: {err}")
    return results

# Example usage
script = '''
tell application "Messages"
    set targetService to 1st service whose service type = iMessage
    set targetBuddy to buddy "+1234567890" of targetService
    send "Hello from Python!" to targetBuddy
end tell
'''
result = run_applescript_pyobjc(script)
```

### Method 3: py-applescript library (modern wrapper)

```python
import applescript

# Create persistent AppleScript object
scpt = applescript.AppleScript('''
on run {phoneNumber, message}
    tell application "Messages"
        set targetService to 1st service whose service type = iMessage
        set targetBuddy to buddy phoneNumber of targetService
        send message to targetBuddy
    end tell
end run
''')

# Send message
scpt.run("+1234567890", "Hello from py-applescript!")
```

## Alternative Python solutions

### Direct Python libraries

**py-iMessage (basic sending):**
```python
from py_imessage import imessage
import time

phone = "1234567890"
if not imessage.check_compatibility(phone):
    print("Not an iPhone")
    
guid = imessage.send(phone, "Hello World!")
time.sleep(5)  # Let recipient read the message
resp = imessage.status(guid)
print(f'Message was read at {resp.get("date_read")}')
```

**macpymessenger (template-based):**
```python
from macpymessenger import IMessageClient, Configuration

config = Configuration()
client = IMessageClient(config)

# Create a template
template_id = "welcome_template"
template_content = "Hello, {{ name }}! Welcome to our service."
client.create_template(template_id, template_content)

# Send message using template
phone_number = "1234567890"
context = {"name": "John"}
client.send_template(phone_number, template_id, context)
```

### Database access methods

**Direct SQLite access to read messages:**
```python
import sqlite3
import pandas as pd

def get_recent_messages(limit=10):
    """Get recent messages from database"""
    db_path = "~/Library/Messages/chat.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        query = """
        SELECT 
            datetime(message.date/1000000000 + strftime('%s', '2001-01-01'), 'unixepoch', 'localtime') as message_date,
            handle.id as sender,
            message.text as message_text
        FROM message
        LEFT JOIN handle ON message.handle_id = handle.ROWID
        WHERE message.text IS NOT NULL
        ORDER BY message.date DESC
        LIMIT ?
        """
        
        cursor.execute(query, (limit,))
        messages = cursor.fetchall()
        conn.close()
        
        return [
            {
                "date": msg[0],
                "sender": msg[1],
                "text": msg[2]
            }
            for msg in messages
        ]
        
    except sqlite3.Error as e:
        raise Exception(f"Database error: {e}")

# Usage (requires Full Disk Access)
messages = get_recent_messages(5)
for msg in messages:
    print(f"From {msg['sender']}: {msg['text']}")
```

**imessage-tools (handles newer macOS versions):**
```python
from imessage_tools import read_messages, send_message

chat_db = "/Users/<YOUR_HOME>/Library/Messages/chat.db"
self_number = "Me"

# Read messages (including hidden ones in newer macOS)
messages = read_messages(chat_db, n=10, self_number=self_number, human_readable_date=True)

# Send to group or individual
if messages[-1]["group_chat_name"]:
    send_message("Hello iMessage Group!", messages[-1]["group_chat_name"], True)
else:
    send_message("Hello iMessage Buddy!", messages[-1]["phone_number"], False)
```

### GUI automation approaches

**PyAutoGUI method:**
```python
import pyautogui
import time

def send_message_gui(message):
    """Send message using GUI automation"""
    try:
        # Open Messages app
        pyautogui.hotkey('cmd', 'space')  # Open Spotlight
        pyautogui.typewrite('Messages')
        pyautogui.press('enter')
        time.sleep(2)
        
        # Type and send message
        pyautogui.typewrite(message)
        pyautogui.press('enter')
        return True
        
    except Exception as e:
        print(f"GUI send error: {e}")
        return False

send_message_gui("Hello from GUI automation!")
```

## Complete working example

**Production-ready iMessage automation class:**
```python
import subprocess
import sqlite3
import time
import logging
from pathlib import Path

class iMessageManager:
    """Complete iMessage automation with multiple methods and attachment handling"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db_path = Path.home() / "Library" / "Messages" / "chat.db"
        self.attachments_path = Path.home() / "Library" / "Messages" / "Attachments"
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('imessage_automation.log'),
                logging.StreamHandler()
            ]
        )
    
    def send_message(self, recipient, message):
        """Send iMessage with AppleScript"""
        try:
            safe_message = self._escape_applescript_string(message)
            safe_recipient = self._escape_applescript_string(recipient)
            
            applescript = f'''
            tell application "Messages"
                set targetService to 1st service whose service type = iMessage
                set targetBuddy to buddy "{safe_recipient}" of targetService
                send "{safe_message}" to targetBuddy
            end tell
            '''
            
            result = subprocess.run(
                ['/usr/bin/osascript', '-'],
                input=applescript,
                text=True,
                capture_output=True,
                timeout=30
            )
            
            if result.returncode != 0:
                self.logger.error(f"Failed to send message: {result.stderr}")
                return False
            
            self.logger.info(f"Message sent to {recipient}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            return False
    
    def send_attachment(self, recipient, file_path):
        """Send file attachment via iMessage"""
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"File not found: {file_path}")
                return False
                
            safe_recipient = self._escape_applescript_string(recipient)
            safe_path = self._escape_applescript_string(file_path)
            
            applescript = f'''
            tell application "Messages"
                set targetService to 1st service whose service type = iMessage
                set targetBuddy to buddy "{safe_recipient}" of targetService
                set theFile to POSIX file "{safe_path}"
                send theFile to targetBuddy
            end tell
            '''
            
            result = subprocess.run(
                ['/usr/bin/osascript', '-'],
                input=applescript,
                text=True,
                capture_output=True,
                timeout=60  # Longer timeout for file uploads
            )
            
            if result.returncode != 0:
                self.logger.error(f"Failed to send attachment: {result.stderr}")
                return False
            
            self.logger.info(f"Attachment sent to {recipient}: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending attachment: {e}")
            return False
    
    def get_recent_messages(self, limit=10):
        """Get recent messages from database"""
        if not self.db_path.exists():
            self.logger.error("Messages database not found")
            return []
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            query = """
            SELECT 
                datetime(message.date/1000000000 + strftime('%s', '2001-01-01'), 'unixepoch', 'localtime') as message_date,
                handle.id as sender,
                message.text as message_text,
                message.cache_has_attachments,
                message.ROWID as message_id
            FROM message
            LEFT JOIN handle ON message.handle_id = handle.ROWID
            WHERE message.text IS NOT NULL
            ORDER BY message.date DESC
            LIMIT ?
            """
            
            cursor.execute(query, (limit,))
            messages = cursor.fetchall()
            conn.close()
            
            return [
                {
                    "date": msg[0],
                    "sender": msg[1],
                    "text": msg[2],
                    "has_attachments": bool(msg[3]),
                    "message_id": msg[4]
                }
                for msg in messages
            ]
            
        except sqlite3.Error as e:
            self.logger.error(f"Database error: {e}")
            return []
    
    def get_attachments_for_message(self, message_id):
        """Get all attachments for a specific message"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            query = """
            SELECT 
                a.filename,
                a.mime_type,
                a.total_bytes
            FROM attachment a
            JOIN message_attachment_join maj ON a.ROWID = maj.attachment_id
            WHERE maj.message_id = ?
            """
            
            cursor.execute(query, (message_id,))
            attachments = cursor.fetchall()
            conn.close()
            
            return [
                {
                    "filename": att[0],
                    "mime_type": att[1],
                    "file_size": att[2]
                }
                for att in attachments if att[0] and os.path.exists(att[0])
            ]
            
        except sqlite3.Error as e:
            self.logger.error(f"Database error: {e}")
            return []
    
    def get_recent_attachments(self, contact=None, limit=10):
        """Get recent attachments, optionally filtered by contact"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            if contact:
                query = """
                SELECT 
                    a.filename,
                    a.mime_type,
                    a.total_bytes,
                    datetime(m.date/1000000000 + strftime('%s', '2001-01-01'), 'unixepoch', 'localtime') as date,
                    h.id as sender
                FROM attachment a
                JOIN message_attachment_join maj ON a.ROWID = maj.attachment_id
                JOIN message m ON maj.message_id = m.ROWID
                JOIN handle h ON m.handle_id = h.ROWID
                WHERE h.id = ?
                ORDER BY m.date DESC
                LIMIT ?
                """
                cursor.execute(query, (contact, limit))
            else:
                query = """
                SELECT 
                    a.filename,
                    a.mime_type,
                    a.total_bytes,
                    datetime(m.date/1000000000 + strftime('%s', '2001-01-01'), 'unixepoch', 'localtime') as date,
                    h.id as sender
                FROM attachment a
                JOIN message_attachment_join maj ON a.ROWID = maj.attachment_id
                JOIN message m ON maj.message_id = m.ROWID
                JOIN handle h ON m.handle_id = h.ROWID
                ORDER BY m.date DESC
                LIMIT ?
                """
                cursor.execute(query, (limit,))
            
            attachments = cursor.fetchall()
            conn.close()
            
            return [
                {
                    "filename": att[0],
                    "mime_type": att[1],
                    "file_size": att[2],
                    "date": att[3],
                    "sender": att[4]
                }
                for att in attachments if att[0] and os.path.exists(att[0])
            ]
            
        except sqlite3.Error as e:
            self.logger.error(f"Database error: {e}")
            return []
    
    def save_attachment(self, attachment_path, destination_dir):
        """Save an attachment to a destination directory"""
        try:
            dest_dir = Path(destination_dir)
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            src_path = Path(attachment_path)
            dest_path = dest_dir / src_path.name
            
            shutil.copy2(attachment_path, dest_path)
            self.logger.info(f"Attachment saved: {dest_path}")
            return str(dest_path)
            
        except Exception as e:
            self.logger.error(f"Failed to save attachment: {e}")
            return None
    
    
    def auto_save_attachments(self, destination_dir, contact_filter=None):
        """Automatically save new attachments to a directory"""
        try:
            attachments = self.get_recent_attachments(contact=contact_filter, limit=20)
            saved_count = 0
            
            for att in attachments:
                if self.save_attachment(att['filename'], destination_dir):
                    saved_count += 1
                    
            self.logger.info(f"Saved {saved_count} attachments to {destination_dir}")
            return saved_count
            
        except Exception as e:
            self.logger.error(f"Auto-save attachments error: {e}")
            return 0
    
    def _escape_applescript_string(self, text):
        """Escape string for AppleScript"""
        return text.replace('\\', '\\\\').replace('"', '\\"')

# Usage
manager = iMessageManager()

# Send text message
manager.send_message("+1234567890", "Hello from Python automation!")

# Send attachment
manager.send_attachment("+1234567890", "/Users/username/Desktop/photo.jpg")

# Get recent messages (requires Full Disk Access)
messages = manager.get_recent_messages(5)
for msg in messages:
    print(f"From {msg['sender']}: {msg['text']}")
    if msg['has_attachments']:
        attachments = manager.get_attachments_for_message(msg['message_id'])
        for att in attachments:
            print(f"  📎 {att['filename']} ({att['mime_type']})")

# Get recent attachments from specific contact
attachments = manager.get_recent_attachments(contact="+1234567890", limit=5)
for att in attachments:
    print(f"Attachment from {att['sender']}: {att['filename']}")

# Auto-save all recent attachments
saved_count = manager.auto_save_attachments("~/Desktop/Saved_Attachments")
print(f"Saved {saved_count} attachments")

```

## Security and permissions setup

### Required permissions

**Step-by-step setup for macOS 13+:**

1. **Automation Permissions**:
   - System Settings → Privacy & Security → Automation
   - Enable Terminal → Messages

2. **Full Disk Access** (for database reading):
   - System Settings → Privacy & Security → Full Disk Access
   - Add Terminal or your Python application

3. **Accessibility** (for GUI automation):
   - System Settings → Privacy & Security → Accessibility
   - Add Terminal or your Python application

### Permission verification

```python
import subprocess
import os

def check_permissions():
    """Check and verify necessary permissions"""
    print("Checking permissions...")
    
    # Check Full Disk Access
    test_db = os.path.expanduser("~/Library/Messages/chat.db")
    if not os.access(test_db, os.R_OK):
        print("❌ Full Disk Access required for Messages database")
        return False
    
    # Check Automation permissions
    try:
        result = subprocess.run(
            ['/usr/bin/osascript', '-e', 'tell application "Messages" to get name'],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print("❌ Automation permission required for Messages")
            return False
    except Exception as e:
        print(f"❌ Error checking automation permission: {e}")
        return False
    
    print("✅ All permissions granted")
    return True

# Run permission check
check_permissions()
```

## Known limitations and workarounds

### Current limitations in macOS 12+

- **No message reactions**: Cannot send thumbs up, heart, etc. programmatically
- **Limited message reading**: Cannot access individual message content reliably
- **No reply threading**: Cannot reply to specific messages in a thread
- **Conversation restrictions**: Cannot start new conversations with unknown contacts
- **Rate limiting**: Apple may limit automated message sending
- **Attachment access via AppleScript**: Cannot read received attachments through AppleScript
- **File permissions**: Attachment files may have restricted access requiring Full Disk Access

### Attachment-specific limitations

1. **AppleScript cannot read received attachments**: Only database access works
2. **File access permissions**: Attachments may be protected by system permissions
3. **Temporary files**: Some attachments may be cleaned up automatically by macOS
4. **Broken file paths**: Database may contain references to moved/deleted files
5. **Large file handling**: Very large attachments may timeout during sending

### Workarounds

1. **For reactions**: Use text responses instead ("👍", "❤️", etc.)
2. **For message reading**: Use database access with Full Disk Access
3. **For conversation management**: Manually initiate conversations first
4. **For bulk sending**: Implement delays between messages
5. **For attachment access**: Use SQLite database queries and file system access
6. **For broken attachment paths**: Check file existence before processing
7. **For large attachments**: Implement chunked copying and proper timeout handling

### Best practices

1. **Always test with existing conversations first**
2. **Use proper error handling for all operations**
3. **Implement rate limiting to avoid being blocked**
4. **Consider user privacy and notification preferences**
5. **Document all required permissions clearly**
6. **Check file existence before accessing attachments**
7. **Handle attachment file permissions gracefully**
8. **Create organized destination directories for saved attachments**
9. **Validate attachment file types and sizes before processing**
10. **Monitor disk space when auto-saving attachments**

This comprehensive guide provides multiple approaches for iMessage automation while acknowledging the significant limitations Apple has implemented. The subprocess method with osascript remains the most reliable approach for basic sending functionality, while database access provides the best option for reading messages when Full Disk Access is available.