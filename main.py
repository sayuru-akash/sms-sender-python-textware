#!/usr/bin/env python3
"""
SMS Campaign Sender - Main Entry Point
Complete SMS sending solution with logging, reporting, and error handling
"""

import sys
import argparse
from pathlib import Path
from sms_sender import SMSSender, get_sms_message
import logging

logger = logging.getLogger(__name__)


def run_test_campaign():
    """Run a test campaign with API diagnostic"""
    print("\n" + "="*60)
    print("🧪 TEST SMS - API DIAGNOSTIC")
    print("="*60 + "\n")
    
    try:
        sender = SMSSender()
        
        print("📤 Testing API connection with multiple methods...")
        print("---\n")
        
        # Use improved test method
        result = sender.test_api_connection()
        
        print("\n📊 TEST RESULT:")
        print("-" * 60)
        print(f"Status: {result['status'].upper()}")
        print(f"Phone: {result.get('phone', 'N/A')}")
        print(f"Timestamp: {result['timestamp']}")
        
        if result.get('method'):
            print(f"Method Used: {result['method']}")
        if result.get('api_format'):
            print(f"Parameter Format: {result['api_format']}")
        
        if result['status'] == 'success':
            print(f"✓ API Response: {result['response']}")
            print(f"✓ API Status Code: {result['status_code']}")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
        
        # Save report
        report_path = sender.save_report()
        print(f"\n📄 Report saved: {report_path}")
        print("="*60 + "\n")
        
        return result['status'] == 'success'
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def run_bulk_campaign():
    """Run full bulk SMS campaign"""
    print("\n" + "="*60)
    print("🚀 BULK SMS CAMPAIGN")
    print("="*60 + "\n")
    
    try:
        sender = SMSSender()
        message_template = get_sms_message()
        
        recipients_file = "recipients.csv"
        if not Path(recipients_file).exists():
            print(f"❌ Recipients file not found: {recipients_file}")
            return False
        
        # Send campaign
        results = sender.send_bulk_sms(recipients_file, message_template)
        
        # Save report
        report_path = sender.save_report()
        
        print(f"\n✓ Campaign completed!")
        print(f"Report saved: {report_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Campaign failed: {str(e)}")
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="SMS Campaign Sender",
        epilog="Examples:\n"
               "  python main.py --test        # Send test SMS\n"
               "  python main.py --bulk        # Send bulk campaign\n"
               "  python main.py --streamlit   # Launch Streamlit dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--test",
        action="store_true",
        help="Send a test SMS to verify API connectivity"
    )
    
    parser.add_argument(
        "--bulk",
        action="store_true",
        help="Send SMS to all recipients in recipients.csv"
    )
    
    parser.add_argument(
        "--streamlit",
        action="store_true",
        help="Launch interactive Streamlit dashboard"
    )
    
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if not any([args.test, args.bulk, args.streamlit]):
        parser.print_help()
        print("\n💡 Tip: Use --test to send a test SMS first")
        return
    
    # Test send
    if args.test:
        success = run_test_campaign()
        sys.exit(0 if success else 1)
    
    # Bulk send
    if args.bulk:
        success = run_bulk_campaign()
        sys.exit(0 if success else 1)
    
    # Streamlit dashboard
    if args.streamlit:
        import subprocess
        print("\n🚀 Launching Streamlit dashboard...")
        try:
            subprocess.run(
                [sys.executable, "-m", "streamlit", "run", "streamlit_app.py"],
                check=True,
            )
        except KeyboardInterrupt:
            print("\n⏹️ Streamlit dashboard stopped.")
        except subprocess.CalledProcessError as exc:
            print(f"❌ Streamlit failed to start or exited unexpectedly (code {exc.returncode}).")
            sys.exit(exc.returncode)


if __name__ == "__main__":
    main()
