import os
import sys
from pathlib import Path
import json
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

load_dotenv()

# Configuration
RAW_DOCS_DIR = Path(__file__).parent.parent / "data" / "raw_docs"
GOOGLE_SEARCH_DIR = RAW_DOCS_DIR / "google_search_history"

# Create directories if they don't exist
RAW_DOCS_DIR.mkdir(parents=True, exist_ok=True)
GOOGLE_SEARCH_DIR.mkdir(parents=True, exist_ok=True)

def find_takeout_file(takeout_path):
    """Find the search history JSON file in a Google Takeout export"""
    takeout_path = Path(takeout_path)
    
    # Common paths for search history in Takeout exports
    possible_paths = [
        takeout_path / "Takeout" / "My Activity" / "Search" / "MyActivity.json",
        takeout_path / "My Activity" / "Search" / "MyActivity.json",
        takeout_path / "MyActivity.json",
    ]
    
    # Also search recursively for any MyActivity.json
    if not any(p.exists() for p in possible_paths):
        for json_file in takeout_path.rglob("MyActivity.json"):
            possible_paths.append(json_file)
    
    for path in possible_paths:
        if path.exists():
            return path
    
    return None

def parse_activity_json(json_path):
    """Parse Google Takeout activity JSON and extract search queries"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    search_entries = []
    
    # Google Takeout JSON structure
    for item in data:
        if 'title' in item:
            # The title contains the search query
            title = item['title']
            time_str = item.get('time', '')
            
            # Parse timestamp if available
            timestamp = None
            if time_str:
                try:
                    # Google uses format like "2024-01-15T10:30:00Z"
                    timestamp = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                except:
                    pass
            
            search_entries.append({
                'query': title,
                'timestamp': timestamp,
                'raw_time': time_str
            })
    
    return search_entries

def save_search_history(search_entries):
    """Save search history to text files organized by date"""
    if not search_entries:
        print("No search entries found.")
        return
    
    # Group by date
    entries_by_date = {}
    for entry in search_entries:
        if entry['timestamp']:
            date_key = entry['timestamp'].strftime('%Y-%m-%d')
        else:
            date_key = 'unknown_date'
        
        if date_key not in entries_by_date:
            entries_by_date[date_key] = []
        entries_by_date[date_key].append(entry)
    
    # Save each date's searches to a separate file
    for date_key, entries in entries_by_date.items():
        # Sort by timestamp
        entries.sort(key=lambda x: x['timestamp'] or datetime.min)
        
        # Create content
        content_lines = [f"Google Search History - {date_key}\n"]
        content_lines.append("=" * 50 + "\n\n")
        
        for entry in entries:
            timestamp_str = entry['timestamp'].strftime('%H:%M:%S') if entry['timestamp'] else entry['raw_time']
            content_lines.append(f"[{timestamp_str}] {entry['query']}\n")
        
        content = ''.join(content_lines)
        
        # Save to file
        output_path = GOOGLE_SEARCH_DIR / f"search_history_{date_key}.txt"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Saved {len(entries)} searches to {output_path}")
    
    return len(entries_by_date)

def fetch_search_history_from_json(json_path):
    """Parse Google Takeout activity JSON and return search entries
    
    Args:
        json_path: Path to the MyActivity.json file
    
    Returns:
        List of dictionaries containing search query data
    """
    return parse_activity_json(json_path)

def main():
    print("Google Search History Importer")
    print("=" * 50)
    print("\nThis script processes Google Takeout exports to import your search history.")
    print("\nTo get your search history:")
    print("1. Go to https://takeout.google.com/")
    print("2. Select 'My Activity' (or 'All data included' -> 'My Activity')")
    print("3. Choose JSON format")
    print("4. Download and extract the zip file")
    print()
    
    takeout_path = input("Enter the path to your extracted Google Takeout folder: ").strip()
    
    if not takeout_path:
        print("No path provided. Exiting.")
        return
    
    takeout_path = Path(takeout_path)
    
    if not takeout_path.exists():
        print(f"Path does not exist: {takeout_path}")
        return
    
    print(f"\nSearching for search history in: {takeout_path}")
    
    activity_file = find_takeout_file(takeout_path)
    
    if not activity_file:
        print("Could not find MyActivity.json in the Takeout export.")
        print("\nMake sure you:")
        print("- Selected 'My Activity' in Google Takeout")
        print("- Chose JSON format")
        print("- Extracted the zip file completely")
        return
    
    print(f"Found activity file: {activity_file}")
    
    print("\nParsing search history...")
    search_entries = parse_activity_json(activity_file)
    
    print(f"Found {len(search_entries)} search entries")
    
    if not search_entries:
        print("No search entries found in the file.")
        return
    
    print("\nSaving search history...")
    files_created = save_search_history(search_entries)
    
    print(f"\nComplete! Created {files_created} files in {GOOGLE_SEARCH_DIR}")
    print("You can now run 'python scripts/ingest.py' to process these files.")

if __name__ == "__main__":
    main()
