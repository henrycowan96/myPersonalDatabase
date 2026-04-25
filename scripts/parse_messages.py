import sys
import json
import re
import csv
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

sys.path.append(str(Path(__file__).parent.parent))
from metadata_utils import generate_metadata, save_with_metadata

# ── Configuration ──────────────────────────────────────────────────────────────
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw_docs" / "messages"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Supported input formats and their default paths
INPUT_DIR = Path(__file__).parent.parent / "data" / "raw_docs" / "message_exports"
INPUT_DIR.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE   = 30
CHUNK_OVERLAP = 5


# ── Text cleaning ──────────────────────────────────────────────────────────────

def clean_text(raw: str | None) -> str | None:
    """Clean message text for mobile exports."""
    if not raw:
        return None
    text = raw.strip()

    # Remove non-printable characters
    text = re.sub(r"[^\x20-\x7E\n\r\t]", " ", text)

    # Collapse whitespace
    text = re.sub(r"\s{2,}", " ", text).strip()

    # Reject if too short
    if len(text) < 2:
        return None

    return text


# ── Contact name resolution ────────────────────────────────────────────────────

def load_contacts(contacts_file: Optional[Path] = None) -> dict[str, str]:
    """Load contacts from a JSON or CSV file."""
    contacts: dict[str, str] = {}
    
    if not contacts_file or not contacts_file.exists():
        return contacts
    
    try:
        if contacts_file.suffix == '.json':
            with open(contacts_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for contact in data:
                    if isinstance(contact, dict):
                        name = contact.get('name') or contact.get('display_name', '')
                        phone = contact.get('phone') or contact.get('number', '')
                        email = contact.get('email', '')
                        
                        if name:
                            if phone:
                                contacts[phone.strip().lower()] = name
                                digits = re.sub(r"\D", "", phone)
                                if digits:
                                    contacts[digits] = name
                            if email:
                                contacts[email.strip().lower()] = name
                                
        elif contacts_file.suffix == '.csv':
            with open(contacts_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get('name') or row.get('display_name', '')
                    phone = row.get('phone') or row.get('number', '')
                    email = row.get('email', '')
                    
                    if name:
                        if phone:
                            contacts[phone.strip().lower()] = name
                            digits = re.sub(r"\D", "", phone)
                            if digits:
                                contacts[digits] = name
                        if email:
                            contacts[email.strip().lower()] = name
    except Exception as e:
        print(f"Error loading contacts: {e}")
    
    return contacts


def resolve_contact(handle: str, contacts: dict[str, str]) -> str:
    if handle.lower() in contacts:
        return contacts[handle.lower()]
    digits = re.sub(r"\D", "", handle)
    if digits in contacts:
        return contacts[digits]
    if len(digits) > 10 and digits[-10:] in contacts:
        return contacts[digits[-10:]]
    return handle


# ── Mobile message parsers ────────────────────────────────────────────────────

def parse_timestamp(ts: str, format_hint: Optional[str] = None) -> datetime:
    """Parse various timestamp formats from mobile exports."""
    if not ts:
        return datetime.now()
    
    # Try common formats
    formats = [
        format_hint,
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M",
        "%m/%d/%Y %H:%M",
        "%d/%m/%Y",
        "%m/%d/%Y",
    ]
    
    for fmt in formats:
        if fmt:
            try:
                return datetime.strptime(ts, fmt)
            except ValueError:
                continue
    
    # Try Unix timestamp
    try:
        return datetime.fromtimestamp(float(ts))
    except ValueError:
        pass
    
    # If all else fails, return current time
    return datetime.now()


def parse_json_messages(file_path: Path) -> List[Dict[str, Any]]:
    """Parse messages from JSON export (common format: iOS/Android backup tools)."""
    messages = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle different JSON structures
        if isinstance(data, list):
            messages = data
        elif isinstance(data, dict):
            if 'messages' in data:
                messages = data['messages']
            elif 'conversations' in data:
                for conv in data['conversations']:
                    if 'messages' in conv:
                        messages.extend(conv['messages'])
            else:
                # Try to treat the dict as a single message
                messages = [data]
        
        # Normalize message structure
        normalized = []
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            
            normalized_msg = {
                'text': msg.get('text') or msg.get('body') or msg.get('message') or msg.get('content', ''),
                'timestamp': msg.get('timestamp') or msg.get('date') or msg.get('time') or msg.get('created_at', ''),
                'sender': msg.get('sender') or msg.get('from') or msg.get('phone_number') or msg.get('address', ''),
                'is_from_me': msg.get('is_from_me', False) or msg.get('sent_by_me', False) or msg.get('direction') == 'outgoing',
                'contact': msg.get('contact') or msg.get('name') or msg.get('recipient', ''),
            }
            normalized.append(normalized_msg)
        
        return normalized
        
    except Exception as e:
        print(f"Error parsing JSON messages: {e}")
        return []


def parse_csv_messages(file_path: Path) -> List[Dict[str, Any]]:
    """Parse messages from CSV export (common format: SMS Backup & Restore)."""
    messages = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                msg = {
                    'text': row.get('body') or row.get('message') or row.get('text', ''),
                    'timestamp': row.get('date') or row.get('timestamp') or row.get('time', ''),
                    'sender': row.get('address') or row.get('phone') or row.get('number', ''),
                    'is_from_me': row.get('type') == '2' or row.get('direction') == 'outgoing' or row.get('sent_by_me', False),
                    'contact': row.get('contact_name') or row.get('name', ''),
                }
                messages.append(msg)
        
        return messages
        
    except Exception as e:
        print(f"Error parsing CSV messages: {e}")
        return []


def parse_xml_messages(file_path: Path) -> List[Dict[str, Any]]:
    """Parse messages from XML export (common format: Android SMS backup)."""
    messages = []
    
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Try common XML structures
        for msg_elem in root.findall('.//sms') + root.findall('.//message') + root.findall('.//msg'):
            msg = {
                'text': msg_elem.get('body') or msg_elem.get('text') or msg_elem.text or '',
                'timestamp': msg_elem.get('date') or msg_elem.get('timestamp') or msg_elem.get('time', ''),
                'sender': msg_elem.get('address') or msg_elem.get('phone') or msg_elem.get('number', ''),
                'is_from_me': msg_elem.get('type') == '2' or msg_elem.get('direction') == 'outgoing',
                'contact': msg_elem.get('contact_name') or msg_elem.get('name', ''),
            }
            messages.append(msg)
        
        return messages
        
    except Exception as e:
        print(f"Error parsing XML messages: {e}")
        return []


# ── RAG chunking ──────────────────────────────────────────────────────────────

def chunk_and_write(handle: str, label: str, messages: list[dict]) -> int:
    safe_id = re.sub(r"[^\w+\-]", "_", handle).strip("_")
    step    = max(1, CHUNK_SIZE - CHUNK_OVERLAP)
    total   = len(messages)
    written = 0

    for ci, start in enumerate(range(0, total, step)):
        batch = messages[start: start + CHUNK_SIZE]
        if not batch:
            break

        first_dt = parse_timestamp(batch[0].get('timestamp', ''))
        last_dt  = parse_timestamp(batch[-1].get('timestamp', ''))

        metadata = generate_metadata(
            source="mobile_messages",
            type="conversation_chunk",
            author=handle,
            contact=label,
            created_date=first_dt.isoformat(),
            modified_date=last_dt.isoformat(),
            message_count=len(batch),
            chunk_index=ci,
            chunk_start_msg=start,
            total_messages=total,
        )

        lines = [
            f"Contact: {label}",
            f"Messages {start+1}–{start+len(batch)} of {total}  "
            f"({first_dt.strftime('%Y-%m-%d')} → {last_dt.strftime('%Y-%m-%d')})",
            "=" * 60, "",
        ]
        for msg in batch:
            dt  = parse_timestamp(msg.get('timestamp', '')).strftime("%Y-%m-%d %H:%M")
            who = "Me" if msg.get('is_from_me', False) else label
            lines.append(f"[{dt}] {who}: {msg.get('text', '')}")

        suffix   = f"_chunk{ci:03d}" if total > CHUNK_SIZE else ""
        out_path = OUTPUT_DIR / f"conversation_{safe_id}{suffix}.txt"
        save_with_metadata(out_path, "\n".join(lines), metadata)
        written += 1

    return written


# ── Main ──────────────────────────────────────────────────────────────────────

def parse_messages(input_file: Optional[Path] = None, contacts_file: Optional[Path] = None):
    """
    Parse mobile messages from export files.
    
    Args:
        input_file: Path to specific message export file (JSON, CSV, or XML)
        contacts_file: Path to contacts file (JSON or CSV)
    """
    # Load contacts
    print("Loading contacts …")
    if contacts_file:
        contacts = load_contacts(contacts_file)
    else:
        # Try to find contacts file in INPUT_DIR
        contacts_file = INPUT_DIR / "contacts.json"
        if not contacts_file.exists():
            contacts_file = INPUT_DIR / "contacts.csv"
        contacts = load_contacts(contacts_file) if contacts_file.exists() else {}
    print(f"  {len(contacts)} entries")

    # Find message export files
    if input_file:
        message_files = [input_file]
    else:
        message_files = []
        for ext in ['*.json', '*.csv', '*.xml']:
            message_files.extend(INPUT_DIR.glob(ext))
        
        if not message_files:
            print(f"No message export files found in {INPUT_DIR}")
            print("Supported formats: JSON, CSV, XML")
            print("Place your message exports in the message_exports directory")
            return

    all_messages: List[Dict[str, Any]] = []
    
    for file_path in message_files:
        print(f"Parsing {file_path.name} …")
        
        if file_path.suffix == '.json':
            messages = parse_json_messages(file_path)
        elif file_path.suffix == '.csv':
            messages = parse_csv_messages(file_path)
        elif file_path.suffix == '.xml':
            messages = parse_xml_messages(file_path)
        else:
            print(f"  Unsupported format: {file_path.suffix}")
            continue
        
        print(f"  {len(messages)} messages found")
        all_messages.extend(messages)
    
    if not all_messages:
        print("No messages to process")
        return

    # Group messages by contact/sender
    conversations: dict[str, list[dict]] = defaultdict(list)
    skipped = 0

    for msg in all_messages:
        cleaned = clean_text(msg.get('text'))
        if not cleaned:
            skipped += 1
            continue

        # Use contact name if available, otherwise use sender
        handle = msg.get('contact') or msg.get('sender') or 'unknown'
        conversations[handle].append({
            "timestamp":   msg.get('timestamp', ''),
            "text":        cleaned,
            "is_from_me":  msg.get('is_from_me', False),
        })

    print(f"  {skipped} messages skipped")
    print(f"  {len(conversations)} conversations\n")

    total_files = 0
    for handle, messages in sorted(conversations.items()):
        if not messages:
            continue
        label      = resolve_contact(handle, contacts)
        n_files    = chunk_and_write(handle, label, messages)
        total_files += n_files
        display    = label if label != handle else handle
        print(f"  {display}: {len(messages)} msgs → {n_files} file(s)")

    print(f"\nDone. {total_files} file(s) → {OUTPUT_DIR}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Parse mobile messages from export files")
    parser.add_argument("--input", type=Path, help="Path to message export file")
    parser.add_argument("--contacts", type=Path, help="Path to contacts file")
    args = parser.parse_args()
    
    parse_messages(input_file=args.input, contacts_file=args.contacts)