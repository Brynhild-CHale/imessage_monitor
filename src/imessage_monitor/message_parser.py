"""Message parsing utilities for iMessage data extraction."""

import sqlite3
import plistlib
import re
from typing import Dict, List, Any, Optional
from pathlib import Path


def decode_attributed_body(attributed_body: bytes) -> Optional[str]:
    """Decode the attributedBody blob to extract text content."""
    if not attributed_body:
        return None
    
    try:
        # Decode the binary data to string with error handling
        attributed_body_str = attributed_body.decode('utf-8', errors='replace')
        
        # Check if this contains NSNumber, NSString, and NSDictionary markers
        if "NSNumber" in attributed_body_str:
            # Split on NSNumber and take the first part
            attributed_body_str = attributed_body_str.split("NSNumber")[0]
            
            if "NSString" in attributed_body_str:
                # Split on NSString and take the second part
                attributed_body_str = attributed_body_str.split("NSString")[1]
                
                if "NSDictionary" in attributed_body_str:
                    # Split on NSDictionary and take the first part
                    attributed_body_str = attributed_body_str.split("NSDictionary")[0]
                    # Remove common prefix/suffix characters
                    attributed_body_str = attributed_body_str[6:-12]
                    return attributed_body_str.strip()
        
        # Fallback: try to extract readable text using regex
        text_matches = re.findall(r'[\x20-\x7E]{2,}', attributed_body_str)
        if text_matches:
            # Return the longest readable string found
            return max(text_matches, key=len).strip()
        
        return None
    except Exception as e:
        print(f"Error decoding attributedBody: {e}")
        return None


def analyze_attributed_body_data(attributed_body: bytes) -> Optional[Dict[str, Any]]:
    """Comprehensively analyze attributedBody blob to extract all available content."""
    if not attributed_body:
        return None
    
    try:
        # Decode the binary data
        attributed_body_str = attributed_body.decode('utf-8', errors='replace')
        
        analysis = {
            'text_content': decode_attributed_body(attributed_body),
            'raw_content_indicators': [],
            'detected_attributes': {},
            'content_markers': [],
            'data_types_found': [],
            'extractable_strings': []
        }
        
        # Extract all readable strings (potential content)
        readable_strings = re.findall(r'[\x20-\x7E]{3,}', attributed_body_str)
        analysis['extractable_strings'] = list(set(readable_strings))  # Remove duplicates
        
        # Look for all NS* class indicators
        ns_classes = re.findall(r'NS[A-Za-z]+', attributed_body_str)
        analysis['data_types_found'] = list(set(ns_classes))
        
        # Look for all __k* attribute names (iMessage internal attributes)
        im_attributes = re.findall(r'__k[A-Za-z]+', attributed_body_str)
        analysis['content_markers'] = list(set(im_attributes))
        
        # Extract specific content indicators
        content_indicators = [
            'Calendar', 'Event', 'Time', 'Date', 'Hours', 'Minutes',
            'DDScannerResult', 'DataDetection', 'Link', 'URL', 'Phone',
            'Address', 'Email', 'Attachment', 'Sticker', 'Emoji',
            'Font', 'Color', 'Style', 'Bold', 'Italic', 'Underline'
        ]
        
        for indicator in content_indicators:
            if indicator in attributed_body_str:
                analysis['raw_content_indicators'].append(indicator)
        
        # Try to extract key-value pairs from attribute sections
        attribute_pattern = r'(__k[A-Za-z]+)[^A-Za-z]*([A-Za-z0-9:\-\s]+)'
        matches = re.findall(attribute_pattern, attributed_body_str)
        
        for attr_name, attr_value in matches:
            # Clean up the attribute value
            clean_value = re.sub(r'[^\w\s:\-]', '', attr_value).strip()
            if clean_value and len(clean_value) > 1:
                analysis['detected_attributes'][attr_name] = clean_value
        
        # Look for time patterns specifically
        time_patterns = [
            r'\d{1,2}:\d{2}',  # Time format like 10:45
            r'\d{1,2}\s*[Hh]ours?',  # Hours
            r'\d{1,2}\s*[Mm]inutes?',  # Minutes
            r'at\s+\d{1,2}:\d{2}',  # "at 10:45"
        ]
        
        time_matches = []
        for pattern in time_patterns:
            matches = re.findall(pattern, attributed_body_str)
            time_matches.extend(matches)
        
        if time_matches:
            analysis['detected_attributes']['time_references'] = list(set(time_matches))
        
        # Look for embedded plist data
        if 'bplist' in attributed_body_str:
            analysis['detected_attributes']['contains_binary_plist'] = True
        
        # Extract any quoted strings or specific delimited content
        quoted_strings = re.findall(r'"([^"]+)"', attributed_body_str)
        if quoted_strings:
            analysis['detected_attributes']['quoted_content'] = quoted_strings
        
        return analysis
        
    except Exception as e:
        print(f"Error analyzing attributedBody data: {e}")
        return None


