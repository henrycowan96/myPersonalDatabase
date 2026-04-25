import os
import sys
from pathlib import Path
import re
import shutil
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from metadata_utils import generate_metadata, save_with_metadata

# Configuration
RAW_DOCS_DIR = Path(__file__).parent.parent / "data" / "raw_docs"
ORGANIZED_DIR = RAW_DOCS_DIR / "organized"
ORGANIZED_DIR.mkdir(parents=True, exist_ok=True)

# Define categories and their patterns
CATEGORIES = {
    'school': {
        'keywords': ['school', 'class', 'homework', 'assignment', 'exam', 'test', 'midterm', 'final', 'grade', 'teacher', 'professor', 'cbu', 'accel', 'econ', 'lit', 'gov', 'french', 'russian', 'math', 'calculus', 'history', 'world', 'english'],
        'patterns': [r'\b(hw|homework)\b', r'\b(chapter|section)\s+\d+', r'\b(test|exam|quiz)\b'],
        'description': 'School-related documents including homework, assignments, and class materials'
    },
    'essays': {
        'keywords': ['essay', 'paper', 'thesis', 'dissertation', 'personal statement', 'application', 'georgetown', 'upenn', 'dartmouth', 'muhlenberg', 'scholarship', 'supplemental'],
        'patterns': [r'\bessay\b', r'\bpaper\b', r'\bstatement\b', r'\bapplication\b'],
        'description': 'College essays, personal statements, and application materials'
    },
    'work': {
        'keywords': ['work', 'job', 'internship', 'resume', 'cv', 'sloop', 'cbu', 'consulting', 'business', 'company', 'startup', 'entrepreneur', 'meeting', 'professional'],
        'patterns': [r'\bresume\b', r'\bcv\b', r'\binternship\b', r'\bjob\b'],
        'description': 'Work-related documents including resumes, internships, and professional materials'
    },
    'notes': {
        'keywords': ['note', 'notes', 'outline', 'summary', 'guide', 'reference', 'research', 'data', 'analysis', 'plan', 'ideas', 'thoughts'],
        'patterns': [r'\bnotes?\b', r'\boutline\b', r'\bsummary\b', r'\bguide\b'],
        'description': 'Personal notes, outlines, and reference materials'
    },
    'finance': {
        'keywords': ['investment', 'stock', 'etf', 'finance', 'money', 'bank', 'credit', 'dividend', 'portfolio', 'trading', 'market', 'vanguard', 'brokerage'],
        'patterns': [r'\binvestment\b', r'\bstock\b', r'\b(etf|etf)\b', r'\bportfolio\b'],
        'description': 'Finance and investment-related documents'
    },
    'personal': {
        'keywords': ['personal', 'blog', 'diary', 'journal', 'birthday', 'family', 'friend', 'social', 'club', 'activity', 'hobby', 'music', 'setlist'],
        'patterns': [r'\bblog\b', r'\bdiary\b', r'\bsetlist\b'],
        'description': 'Personal documents including blogs, journals, and personal activities'
    },
    'travel': {
        'keywords': ['travel', 'trip', 'flight', 'hotel', 'reservation', 'vacation', 'destination', 'itinerary'],
        'patterns': [r'\btravel\b', r'\btrip\b', r'\bflight\b', r'\bhotel\b'],
        'description': 'Travel-related documents and itineraries'
    },
    'projects': {
        'keywords': ['project', 'app', 'website', 'code', 'programming', 'development', 'github', 'repo', 'software', 'tech', 'ai', 'machine learning'],
        'patterns': [r'\bproject\b', r'\bapp\b', r'\bwebsite\b', r'\bcode\b'],
        'description': 'Project and development-related documents'
    }
}

def categorize_file(filename, content):
    """Categorize a file based on filename and content"""
    filename_lower = filename.lower()
    content_lower = content.lower() if content else ''
    
    scores = {category: 0 for category in CATEGORIES}
    
    for category, config in CATEGORIES.items():
        # Check keywords in filename
        for keyword in config['keywords']:
            if keyword.lower() in filename_lower:
                scores[category] += 3  # Filename matches are weighted higher
        
        # Check keywords in content
        for keyword in config['keywords']:
            if keyword.lower() in content_lower:
                scores[category] += 1
        
        # Check patterns in content
        for pattern in config['patterns']:
            if re.search(pattern, content_lower):
                scores[category] += 2
    
    # Find category with highest score
    max_score = max(scores.values())
    if max_score == 0:
        return 'uncategorized'
    
    # Get all categories with max score (in case of tie)
    max_categories = [cat for cat, score in scores.items() if score == max_score]
    
    # Return first max category, or 'uncategorized' if tie
    if len(max_categories) == 1:
        return max_categories[0]
    else:
        return 'uncategorized'

