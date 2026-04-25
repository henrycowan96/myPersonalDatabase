#!/usr/bin/env python3
"""
Main orchestration script for Personal Database
Runs extraction, processing, ingestion, and launches the application
"""

import os
import sys
import subprocess
import argparse
import signal
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

# Load environment variables
load_dotenv()

# Configuration
PROJECT_ROOT = Path(__file__).parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
APP_DIR = PROJECT_ROOT / "app"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
RAW_DOCS_DIR = PROJECT_ROOT / "data" / "raw_docs"

# Process tracking
backend_process = None
frontend_process = None


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\nShutting down...")
    if backend_process:
        backend_process.terminate()
    if frontend_process:
        frontend_process.terminate()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def run_script(script_name, args=None):
    """Run a Python script from the scripts directory"""
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        print(f"Script not found: {script_path}")
        return False
    
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)
    
    print(f"Running: {script_name}")
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)
        print(f"✓ {script_name} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {script_name} failed with exit code {e.returncode}")
        return False


def fetch_apple_notes_auto():
    """Fetch Apple Notes without interactive prompts"""
    print_section("Fetching Apple Notes")
    
    # Import and modify the script to bypass prompts
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("fetch_apple_notes", SCRIPTS_DIR / "fetch_apple_notes.py")
        module = importlib.util.module_from_spec(spec)
        
        # Monkey-patch input to auto-confirm
        original_input = __builtins__.input
        __builtins__.input = lambda prompt: 'y'
        
        spec.loader.exec_module(module)
        
        # Restore input
        __builtins__.input = original_input
        
        print("✓ Apple Notes fetched successfully")
        return True
    except Exception as e:
        print(f"✗ Error fetching Apple Notes: {e}")
        return False


def parse_messages_auto():
    """Parse Mac Messages without interactive prompts"""
    print_section("Parsing Mac Messages")
    
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("parse_messages", SCRIPTS_DIR / "parse_messages.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.parse_messages()
        print("✓ Messages parsed successfully")
        return True
    except Exception as e:
        print(f"✗ Error parsing messages: {e}")
        return False


def fetch_calendar_auto(days_back=30):
    """Fetch Google Calendar events without interactive prompts"""
    print_section(f"Fetching Google Calendar (last {days_back} days)")
    
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("fetch_calendar", SCRIPTS_DIR / "fetch_calendar.py")
        module = importlib.util.module_from_spec(spec)
        
        # Monkey-patch input to provide default values
        original_input = __builtins__.input
        
        def mock_input(prompt):
            if "Start date" in prompt:
                return ""
            elif "End date" in prompt:
                return ""
            elif "Fetch events" in prompt:
                return 'y'
            return ""
        
        __builtins__.input = mock_input
        spec.loader.exec_module(module)
        __builtins__.input = original_input
        
        print("✓ Calendar events fetched successfully")
        return True
    except Exception as e:
        print(f"✗ Error fetching calendar: {e}")
        return False


def fetch_google_docs_auto():
    """Fetch Google Docs without interactive prompts"""
    print_section("Fetching Google Docs")
    
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("fetch_google_docs", SCRIPTS_DIR / "fetch_google_docs.py")
        module = importlib.util.module_from_spec(spec)
        
        # Monkey-patch input to auto-confirm
        original_input = __builtins__.input
        __builtins__.input = lambda prompt: 'y'
        
        spec.loader.exec_module(module)
        __builtins__.input = original_input
        
        print("✓ Google Docs fetched successfully")
        return True
    except Exception as e:
        print(f"✗ Error fetching Google Docs: {e}")
        return False


def fetch_drive_files_auto():
    """Fetch Google Drive files without interactive prompts"""
    print_section("Fetching Google Drive Files")
    
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("fetch_drive_files", SCRIPTS_DIR / "fetch_drive_files.py")
        module = importlib.util.module_from_spec(spec)
        
        # Monkey-patch input to auto-confirm
        original_input = __builtins__.input
        __builtins__.input = lambda prompt: 'y'
        
        spec.loader.exec_module(module)
        __builtins__.input = original_input
        
        print("✓ Drive files fetched successfully")
        return True
    except Exception as e:
        print(f"✗ Error fetching Drive files: {e}")
        return False


def fetch_emails_auto(max_emails=100):
    """Fetch Gmail without interactive prompts"""
    print_section(f"Fetching Gmail (max {max_emails} emails)")
    
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("fetch_emails", SCRIPTS_DIR / "fetch_emails.py")
        module = importlib.util.module_from_spec(spec)
        
        # Monkey-patch input to provide default values
        original_input = __builtins__.input
        
        def mock_input(prompt):
            if "How many emails" in prompt:
                return str(max_emails)
            elif "Download all" in prompt:
                return 'y'
            return ""
        
        __builtins__.input = mock_input
        spec.loader.exec_module(module)
        __builtins__.input = original_input
        
        print("✓ Emails fetched successfully")
        return True
    except Exception as e:
        print(f"✗ Error fetching emails: {e}")
        return False


def fetch_google_search_history_auto(takeout_path=None):
    """Fetch Google Search History without interactive prompts"""
    print_section("Fetching Google Search History")
    
    if not takeout_path:
        print("✗ Google Search History requires a takeout path")
        print("  Use --takeout-path to specify the path")
        return False
    
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("fetch_google_search_history", SCRIPTS_DIR / "fetch_google_search_history.py")
        module = importlib.util.module_from_spec(spec)
        
        # Monkey-patch input to provide takeout path
        original_input = __builtins__.input
        __builtins__.input = lambda prompt: takeout_path
        
        spec.loader.exec_module(module)
        __builtins__.input = original_input
        
        print("✓ Search history fetched successfully")
        return True
    except Exception as e:
        print(f"✗ Error fetching search history: {e}")
        return False


def process_calendar_auto():
    """Process calendar events"""
    print_section("Processing Calendar Events")
    return run_script("process_calendar.py")


def process_emails_auto():
    """Process emails"""
    print_section("Processing Emails")
    return run_script("process_emails.py")


def ingest_documents():
    """Ingest documents into vector database"""
    print_section("Ingesting Documents into Vector Database")
    return run_script("ingest.py")


def launch_backend():
    """Launch the FastAPI backend server"""
    print_section("Launching Backend API")
    
    global backend_process
    
    try:
        backend_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"],
            cwd=PROJECT_ROOT
        )
        print(f"✓ Backend API launched on http://localhost:8000")
        print(f"  Process ID: {backend_process.pid}")
        return True
    except Exception as e:
        print(f"✗ Error launching backend: {e}")
        return False


