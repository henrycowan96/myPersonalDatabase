import os
import sys
from pathlib import Path
import re
import hashlib
from bs4 import BeautifulSoup
from datetime import datetime
from collections import defaultdict

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from metadata_utils import generate_metadata, save_with_metadata

# Configuration
RAW_DOCS_DIR = Path(__file__).parent.parent / "data" / "raw_docs"
EMAILS_DIR = RAW_DOCS_DIR / "emails"
PROCESSED_EMAILS_DIR = RAW_DOCS_DIR / "emails_processed"
PROCESSED_EMAILS_DIR.mkdir(parents=True, exist_ok=True)

def strip_html_headers_footers(html_content):
    """Remove common email header/footer HTML and extract clean text"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove common footer patterns
    footer_patterns = [
        re.compile(r'unsubscribe', re.IGNORECASE),
        re.compile(r'manage your email preferences', re.IGNORECASE),
        re.compile(r'view in browser', re.IGNORECASE),
        re.compile(r'connect with us on social media', re.IGNORECASE),
        re.compile(r'© \d{4}', re.IGNORECASE),
    ]
    
    # Remove elements matching footer patterns
    for element in soup.find_all(text=True):
        for pattern in footer_patterns:
            if pattern.search(str(element)):
                parent = element.parent
                if parent:
                    parent.decompose()
                break
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Get text
    text = soup.get_text()
    
    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    
    return text

def extract_email_metadata(file_path):
    """Extract metadata from email file"""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Check if file has metadata header
    metadata = {}
    email_content = content
    
    if content.startswith('=== METADATA ==='):
        # Parse existing metadata
        try:
            end_metadata = content.index('=== END METADATA ===')
            metadata_json = content[16:end_metadata].strip()
            import json
            metadata = json.loads(metadata_json)
            email_content = content[end_metadata + 20:].strip()
        except:
            pass
    
    # Extract header info from content if not in metadata
    subject = metadata.get('subject', '')
    sender = metadata.get('author', '')
    date = metadata.get('created_date', '')
    
    if not subject:
        match = re.search(r'Subject:\s*(.+?)(?:\n|$)', email_content)
        if match:
            subject = match.group(1).strip()
    
    if not sender:
        match = re.search(r'From:\s*(.+?)(?:\n|$)', email_content)
        if match:
            sender = match.group(1).strip()
    
    if not date:
        match = re.search(r'Date:\s*(.+?)(?:\n|$)', email_content)
        if match:
            date = match.group(1).strip()
    
    return {
        'subject': subject,
        'sender': sender,
        'date': date,
        'content': email_content,
        'original_metadata': metadata
    }

def clean_email_content(content):
    """Clean email content - strip HTML if present"""
    # Check if content is HTML
    if '<html' in content.lower() or '<!DOCTYPE' in content:
        return strip_html_headers_footers(content)
    return content

def generate_content_hash(content):
    """Generate hash of content for deduplication"""
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def create_better_filename(subject, sender, date):
    """Create a better filename from email metadata"""
    # Clean subject
    clean_subject = re.sub(r'[^\w\s-]', '', subject).strip()
    clean_subject = re.sub(r'\s+', '_', clean_subject)
    
    # Limit length
    if len(clean_subject) > 50:
        clean_subject = clean_subject[:50]
    
    # Extract sender name (before @)
    if '@' in sender:
        sender_name = sender.split('@')[0]
    else:
        sender_name = re.sub(r'[^\w\s-]', '', sender).strip()
        sender_name = re.sub(r'\s+', '_', sender_name)
    
    # Try to parse date for filename
    date_str = ''
    if date:
        try:
            # Try various date formats
            for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%Y-%m-%d', '%m/%d/%Y']:
                try:
                    dt = datetime.strptime(date.split('(')[0].strip(), fmt)
                    date_str = dt.strftime('%Y-%m-%d')
                    break
                except:
                    continue
        except:
            pass
    
    # Build filename
    if date_str:
        filename = f"{date_str}_{sender_name}_{clean_subject}.txt"
    else:
        filename = f"{sender_name}_{clean_subject}.txt"
    
    # Ensure filename is not empty
    if not filename or filename == '.txt':
        filename = f"email_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    return filename

def process_emails():
    """Process all emails in the emails directory"""
    print(f"Processing emails from {EMAILS_DIR}...")
    
    # Get all email files
    email_files = list(EMAILS_DIR.glob('*.txt'))
    print(f"Found {len(email_files)} email files")
    
    # Track content hashes for deduplication
    content_hashes = {}
    duplicates = []
    processed = 0
    errors = 0
    
    for email_file in email_files:
        try:
            # Extract metadata and content
            email_data = extract_email_metadata(email_file)
            
            # Clean content
            clean_content = clean_email_content(email_data['content'])
            
            # Generate hash for deduplication
            content_hash = generate_content_hash(clean_content)
            
            if content_hash in content_hashes:
                duplicates.append((email_file.name, content_hashes[content_hash]))
                print(f"Duplicate detected: {email_file.name}")
                continue
            
            content_hashes[content_hash] = email_file.name
            
            # Create better filename
            better_filename = create_better_filename(
                email_data['subject'],
                email_data['sender'],
                email_data['date']
            )
            
            # Generate metadata
            metadata = generate_metadata(
                source="gmail",
                type="email",
                author=email_data['sender'],
                created_date=email_data['date'],
                modified_date=None,
                subject=email_data['subject'],
                processed_at=datetime.now().isoformat(),
                original_file=email_file.name
            )
            
            # Save processed email
            output_path = PROCESSED_EMAILS_DIR / better_filename
            save_with_metadata(output_path, clean_content, metadata)
            
            print(f"Processed: {email_file.name} -> {better_filename}")
            processed += 1
            
        except Exception as e:
            print(f"Error processing {email_file.name}: {e}")
            errors += 1
    
    print(f"\nComplete!")
    print(f"Processed: {processed} emails")
    print(f"Duplicates removed: {len(duplicates)}")
    print(f"Errors: {errors}")
    print(f"Processed emails saved to {PROCESSED_EMAILS_DIR}")
    
    if duplicates:
        print(f"\nDuplicate pairs:")
        for dup, original in duplicates[:10]:  # Show first 10
            print(f"  {dup} -> {original}")
        if len(duplicates) > 10:
            print(f"  ... and {len(duplicates) - 10} more")

if __name__ == "__main__":
    process_emails()
