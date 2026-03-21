import os
import csv
import json
import time
import re
import requests
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

import pandas as pd
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
        logging.FileHandler(
            log_dir / f"sms_sender_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DEFAULT_MESSAGE_TEMPLATE = """Dear Student, {name}

We're excited to announce that the CCA Bootcamp Programs Inauguration Ceremony will be held today.

This will be the official launch session for our bootcamp programs under BYOW, DDIGITAL, RANDS, and VAT0. We warmly invite you to join us and be part of this important beginning.

Date: 22 March 2026
Time: 9.00 PM
Platform: Zoom

Join Link: https://us06web.zoom.us/j/85143454719?pwd=ppwZBbAjxq2v3mr6td368TpiFvZa02.1

Passcode: 331423

We look forward to having you with us tonight.

SITC Campus X CodeZela"""
MESSAGE_TEMPLATE_FILE = Path(__file__).with_name("message_template.txt")


def limit_name_to_two_words(name: str) -> str:
    """Limit name to first 2 words only"""
    if not name:
        return name
    words = name.strip().split()
    return " ".join(words[:2])


def normalize_sl_phone_number(phone: str) -> Optional[str]:
    """Normalize Sri Lankan mobile numbers to 94XXXXXXXXX format.

    Accepted inputs:
    - 9 digits: 7XXXXXXXX
    - 10 digits: 07XXXXXXXX
    - 11 digits: 947XXXXXXXX
    - +94 / separators like spaces, dashes, parentheses are tolerated
    """
    if phone is None:
        return None

    raw = str(phone).strip()
    if not raw:
        return None

    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        return None

    if len(digits) == 9 and digits.startswith("7"):
        normalized = f"94{digits}"
    elif len(digits) == 10 and digits.startswith("07"):
        normalized = f"94{digits[1:]}"
    elif len(digits) == 11 and digits.startswith("94"):
        normalized = digits
    elif len(digits) == 13 and digits.startswith("0094"):
        normalized = digits[2:]
    else:
        return None

    # Mobile format must be 94 + 9 digits, with local part starting 7X.
    if not re.fullmatch(r"94(7[0-8]\d{7})", normalized):
        return None

    return normalized


def is_valid_email(email: str) -> bool:
    """Validate email with a practical, strict-enough pattern."""
    if email is None:
        return False
    value = str(email).strip()
    if not value:
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", value))


def sanitize_recipient(name: str, email: str, phone: str) -> Dict:
    """Return cleaned recipient fields and validation errors."""
    cleaned_name = limit_name_to_two_words((name or "").strip())
    cleaned_email = (email or "").strip().lower()
    cleaned_phone = normalize_sl_phone_number(phone)

    errors: List[str] = []
    if not cleaned_name:
        errors.append("Missing name")
    if not cleaned_email or not is_valid_email(cleaned_email):
        errors.append("Invalid email")
    if not cleaned_phone:
        errors.append("Invalid Sri Lanka mobile number")

    return {
        "name": cleaned_name,
        "email": cleaned_email,
        "contact_number": cleaned_phone,
        "errors": errors,
        "is_valid": len(errors) == 0,
    }


class SMSSender:
    """SMS Sender with rate limiting, retrying, and comprehensive error handling"""

    def __init__(self):
        self.username = os.getenv("SMS_USERNAME") or ""
        self.password = os.getenv("SMS_PASSWORD") or ""
        self.source = os.getenv("SMS_SOURCE") or ""
        self.api_url = os.getenv("SMS_API_URL") or ""
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
        required_vars = ["SMS_USERNAME",
                         "SMS_PASSWORD", "SMS_SOURCE", "SMS_API_URL"]
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

    def _send_sms_request(self, phone_number: str, message: str) -> Dict:
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
                    logger.debug(
                        f"Attempt {attempt}: Trying payload format {attempt}")
                    response = self.session.post(
                        self.api_url,
                        data=payload,
                        timeout=self.timeout
                    )

                    # If response is 200-299 range (success), break
                    if 200 <= response.status_code < 300:
                        logger.info(
                            f"✓ SMS sent successfully to {phone_number}")
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

            logger.error(
                f"❌ Failed to send SMS to {phone_number}: {error_msg}")

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
            logger.debug(
                f"🔄 Trying GET request to SMS API for {phone_number}...")

            for attempt, params in enumerate(params_list, 1):
                try:
                    response = self.session.get(
                        self.api_url,
                        params=params,
                        timeout=self.timeout
                    )

                    if 200 <= response.status_code < 300:
                        logger.info(
                            f"✓ SMS sent successfully (GET) to {phone_number}")
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
                valid_row = None
                for row in reader:
                    cleaned = sanitize_recipient(
                        row.get("name", ""),
                        row.get("email", ""),
                        row.get("contact_number", "")
                    )
                    if cleaned["is_valid"]:
                        valid_row = cleaned
                        break

                if not valid_row:
                    error_msg = "No valid recipients found in CSV file"
                    logger.error(f"❌ {error_msg}")
                    return {
                        "status": "error",
                        "error": error_msg,
                        "timestamp": datetime.now().isoformat()
                    }

                test_phone = valid_row["contact_number"]
                test_name = valid_row["name"]
                test_email = valid_row["email"]

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
                get_result = self._send_sms_get_request(
                    test_phone, test_message)

                if get_result:
                    get_result["name"] = test_name
                    get_result["email"] = test_email
                    get_result["message_preview"] = test_message
                    logger.info("✓ API connection successful (GET)")
                    # Add to report
                    self.report_data.append(get_result)
                    return get_result

                # Both failed
                logger.error(
                    "❌ API connection failed - tried both POST and GET methods")
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

        cleaned = sanitize_recipient(name, email, phone_number)
        if not cleaned["is_valid"]:
            result = {
                "status": "error",
                "error": "; ".join(cleaned["errors"]),
                "phone": phone_number,
                "name": cleaned["name"],
                "email": cleaned["email"],
                "timestamp": datetime.now().isoformat(),
                "message_preview": message[:50] + "..." if len(message) > 50 else message,
            }
            self.report_data.append(result)
            return result

        result = self._send_sms_request(cleaned["contact_number"], message)

        # Add additional info to report
        result["name"] = cleaned["name"]
        result["email"] = cleaned["email"]
        result["message_preview"] = message[:50] + \
            "..." if len(message) > 50 else message

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

        try:
            with open(recipients_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                return self._send_bulk_rows(reader, message)
        except csv.Error as e:
            error_msg = f"Error reading CSV file: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error during bulk SMS send: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise

    def send_bulk_sms_dataframe(self, recipients_df: pd.DataFrame, message: str) -> Dict:
        """Send SMS to multiple recipients from a dataframe."""
        if recipients_df is None or recipients_df.empty:
            raise ValueError("Recipients dataframe is empty")

        records = recipients_df.fillna("").to_dict(orient="records")
        return self._send_bulk_rows(records, message)

    def _send_bulk_rows(self, rows, message: str) -> Dict:
        """Send SMS to multiple recipients from row dictionaries."""

        results = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "details": []
        }

        try:
            seen_numbers = set()

            for row in rows:
                results["total"] += 1

                cleaned = sanitize_recipient(
                    row.get("name", ""),
                    row.get("email", ""),
                    row.get("contact_number", "")
                )

                if not cleaned["is_valid"]:
                    logger.warning(
                        f"⚠ Skipping invalid recipient: {cleaned['name'] or 'Unknown'} ({'; '.join(cleaned['errors'])})")
                    skipped_result = {
                        "status": "skipped",
                        "name": cleaned["name"],
                        "email": cleaned["email"],
                        "contact_number": str(row.get("contact_number", "")).strip(),
                        "reason": "; ".join(cleaned["errors"]),
                        "timestamp": datetime.now().isoformat(),
                    }
                    results["failed"] += 1
                    results["details"].append(skipped_result)
                    self.report_data.append(skipped_result)
                    continue

                name = cleaned["name"]
                email = cleaned["email"]
                contact_number = cleaned["contact_number"]

                if contact_number in seen_numbers:
                    logger.warning(
                        f"⚠ Skipping duplicate phone number: {contact_number} ({name})")
                    skipped_result = {
                        "status": "skipped",
                        "name": name,
                        "email": email,
                        "contact_number": contact_number,
                        "reason": "Duplicate contact number",
                        "timestamp": datetime.now().isoformat(),
                    }
                    results["failed"] += 1
                    results["details"].append(skipped_result)
                    self.report_data.append(skipped_result)
                    continue

                seen_numbers.add(contact_number)

                personalized_message = message.replace(
                    "{name}", name) if name else message

                result = self.send_sms(
                    contact_number, personalized_message, name, email)

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
            "failed": sum(1 for r in self.report_data if r.get("status") != "success"),
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


def load_message_template(template_path: str | Path | None = None) -> str:
    """Load the default message template from disk, with a safe fallback."""
    target_path = Path(template_path) if template_path else MESSAGE_TEMPLATE_FILE

    try:
        message = target_path.read_text(encoding="utf-8").strip()
        if message:
            return message
        logger.warning("Message template file is empty: %s. Falling back to built-in default.", target_path)
    except FileNotFoundError:
        logger.warning("Message template file not found: %s. Falling back to built-in default.", target_path)
    except OSError as exc:
        logger.warning("Failed to read message template file %s: %s. Falling back to built-in default.", target_path, exc)

    return DEFAULT_MESSAGE_TEMPLATE


def get_sms_message(template_path: str | Path | None = None) -> str:
    """Get the default SMS message template."""
    return load_message_template(template_path)


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
