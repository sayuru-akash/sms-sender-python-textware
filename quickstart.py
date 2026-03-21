#!/usr/bin/env python3
"""
SMS Campaign Manager - Quick Start Utility
Helps with initial setup and provides easy shortcuts
"""

import os
import sys
import subprocess
from pathlib import Path


def print_header():
    """Print welcome header"""
    print("\n" + "="*70)
    print("📱 SMS CAMPAIGN MANAGER - QUICK START")
    print("="*70 + "\n")


def check_setup():
    """Check if everything is set up correctly"""
    print("🔍 Checking setup...\n")
    
    checks = {
        ".env file": Path(".env").exists(),
        "recipients.csv file": Path("recipients.csv").exists(),
        "sms_sender.py": Path("sms_sender.py").exists(),
        "streamlit_app.py": Path("streamlit_app.py").exists(),
        "requirements.txt": Path("requirements.txt").exists(),
    }
    
    all_good = True
    for check, result in checks.items():
        status = "✓" if result else "✗"
        print(f"  {status} {check}")
        if not result:
            all_good = False
    
    print()
    return all_good


def show_menu():
    """Show main menu"""
    print("\n" + "="*70)
    print("WHAT WOULD YOU LIKE TO DO?")
    print("="*70)
    print("""
  1️⃣  Send Test SMS
       └─ Sends a single test SMS to verify API connectivity
       └─ Fast and safe way to test before bulk sending
       
  2️⃣  Send Bulk Campaign
       └─ Sends SMS to all recipients in recipients.csv
       └─ Shows detailed progress and results
       
  3️⃣  Launch Dashboard
       └─ Open interactive Streamlit web interface
       └─ Recommended for most users (easier to use)
       
  4️⃣  View Reports
       └─ Display all campaign reports and logs
       
  5️⃣  Check Status
       └─ Show setup status and available files
       
  6️⃣  View Documentation
       └─ Display README and setup guides
       
  7️⃣  Exit
       └─ Close this program

""")
    
    choice = input("Enter your choice (1-7): ").strip()
    return choice


def run_test():
    """Run test SMS"""
    print("\n" + "="*70)
    print("🧪 RUNNING TEST SMS")
    print("="*70 + "\n")
    subprocess.run([sys.executable, "main.py", "--test"])


def run_bulk():
    """Run bulk campaign"""
    print("\n" + "="*70)
    print("🚀 RUNNING BULK CAMPAIGN")
    print("="*70 + "\n")
    confirm = input("⚠️  This will send SMS to all recipients in recipients.csv\nContinue? (y/n): ").strip().lower()
    if confirm == 'y':
        subprocess.run([sys.executable, "main.py", "--bulk"])
    else:
        print("❌ Cancelled")


def run_dashboard():
    """Run Streamlit dashboard"""
    print("\n" + "="*70)
    print("🚀 LAUNCHING DASHBOARD")
    print("="*70 + "\n")
    print("Opening Streamlit dashboard...")
    print("🌐 Dashboard will open at: http://localhost:8501\n")
    subprocess.run([sys.executable, "main.py", "--streamlit"])


def view_reports():
    """View available reports"""
    print("\n" + "="*70)
    print("📊 AVAILABLE REPORTS")
    print("="*70 + "\n")
    
    report_dir = Path("reports")
    if not report_dir.exists():
        print("No reports directory found. Run a campaign first.")
        return
    
    reports = sorted(report_dir.glob("*.json"), key=os.path.getmtime, reverse=True)
    
    if not reports:
        print("No reports found. Run a campaign to generate reports.")
        return
    
    print("Recent reports:\n")
    for i, report in enumerate(reports[:10], 1):
        size = report.stat().st_size
        mtime = Path(report).stat().st_mtime
        print(f"  {i}. {report.name} ({size} bytes)")
    
    print("\n📂 Reports directory: reports/")
    print("💡 Open with: cat reports/sms_report_*.json")


