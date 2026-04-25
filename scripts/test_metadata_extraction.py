#!/usr/bin/env python3
"""
Test script for metadata extraction functionality
Tests the extract_metadata_from_text function on various file types
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

def extract_metadata_from_text(text):
    """Extract metadata header from text if present"""
    import json
    metadata = {}
    content = text
    
    if text.startswith('=== METADATA ==='):
        try:
            end_metadata = text.index('=== END METADATA ===')
            metadata_json = text[16:end_metadata].strip()
            metadata = json.loads(metadata_json)
            content = text[end_metadata + 20:].strip()
        except (ValueError, json.JSONDecodeError):
            # If parsing fails, use original text
            pass
    
    return metadata, content

def test_file(file_path):
    """Test metadata extraction on a single file"""
    print(f"\n{'='*60}")
    print(f"Testing: {file_path.name}")
    print(f"{'='*60}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Show first 200 chars of original
        print(f"\nOriginal content (first 200 chars):")
        print(content[:200] + "..." if len(content) > 200 else content)
        
        # Extract metadata
        metadata, clean_content = extract_metadata_from_text(content)
        
        print(f"\n--- Metadata Extraction Results ---")
        if metadata:
            print(f"✓ Metadata found: {len(metadata)} fields")
            for key, value in metadata.items():
                print(f"  - {key}: {value}")
        else:
            print("✗ No metadata header found")
        
        print(f"\n--- Clean Content (first 200 chars) ---")
        print(clean_content[:200] + "..." if len(clean_content) > 200 else clean_content)
        
        return metadata is not None
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    print("Testing Metadata Extraction on Different File Types")
    print("="*60)
    
    # Test files of different types
    test_files = [
        # File with new metadata format (messages)
        Path(__file__).parent.parent / "data" / "raw_docs" / "messages" / "conversation_+16092694075.txt",
        
        # File with new metadata format (calendar)
        Path(__file__).parent.parent / "data" / "raw_docs" / "calendar_processed" / "henrysloopai_summary.txt",
        
        # File without metadata (plain text)
        Path(__file__).parent.parent / "data" / "raw_docs" / "Weird Investment Analysis.txt",
        
        # Apple Notes file with old-style metadata (not new format)
        Path(__file__).parent.parent / "data" / "raw_docs" / "apple_notes" / "Decorating 118.txt",
    ]
    
    results = {}
    for file_path in test_files:
        if file_path.exists():
            results[file_path.name] = test_file(file_path)
        else:
            print(f"\n✗ File not found: {file_path}")
            results[file_path.name] = False
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for filename, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {filename}")
    
    total = len(results)
    passed = sum(results.values())
    print(f"\nTotal: {passed}/{total} tests passed")

if __name__ == "__main__":
    main()