def read_file_content(file_path):
    """Read file content with error handling"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except:
        return ''

def organize_files():
    """Organize root .txt files into categorized subdirectories"""
    print(f"Organizing files from {RAW_DOCS_DIR}...")
    
    # Get all .txt files in root directory (not in subdirectories)
    txt_files = [f for f in RAW_DOCS_DIR.glob('*.txt') if f.is_file()]
    
    # Filter out files that are already in subdirectories
    txt_files = [f for f in txt_files if f.parent == RAW_DOCS_DIR]
    
    print(f"Found {len(txt_files)} .txt files in root directory")
    
    # Create category directories
    for category in CATEGORIES.keys():
        category_dir = ORGANIZED_DIR / category
        category_dir.mkdir(parents=True, exist_ok=True)
    
    # Create uncategorized directory
    uncategorized_dir = ORGANIZED_DIR / 'uncategorized'
    uncategorized_dir.mkdir(parents=True, exist_ok=True)
    
    # Track statistics
    stats = {category: 0 for category in CATEGORIES.keys()}
    stats['uncategorized'] = 0
    errors = 0
    
    for file_path in txt_files:
        try:
            filename = file_path.name
            content = read_file_content(file_path)
            
            # Categorize file
            category = categorize_file(filename, content)
            
            # Determine destination directory
            if category == 'uncategorized':
                dest_dir = uncategorized_dir
            else:
                dest_dir = ORGANIZED_DIR / category
            
            # Copy file to destination (keeping original)
            dest_path = dest_dir / filename
            
            # Handle duplicate filenames
            counter = 1
            while dest_path.exists():
                name_without_ext = file_path.stem
                dest_path = dest_dir / f"{name_without_ext}_{counter}{file_path.suffix}"
                counter += 1
            
            # Copy file
            shutil.copy2(file_path, dest_path)
            
            # Add metadata about organization
            metadata = generate_metadata(
                source="file_organization",
                type="document",
                author=None,
                created_date=None,
                modified_date=datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                original_path=str(file_path),
                category=category,
                organized_at=datetime.now().isoformat()
            )
            
            # Save with metadata (will create new file with metadata header)
            # We'll just add metadata to the copied file
            with open(dest_path, 'r', encoding='utf-8', errors='ignore') as f:
                original_content = f.read()
            
            save_with_metadata(dest_path, original_content, metadata)
            
            stats[category] += 1
            print(f"Organized: {filename} -> {category}/")
            
        except Exception as e:
            print(f"Error organizing {filename}: {e}")
            errors += 1
    
    # Print summary
    print(f"\nOrganization complete!")
    print(f"Total files processed: {len(txt_files)}")
    print(f"Errors: {errors}")
    print(f"\nFiles by category:")
    for category, count in stats.items():
        if count > 0:
            print(f"  {category}: {count}")
    
    print(f"\nOrganized files saved to {ORGANIZED_DIR}")
    print(f"Original files remain in {RAW_DOCS_DIR}")
    
    # Create category summary file
    summary_path = ORGANIZED_DIR / "organization_summary.txt"
    summary_content = "File Organization Summary\n"
    summary_content += "=" * 50 + "\n\n"
    summary_content += f"Organized at: {datetime.now().isoformat()}\n"
    summary_content += f"Total files: {len(txt_files)}\n\n"
    
    for category, config in CATEGORIES.items():
        count = stats[category]
        if count > 0:
            summary_content += f"\n{category.upper()} ({count} files)\n"
            summary_content += f"  Description: {config['description']}\n"
            summary_content += f"  Keywords: {', '.join(config['keywords'][:5])}...\n"
    
    if stats['uncategorized'] > 0:
        summary_content += f"\nUNCATEGORIZED ({stats['uncategorized']} files)\n"
        summary_content += "  These files didn't match any category patterns\n"
    
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(summary_content)
    
    print(f"\nSummary saved to {summary_path}")

if __name__ == "__main__":
    organize_files()
