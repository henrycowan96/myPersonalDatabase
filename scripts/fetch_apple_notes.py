import os
import sys
from pathlib import Path
import subprocess
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from metadata_utils import generate_metadata, save_with_metadata

# Configuration
RAW_DOCS_DIR = Path(__file__).parent.parent / "data" / "raw_docs"
APPLE_NOTES_DIR = RAW_DOCS_DIR / "apple_notes"

# Create directories if they don't exist
RAW_DOCS_DIR.mkdir(parents=True, exist_ok=True)
APPLE_NOTES_DIR.mkdir(parents=True, exist_ok=True)

def get_notes_via_applescript():
    """Use AppleScript to get all notes from Apple Notes"""
    applescript = '''
    tell application "Notes"
        set allNotes to every note
        set notesData to {}
        
        repeat with currentNote in allNotes
            set noteName to name of currentNote
            set noteBody to body of currentNote
            set noteCreation to creation date of currentNote
            set noteModification to modification date of currentNote
            
            set noteRecord to {name:noteName, body:noteBody, created:noteCreation as string, modified:noteModification as string}
            set end of notesData to noteRecord
        end repeat
        
        return notesData
    end tell
    '''
    
    try:
        result = subprocess.run(
            ['osascript', '-e', applescript],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running AppleScript: {e}")
        print(f"stderr: {e.stderr}")
        return None

def parse_applescript_output(output):
    """Parse the AppleScript output to extract note data"""
    # This is a simple parser - AppleScript returns a complex structure
    # We'll use a simpler approach: export each note individually
    
    # Alternative approach: get note names first, then export each one
    applescript_list = '''
    tell application "Notes"
        set allNotes to every note
        set noteNames to {}
        
        repeat with currentNote in allNotes
            set end of noteNames to name of currentNote
        end repeat
        
        return noteNames
    end tell
    '''
    
    try:
        result = subprocess.run(
            ['osascript', '-e', applescript_list],
            capture_output=True,
            text=True,
            check=True
        )
        # Parse the output - AppleScript returns comma-separated values
        note_names = [name.strip().strip('"') for name in result.stdout.split(',')]
        return note_names
    except subprocess.CalledProcessError as e:
        print(f"Error listing notes: {e}")
        return []

def export_note_by_name(note_name):
    """Export a single note by name using AppleScript"""
    applescript = f'''
    tell application "Notes"
        set targetNote to first note whose name is "{note_name}"
        set noteBody to body of targetNote
        set noteCreation to creation date of targetNote as string
        set noteModification to modification date of targetNote as string
        
        return noteBody & "|||" & noteCreation & "|||" & noteModification
    end tell
    '''
    
    try:
        result = subprocess.run(
            ['osascript', '-e', applescript],
            capture_output=True,
            text=True,
            check=True
        )
        output = result.stdout.strip()
        
        # Parse the output
        parts = output.split('|||')
        if len(parts) >= 3:
            body = parts[0]
            created = parts[1]
            modified = parts[2]
            return body, created, modified
        else:
            return output, "", ""
    except subprocess.CalledProcessError as e:
        print(f"Error exporting note '{note_name}': {e}")
        return None, None, None

def save_note(note_name, body, created, modified):
    """Save a note to a text file with metadata"""
    # Create a safe filename
    safe_name = "".join(c for c in note_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    if not safe_name:
        safe_name = "unnamed_note"
    
    filename = f"{safe_name}.txt"
    output_path = APPLE_NOTES_DIR / filename
    
    # Generate metadata
    metadata = generate_metadata(
        source="apple_notes",
        type="note",
        author=None,  # Apple Notes doesn't provide author info
        created_date=created,
        modified_date=modified,
        title=note_name
    )
    
    # Format the note content (without the old metadata header)
    note_text = body
    
    # Save with metadata header
    save_with_metadata(output_path, note_text, metadata)
    
    return output_path

def main():
    print("Fetching Apple Notes...")
    
    # Get list of note names
    print("Listing notes...")
    note_names = parse_applescript_output("")
    
    if not note_names:
        print("No notes found or error accessing Notes.")
        return
    
    print(f"Found {len(note_names)} notes")
    
    # Show first few notes
    print("\nFirst 10 notes:")
    for i, name in enumerate(note_names[:10]):
        print(f"  {i + 1}. {name}")
    
    if len(note_names) > 10:
        print(f"  ... and {len(note_names) - 10} more")
    
    confirm = input(f"\nExport all {len(note_names)} notes? (y/n): ")
    if confirm.lower() != 'y':
        print("Aborted.")
        return
    
    print("\nExporting notes...")
    success_count = 0
    error_count = 0
    
    for note_name in note_names:
        try:
            body, created, modified = export_note_by_name(note_name)
            if body is not None:
                output_path = save_note(note_name, body, created, modified)
                print(f"Exported: {note_name[:50]}... -> {output_path.name}")
                success_count += 1
            else:
                error_count += 1
        except Exception as e:
            print(f"Error exporting '{note_name}': {e}")
            error_count += 1
    
    print(f"\nComplete! Exported {success_count} notes to {APPLE_NOTES_DIR}")
    if error_count > 0:
        print(f"Failed to export {error_count} notes")
    print("You can now run 'python scripts/ingest.py' to process these notes.")

if __name__ == "__main__":
    main()
