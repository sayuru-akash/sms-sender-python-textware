import os
import csv
import json
import time
import requests
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Load environment variables
load_dotenv()

# Configure logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
report_dir = Path("reports")
report_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f"sms_sender_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SMSSender:
    """SMS Sender with rate limiting, retrying, and comprehensive error handling"""
    
    def __init__(self):
        self.username = os.getenv("SMS_USERNAME")
        self.password = os.getenv("SMS_PASSWORD")
        self.source = os.getenv("SMS_SOURCE")
        self.api_url = os.getenv("SMS_API_URL")
        self.rate_limit_delay = 2  # Delay in seconds between SMS sends
        self.max_retries = 3
        self.timeout = 30
        
        # Validate credentials
        self._validate_credentials()
        
        # Setup session with retry strategy
        self.session = self._create_session()
        
        # Report data
        self.report_data = []
        
    def _validate_credentials(self) -> None:
        """Validate that all required environment variables are set"""
        required_vars = ["SMS_USERNAME", "SMS_PASSWORD", "SMS_SOURCE", "SMS_API_URL"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            error_msg = f"Missing environment variables: {', '.join(missing_vars)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info("✓ All SMS credentials validated successfully")
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=self.max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"],
            backoff_factor=1
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _send_sms_request(self, phone_number: str, message: str) -> Optional[Dict]:
        """Send SMS via API with retry logic - supports multiple API formats"""
        
        # Format 1: Correct Text-Ware API format (src, dst, text)
        payload_format1 = {
            "username": self.username,
            "password": self.password,
            "src": self.source,  # src instead of source
            "dst": phone_number,   # dst instead of destination
            "text": message        # text instead of message
        }
        
        # Format 2: Alternative with message key
        payload_format2 = {
            "username": self.username,
            "password": self.password,
            "src": self.source,
            "dst": phone_number,
            "msg": message
        }
        
        # Format 3: Alternative parameter names
        payload_format3 = {
            "user": self.username,
            "pass": self.password,
            "sender": self.source,
            "to": phone_number,
            "text": message
        }
        
        payloads = [payload_format1, payload_format2, payload_format3]
        
        try:
            logger.info(f"📤 Sending SMS to {phone_number}...")
            response = None
            last_error = None
            
            # Try each payload format
            for attempt, payload in enumerate(payloads, 1):
                try:
                    logger.debug(f"Attempt {attempt}: Trying payload format {attempt}")
                    response = self.session.post(
                        self.api_url,
                        data=payload,
                        timeout=self.timeout
                    )
                    
                    # If response is 200-299 range (success), break
                    if 200 <= response.status_code < 300:
                        logger.info(f"✓ SMS sent successfully to {phone_number}")
                        logger.debug(f"Response: {response.text}")
                        
                        return {
                            "status": "success",
                            "response": response.text,
                            "status_code": response.status_code,
                            "phone": phone_number,
                            "timestamp": datetime.now().isoformat(),
                            "api_format": attempt
                        }
                    
                    # If it's a client error on all attempts, keep trying
                    last_error = response
                    
                except requests.exceptions.Timeout:
                    last_error = f"Timeout on format {attempt}"
                    continue
                except requests.exceptions.ConnectionError:
                    last_error = f"Connection error on format {attempt}"
                    continue
                except Exception as e:
                    last_error = f"Error on format {attempt}: {str(e)}"
                    continue
            
            # If we got here, all formats failed
            if response is not None:
                error_msg = f"API returned {response.status_code}: {response.text}"
            else:
                error_msg = str(last_error) if last_error else "Unknown error"
            
            logger.error(f"❌ Failed to send SMS to {phone_number}: {error_msg}")
            
            return {
                "status": "error",
                "error": error_msg,
                "status_code": response.status_code if response else None,
                "phone": phone_number,
                "timestamp": datetime.now().isoformat()
            }
            
        except requests.exceptions.Timeout:
            error_msg = f"Timeout error while sending SMS to {phone_number}"
            logger.error(f"❌ {error_msg}")
            return {
                "status": "error",
                "error": error_msg,
                "phone": phone_number,
                "timestamp": datetime.now().isoformat()
            }
            
        except requests.exceptions.ConnectionError:
            error_msg = f"Connection error while sending SMS to {phone_number}"
            logger.error(f"❌ {error_msg}")
            return {
                "status": "error",
                "error": error_msg,
                "phone": phone_number,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            error_msg = f"Unexpected error while sending SMS to {phone_number}: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "status": "error",
                "error": error_msg,
                "phone": phone_number,
                "timestamp": datetime.now().isoformat()
            }
    
    def _send_sms_get_request(self, phone_number: str, message: str) -> Optional[Dict]:
        """Try sending SMS using GET request instead of POST"""
        
        # Build query parameters with correct API format
        params_format1 = {
            "username": self.username,
            "password": self.password,
            "src": self.source,
            "dst": phone_number,
            "text": message
        }
        
        params_format2 = {
            "user": self.username,
            "pass": self.password,
            "sender": self.source,
            "to": phone_number,
            "text": message
        }
        
        params_list = [params_format1, params_format2]
        
        try:
            logger.debug(f"🔄 Trying GET request to SMS API for {phone_number}...")
            
            for attempt, params in enumerate(params_list, 1):
                try:
                    response = self.session.get(
                        self.api_url,
                        params=params,
                        timeout=self.timeout
                    )
                    
                    if 200 <= response.status_code < 300:
                        logger.info(f"✓ SMS sent successfully (GET) to {phone_number}")
                        return {
                            "status": "success",
                            "response": response.text,
                            "status_code": response.status_code,
                            "phone": phone_number,
                            "timestamp": datetime.now().isoformat(),
                            "method": "GET",
                            "format": attempt
                        }
                except Exception as e:
                    logger.debug(f"GET format {attempt} failed: {str(e)}")
                    continue
            
            return None
            
        except Exception as e:
            logger.debug(f"GET request attempt failed: {str(e)}")
            return None
    
    def test_api_connection(self, recipients_file: str = "recipients.csv") -> Dict:
        """Test API connection using first recipient from CSV"""
        logger.info("🧪 Testing SMS API Connection...")
        
        # Load first recipient from CSV for testing
        if not Path(recipients_file).exists():
            error_msg = f"Recipients file not found: {recipients_file}"
            logger.error(f"❌ {error_msg}")
            return {
                "status": "error",
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }
        
        try:
            with open(recipients_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                first_row = next(reader, None)
                
                if not first_row:
                    error_msg = "No recipients found in CSV file"
                    logger.error(f"❌ {error_msg}")
                    return {
                        "status": "error",
                        "error": error_msg,
                        "timestamp": datetime.now().isoformat()
                    }
                
                test_phone = first_row.get("contact_number", "").strip()
                test_name = first_row.get("name", "").strip()
                test_email = first_row.get("email", "").strip()
                
                if not test_phone:
                    error_msg = "No phone number found in first recipient"
                    logger.error(f"❌ {error_msg}")
                    return {
                        "status": "error",
                        "error": error_msg,
                        "timestamp": datetime.now().isoformat()
                    }
                
                logger.info(f"📤 Testing with: {test_name} ({test_phone})")
                test_message = "Test SMS - API Connectivity Check"
                
                # Try POST first
                result = self._send_sms_request(test_phone, test_message)
                result["name"] = test_name
                result["email"] = test_email
                result["message_preview"] = test_message
                
                if result.get("status") == "success":
                    logger.info("✓ API connection successful (POST)")
                    # Add to report
                    self.report_data.append(result)
                    return result
                
                # Try GET if POST fails
                logger.info("🔄 POST failed, trying GET method...")
                get_result = self._send_sms_get_request(test_phone, test_message)
                
                if get_result:
                    get_result["name"] = test_name
                    get_result["email"] = test_email
                    get_result["message_preview"] = test_message
                    logger.info("✓ API connection successful (GET)")
                    # Add to report
                    self.report_data.append(get_result)
                    return get_result
                
                # Both failed
                logger.error("❌ API connection failed - tried both POST and GET methods")
                error_result = {
                    "status": "error",
                    "error": "Both POST and GET methods failed",
                    "post_error": result.get("error"),
                    "timestamp": datetime.now().isoformat(),
                    "name": test_name,
                    "email": test_email,
                    "message_preview": test_message,
                    "phone": test_phone
                }
                # Add to report
                self.report_data.append(error_result)
                return error_result
        
        except Exception as e:
            error_msg = f"Error reading test CSV: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "status": "error",
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }
    

    def send_sms(self, phone_number: str, message: str, name: str = "", email: str = "") -> Dict:
        """Send SMS with rate limiting"""
        
        result = self._send_sms_request(phone_number, message)
        
        # Add additional info to report
        result["name"] = name
        result["email"] = email
        result["message_preview"] = message[:50] + "..." if len(message) > 50 else message
        
        self.report_data.append(result)
        
        # Rate limiting - prevent sending too fast
        time.sleep(self.rate_limit_delay)
        
        return result
    
    def send_bulk_sms(self, recipients_file: str, message: str) -> Dict:
        """Send SMS to multiple recipients from CSV"""
        
        if not Path(recipients_file).exists():
            error_msg = f"Recipients file not found: {recipients_file}"
            logger.error(f"❌ {error_msg}")
            raise FileNotFoundError(error_msg)
        
        results = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "details": []
        }
        
        try:
            with open(recipients_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    results["total"] += 1
                    
                    # Extract data from CSV
                    name = row.get("name", "").strip()
                    email = row.get("email", "").strip()
                    contact_number = row.get("contact_number", "").strip()
                    
                    # Validate phone number
                    if not contact_number:
                        logger.warning(f"⚠ Skipping recipient with no contact number: {name}")
                        results["failed"] += 1
                        results["details"].append({
                            "status": "skipped",
                            "name": name,
                            "email": email,
                            "reason": "No contact number provided"
                        })
                        continue
                    
                    # Personalize message
                    personalized_message = message.replace("{name}", name) if name else message
                    
                    # Send SMS
                    result = self.send_sms(contact_number, personalized_message, name, email)
                    
                    if result["status"] == "success":
                        results["successful"] += 1
                    else:
                        results["failed"] += 1
                    
                    results["details"].append(result)
            
            logger.info(f"\n{'='*60}")
            logger.info(f"📊 BULK SMS CAMPAIGN COMPLETED")
            logger.info(f"{'='*60}")
            logger.info(f"Total Recipients: {results['total']}")
            logger.info(f"✓ Successfully Sent: {results['successful']}")
            logger.info(f"❌ Failed: {results['failed']}")
            logger.info(f"{'='*60}\n")
            
        except csv.Error as e:
            error_msg = f"Error reading CSV file: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error during bulk SMS send: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise
        
        return results
    
    def save_report(self) -> str:
        """Save report to JSON file"""
        
        report_filename = f"sms_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = report_dir / report_filename
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_sms": len(self.report_data),
            "successful": sum(1 for r in self.report_data if r.get("status") == "success"),
            "failed": sum(1 for r in self.report_data if r.get("status") == "error"),
            "details": self.report_data
        }
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"📄 Report saved to: {report_path}")
            return str(report_path)
            
        except Exception as e:
            logger.error(f"❌ Failed to save report: {str(e)}")
            raise