def decode_binary_plist(data: bytes) -> Optional[Dict]:
    """Decode binary plist data."""
    if not data:
        return None
    
    try:
        return plistlib.loads(data)
    except Exception as e:
        print(f"Error decoding binary plist: {e}")
        return None


def analyze_payload_data(payload_data: bytes) -> Optional[Dict[str, Any]]:
    """Comprehensively analyze payload_data blob to extract all available content."""
    if not payload_data:
        return None
    
    try:
        analysis = {
            'plist_decoded': None,
            'raw_content_indicators': [],
            'detected_attributes': {},
            'content_markers': [],
            'data_types_found': [],
            'extractable_strings': [],
            'binary_indicators': {},
            'structured_data': {}
        }
        
        # First try to decode as plist
        try:
            plist_data = plistlib.loads(payload_data)
            analysis['plist_decoded'] = plist_data
            analysis['structured_data']['plist_success'] = True
        except:
            analysis['structured_data']['plist_success'] = False
        
        # Decode the binary data to string for analysis
        payload_str = payload_data.decode('utf-8', errors='replace')
        
        # Extract all readable strings (potential content)
        readable_strings = re.findall(r'[\x20-\x7E]{3,}', payload_str)
        analysis['extractable_strings'] = list(set(readable_strings))
        
        # Look for all NS* class indicators
        ns_classes = re.findall(r'NS[A-Za-z]+', payload_str)
        analysis['data_types_found'] = list(set(ns_classes))
        
        # Look for various content markers
        content_markers = [
            # App-specific
            'bundle', 'Bundle', 'app', 'App', 'plugin', 'Plugin',
            # Media
            'image', 'Image', 'video', 'Video', 'audio', 'Audio',
            # Documents
            'document', 'Document', 'file', 'File', 'pdf', 'PDF',
            # Rich content
            'rich', 'Rich', 'interactive', 'Interactive', 'card', 'Card',
            # Stickers and reactions
            'sticker', 'Sticker', 'reaction', 'Reaction', 'emoji', 'Emoji',
            # Location
            'location', 'Location', 'map', 'Map', 'coordinate', 'Coordinate',
            # Payment/Business
            'payment', 'Payment', 'business', 'Business', 'money', 'Money',
            # Game/App content
            'game', 'Game', 'score', 'Score', 'achievement', 'Achievement'
        ]
        
        for marker in content_markers:
            if marker in payload_str:
                analysis['content_markers'].append(marker)
        
        # Look for JSON-like structures
        json_patterns = [
            r'\{[^}]*\}',  # Simple JSON objects
            r'\[[^\]]*\]',  # JSON arrays
        ]
        
        json_matches = []
        for pattern in json_patterns:
            matches = re.findall(pattern, payload_str)
            json_matches.extend(matches)
        
        if json_matches:
            analysis['detected_attributes']['json_like_structures'] = json_matches
        
        # Look for URL patterns
        url_patterns = [
            r'https?://[^\s]+',
            r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            r'file://[^\s]+',
            r'data://[^\s]+'
        ]
        
        urls = []
        for pattern in url_patterns:
            matches = re.findall(pattern, payload_str)
            urls.extend(matches)
        
        if urls:
            analysis['detected_attributes']['urls'] = list(set(urls))
        
        # Look for identifiers (UUIDs, bundle IDs, etc.)
        identifier_patterns = [
            r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}',  # UUID
            r'com\.[a-zA-Z0-9.-]+',  # Bundle ID
            r'[a-zA-Z0-9]{20,}',  # Long alphanumeric strings
        ]
        
        identifiers = []
        for pattern in identifier_patterns:
            matches = re.findall(pattern, payload_str)
            identifiers.extend(matches)
        
        if identifiers:
            analysis['detected_attributes']['identifiers'] = list(set(identifiers))
        
        # Look for key-value patterns
        kv_patterns = [
            r'(\w+)[=:]\s*([^,\s]+)',  # key=value or key: value
            r'"(\w+)"[:\s]*"([^"]+)"',  # "key": "value"
        ]
        
        key_values = {}
        for pattern in kv_patterns:
            matches = re.findall(pattern, payload_str)
            for key, value in matches:
                if len(key) > 1 and len(value) > 1:
                    key_values[key] = value
        
        if key_values:
            analysis['detected_attributes']['key_value_pairs'] = key_values
        
        # Binary analysis
        analysis['binary_indicators'] = {
            'size_bytes': len(payload_data),
            'has_null_bytes': b'\x00' in payload_data,
            'entropy_high': len(set(payload_data)) > 200,  # High entropy suggests compression/encryption
            'starts_with_magic': payload_data[:4].hex() if len(payload_data) >= 4 else None
        }
        
        # Check for specific file signatures
        file_signatures = {
            b'PK\x03\x04': 'zip_archive',
            b'\x89PNG': 'png_image',
            b'\xff\xd8\xff': 'jpeg_image',
            b'GIF8': 'gif_image',
            b'%PDF': 'pdf_document',
            b'bplist00': 'binary_plist',
            b'\x00\x00\x00\x20ftypmp4': 'mp4_video',
        }
        
        for signature, file_type in file_signatures.items():
            if payload_data.startswith(signature):
                analysis['binary_indicators']['file_type'] = file_type
                break
        
        return analysis
        
    except Exception as e:
        print(f"Error analyzing payload data: {e}")
        return None