def launch_frontend():
    """Launch the React frontend"""
    print_section("Launching Frontend")
    
    global frontend_process
    
    # Check if node_modules exists
    if not (FRONTEND_DIR / "node_modules").exists():
        print("Installing frontend dependencies...")
        try:
            subprocess.run(
                ["npm", "install"],
                cwd=FRONTEND_DIR,
                check=True
            )
            print("✓ Dependencies installed")
        except subprocess.CalledProcessError as e:
            print(f"✗ Error installing dependencies: {e}")
            return False
    
    try:
        frontend_process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=FRONTEND_DIR
        )
        print(f"✓ Frontend launched")
        print(f"  Process ID: {frontend_process.pid}")
        print(f"  Check terminal for the actual URL (typically http://localhost:5173)")
        return True
    except Exception as e:
        print(f"✗ Error launching frontend: {e}")
        return False


def run_extraction(skip_google=False, skip_apple=False, calendar_days=30, email_count=100, takeout_path=None):
    """Run all extraction scripts"""
    print_section("Starting Data Extraction")
    
    results = {}
    
    # Apple-specific extractions
    if not skip_apple:
        if sys.platform == "darwin":  # macOS
            results['apple_notes'] = fetch_apple_notes_auto()
            results['messages'] = parse_messages_auto()
        else:
            print("Skipping Apple Notes and Messages (not on macOS)")
            results['apple_notes'] = None
            results['messages'] = None
    else:
        print("Skipping Apple extractions")
        results['apple_notes'] = None
        results['messages'] = None
    
    # Google extractions
    if not skip_google:
        results['calendar'] = fetch_calendar_auto(days_back=calendar_days)
        results['google_docs'] = fetch_google_docs_auto()
        results['drive_files'] = fetch_drive_files_auto()
        results['emails'] = fetch_emails_auto(max_emails=email_count)
        
        if takeout_path:
            results['search_history'] = fetch_google_search_history_auto(takeout_path=takeout_path)
        else:
            print("Skipping Google Search History (no takeout path provided)")
            results['search_history'] = None
    else:
        print("Skipping Google extractions")
        results['calendar'] = None
        results['google_docs'] = None
        results['drive_files'] = None
        results['emails'] = None
        results['search_history'] = None
    
    # Print summary
    print_section("Extraction Summary")
    for name, success in results.items():
        if success is None:
            status = "SKIPPED"
        elif success:
            status = "✓ SUCCESS"
        else:
            status = "✗ FAILED"
        print(f"  {name:20s}: {status}")
    
    return results