def get_sms_message() -> str:
    """Get the SMS message about CCA Bootcamp"""
    
    return """Dear Student, {name}

We're excited to announce that the CCA Bootcamp Programs Inauguration Ceremony will be held today.

This will be the official launch session for our bootcamp programs under BYOW, DDIGITAL, RANDS, and VAT0. We warmly invite you to join us and be part of this important beginning.

Date: 22 March 2026
Time: 9.00 PM
Platform: Zoom

Join Link: https://us06web.zoom.us/j/85143454719?pwd=ppwZBbAjxq2v3mr6td368TpiFvZa02.1

Passcode: 331423

We look forward to having you with us tonight.

SITC Campus X CodeZela"""


def main():
    """Main function to send SMS"""
    
    logger.info("="*60)
    logger.info("🚀 SMS SENDER APPLICATION STARTED")
    logger.info("="*60)
    
    try:
        # Initialize SMS Sender
        sender = SMSSender()
        
        # Get message
        message_template = get_sms_message()
        
        # Send bulk SMS
        recipients_file = "recipients.csv"
        results = sender.send_bulk_sms(recipients_file, message_template)
        
        # Save report
        report_path = sender.save_report()
        
        logger.info(f"✓ SMS campaign completed successfully!")
        logger.info(f"Report available at: {report_path}")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {str(e)}")
        raise


if __name__ == "__main__":
    main()