def get_recent_messages(db_path: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent messages with all associated data."""
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.cursor()
        
        # Complex query to get messages with all related data
        query = """
        SELECT 
            m.ROWID as message_id,
            m.guid as message_guid,
            m.text as message_text,
            m.attributedBody,
            m.payload_data,
            m.date,
            m.date_read,
            m.date_delivered,
            m.is_from_me,
            m.is_read,
            m.is_delivered,
            m.is_sent,
            m.service,
            m.account,
            m.handle_id,
            m.cache_has_attachments,
            m.message_summary_info,
            m.balloon_bundle_id,
            m.associated_message_guid,
            m.associated_message_type,
            m.expressive_send_style_id,
            m.reply_to_guid,
            m.thread_originator_guid,
            m.is_audio_message,
            m.group_title,
            m.group_action_type,
            
            -- Handle information
            h.id as handle_id_str,
            h.service as handle_service,
            h.country as handle_country,
            h.uncanonicalized_id,
            
            -- Chat information
            c.guid as chat_guid,
            c.chat_identifier,
            c.service_name as chat_service,
            c.display_name as chat_display_name,
            c.room_name,
            c.style as chat_style,
            c.properties as chat_properties,
            c.group_id,
            c.is_archived,
            
            -- Attachment information (if any)
            GROUP_CONCAT(a.guid) as attachment_guids,
            GROUP_CONCAT(a.filename) as attachment_filenames,
            GROUP_CONCAT(a.mime_type) as attachment_mime_types,
            GROUP_CONCAT(a.total_bytes) as attachment_sizes,
            GROUP_CONCAT(a.is_sticker) as attachment_is_stickers
            
        FROM message m
        LEFT JOIN handle h ON m.handle_id = h.ROWID
        LEFT JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
        LEFT JOIN chat c ON cmj.chat_id = c.ROWID
        LEFT JOIN message_attachment_join maj ON m.ROWID = maj.message_id
        LEFT JOIN attachment a ON maj.attachment_id = a.ROWID
        
        GROUP BY m.ROWID
        ORDER BY m.date DESC
        LIMIT ?
        """
        
        cursor.execute(query, (limit,))
        results = cursor.fetchall()
        
        # Get column names
        columns = [description[0] for description in cursor.description]
        
        messages = []
        for row in results:
            message_dict = dict(zip(columns, row))
            
            # Decode binary data fields
            if message_dict['attributedBody']:
                message_dict['decoded_attributed_body'] = decode_attributed_body(message_dict['attributedBody'])
                message_dict['decoded_attributedBody_data'] = analyze_attributed_body_data(message_dict['attributedBody'])
            
            if message_dict['payload_data']:
                message_dict['decoded_payload_data'] = decode_binary_plist(message_dict['payload_data'])
                message_dict['decoded_payload_data_analysis'] = analyze_payload_data(message_dict['payload_data'])
            
            if message_dict['message_summary_info']:
                message_dict['decoded_message_summary_info'] = decode_binary_plist(message_dict['message_summary_info'])
            
            if message_dict['chat_properties']:
                message_dict['decoded_chat_properties'] = decode_binary_plist(message_dict['chat_properties'])
            
            # Parse attachment information
            if message_dict['attachment_guids']:
                attachments = []
                guids = message_dict['attachment_guids'].split(',')
                filenames = (message_dict['attachment_filenames'] or '').split(',')
                mime_types = (message_dict['attachment_mime_types'] or '').split(',')
                sizes = (message_dict['attachment_sizes'] or '').split(',')
                is_stickers = (message_dict['attachment_is_stickers'] or '').split(',')
                
                for i, guid in enumerate(guids):
                    attachment = {
                        'guid': guid,
                        'filename': filenames[i] if i < len(filenames) else None,
                        'mime_type': mime_types[i] if i < len(mime_types) else None,
                        'size': int(sizes[i]) if i < len(sizes) and sizes[i].isdigit() else None,
                        'is_sticker': bool(int(is_stickers[i])) if i < len(is_stickers) and is_stickers[i].isdigit() else False
                    }
                    attachments.append(attachment)
                
                message_dict['parsed_attachments'] = attachments
            
            messages.append(message_dict)
        
        conn.close()
        return messages
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    except Exception as e:
        print(f"Error: {e}")
        return []