def run_processing():
    """Run all processing scripts"""
    print_section("Starting Data Processing")
    
    results = {}
    
    # Process calendar if calendar files exist
    calendar_dir = RAW_DOCS_DIR / "calendar"
    if calendar_dir.exists() and list(calendar_dir.glob("*_events.txt")):
        results['calendar'] = process_calendar_auto()
    else:
        print("Skipping calendar processing (no calendar files found)")
        results['calendar'] = None
    
    # Process emails if email files exist
    emails_dir = RAW_DOCS_DIR / "emails"
    if emails_dir.exists() and list(emails_dir.glob("*.txt")):
        results['emails'] = process_emails_auto()
    else:
        print("Skipping email processing (no email files found)")
        results['emails'] = None
    
    # Print summary
    print_section("Processing Summary")
    for name, success in results.items():
        if success is None:
            status = "SKIPPED"
        elif success:
            status = "✓ SUCCESS"
        else:
            status = "✗ FAILED"
        print(f"  {name:20s}: {status}")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Personal Database - Extract, process, ingest, and launch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full pipeline: extract, process, ingest, and launch
  python main.py
  
  # Only extract data
  python main.py --extract-only
  
  # Only ingest and launch (skip extraction)
  python main.py --skip-extraction --skip-processing
  
  # Extract with custom parameters
  python main.py --calendar-days 90 --email-count 50
  
  # Launch only (skip all data operations)
  python main.py --skip-extraction --skip-processing --skip-ingestion
  
  # Mobile mode: skip frontend launch (only backend API)
  python main.py --mobile
        """
    )
    
    parser.add_argument(
        "--skip-extraction",
        action="store_true",
        help="Skip data extraction step"
    )
    parser.add_argument(
        "--skip-processing",
        action="store_true",
        help="Skip data processing step"
    )
    parser.add_argument(
        "--skip-ingestion",
        action="store_true",
        help="Skip ingestion into vector database"
    )
    parser.add_argument(
        "--skip-launch",
        action="store_true",
        help="Skip launching backend and frontend"
    )
    parser.add_argument(
        "--skip-google",
        action="store_true",
        help="Skip all Google API extractions"
    )
    parser.add_argument(
        "--skip-apple",
        action="store_true",
        help="Skip all Apple-specific extractions"
    )
    parser.add_argument(
        "--mobile",
        action="store_true",
        help="Mobile mode: skip frontend launch, only run backend API"
    )
    parser.add_argument(
        "--calendar-days",
        type=int,
        default=30,
        help="Number of days to fetch from calendar (default: 30)"
    )
    parser.add_argument(
        "--email-count",
        type=int,
        default=100,
        help="Number of emails to fetch (default: 100)"
    )
    parser.add_argument(
        "--takeout-path",
        type=str,
        help="Path to Google Takeout export for search history"
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("  PERSONAL DATABASE - MAIN ORCHESTRATOR")
    print("=" * 60)
    print(f"  Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Step 1: Extraction
    if not args.skip_extraction:
        run_extraction(
            skip_google=args.skip_google,
            skip_apple=args.skip_apple,
            calendar_days=args.calendar_days,
            email_count=args.email_count,
            takeout_path=args.takeout_path
        )
    
    # Step 2: Processing
    if not args.skip_processing:
        run_processing()
    
    # Step 3: Ingestion
    if not args.skip_ingestion:
        ingest_documents()
    
    # Step 4: Launch
    if not args.skip_launch:
        launch_backend()
        
        # Only launch frontend if not in mobile mode
        if not args.mobile:
            launch_frontend()
        
        print("\n" + "=" * 60)
        print("  APPLICATION RUNNING")
        print("=" * 60)
        print("  Backend API:  http://localhost:8000")
        if args.mobile:
            print("  Frontend:    Mobile app (connect to backend API)")
        else:
            print("  Frontend:    Check terminal for URL (typically http://localhost:5173)")
        print("  Press Ctrl+C to stop")
        print("=" * 60 + "\n")
        
        # Keep running until interrupted
        try:
            if backend_process:
                backend_process.wait()
            if frontend_process and not args.mobile:
                frontend_process.wait()
        except KeyboardInterrupt:
            signal_handler(None, None)
    else:
        print("\n" + "=" * 60)
        print("  COMPLETE")
        print("=" * 60)
        print(f"  Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)


if __name__ == "__main__":
    main()