def check_status():
    """Show detailed status"""
    print("\n" + "="*70)
    print("📋 SYSTEM STATUS")
    print("="*70 + "\n")
    
    print("✓ Setup Files:")
    print(f"  • .env: {Path('.env').exists()}")
    print(f"  • recipients.csv: {Path('recipients.csv').exists()}")
    print(f"  • sms_sender.py: {Path('sms_sender.py').exists()}")
    print(f"  • streamlit_app.py: {Path('streamlit_app.py').exists()}")
    
    print("\n📁 Generated Directories:")
    print(f"  • logs/: {Path('logs').exists()} - {len(list(Path('logs').glob('*.log')))} log files" if Path('logs').exists() else "  • logs/: Not created yet")
    print(f"  • reports/: {Path('reports').exists()} - {len(list(Path('reports').glob('*.json')))} report files" if Path('reports').exists() else "  • reports/: Not created yet")
    
    print("\n📦 Python Environment:")
    try:
        import requests
        print("  ✓ requests")
    except:
        print("  ✗ requests - Install with: pip install requests")
    
    try:
        import dotenv
        print("  ✓ python-dotenv")
    except:
        print("  ✗ python-dotenv - Install with: pip install python-dotenv")
    
    try:
        import pandas
        print("  ✓ pandas")
    except:
        print("  ✗ pandas - Install with: pip install pandas")
    
    try:
        import streamlit
        print("  ✓ streamlit")
    except:
        print("  ✗ streamlit - Install with: pip install streamlit")


def view_docs():
    """Show documentation"""
    print("\n" + "="*70)
    print("📚 DOCUMENTATION")
    print("="*70 + "\n")
    
    print("""
QUICK REFERENCE:

📱 Test Send:
  python main.py --test
  └─ Send single SMS to verify API works

🚀 Bulk Send:
  python main.py --bulk
  └─ Send to all recipients in recipients.csv

🎯 Dashboard (Recommended):
  python main.py --streamlit
  └─ Open interactive web interface

📊 View Reports:
  ls reports/
  cat reports/sms_report_*.json

📋 Check Logs:
  ls logs/
  tail -f logs/sms_sender_*.log

📁 Project Structure:
  PythonProjectSMS/
  ├── main.py                 ← Entry point
  ├── sms_sender.py           ← SMS sending engine
  ├── streamlit_app.py        ← Dashboard
  ├── .env                    ← API credentials
  ├── recipients.csv          ← Recipient list
  ├── logs/                   ← Application logs
  ├── reports/                ← Campaign reports
  ├── requirements.txt        ← Dependencies
  ├── README.md               ← Full documentation
  └── IMPLEMENTATION.md       ← Setup guide

🔑 Key Features:
  ✓ Rate limiting (2 sec between SMS)
  ✓ Automatic retry (3 attempts)
  ✓ Error handling & logging
  ✓ JSON reports
  ✓ Message personalization
  ✓ CSV recipient management

❓ Having Issues?
  1. Check logs/ directory for error details
  2. Run: python main.py --test
  3. View: cat reports/sms_report_*.json
  4. Read: README.md or IMPLEMENTATION.md

💡 Next Steps:
  1. Read README.md for complete guide
  2. Run: python main.py --streamlit
  3. Add your recipients in the dashboard
  4. Test with: python main.py --test
  5. Send campaign when ready
""")


def main():
    """Main menu loop"""
    print_header()
    
    # Check setup
    if not check_setup():
        print("\n⚠️  WARNING: Some files are missing!")
        print("Please ensure all files are in the project directory.")
        return
    
    print("✓ All setup files found!\n")
    
    while True:
        choice = show_menu()
        
        if choice == "1":
            run_test()
        elif choice == "2":
            run_bulk()
        elif choice == "3":
            run_dashboard()
        elif choice == "4":
            view_reports()
        elif choice == "5":
            check_status()
        elif choice == "6":
            view_docs()
        elif choice == "7":
            print("\n👋 Goodbye!\n")
            break
        else:
            print("❌ Invalid choice. Please try again.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏸️  Cancelled by user\n")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}\n")

