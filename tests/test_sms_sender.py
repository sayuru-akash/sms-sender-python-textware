from pathlib import Path
import json

import pandas as pd
import pytest

import sms_sender
from sms_sender import (
    SMSSender,
    is_valid_email,
    limit_name_to_two_words,
    normalize_sl_phone_number,
    sanitize_recipient,
)


class DummyResponse:
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text


@pytest.mark.parametrize(
    ("raw_name", "expected"),
    [
        ("", ""),
        ("Sayuru", "Sayuru"),
        ("Sayuru Akash", "Sayuru Akash"),
        ("Sayuru Akash Perera", "Sayuru Akash"),
    ],
)
def test_limit_name_to_two_words(raw_name, expected):
    assert limit_name_to_two_words(raw_name) == expected


@pytest.mark.parametrize(
    ("raw_phone", "expected"),
    [
        ("0777123456", "94777123456"),
        ("777123456", "94777123456"),
        ("94777123456", "94777123456"),
        ("+94 77 712 3456", "94777123456"),
        ("0094777123456", "94777123456"),
    ],
)
def test_normalize_sl_phone_number_valid_formats(raw_phone, expected):
    assert normalize_sl_phone_number(raw_phone) == expected


@pytest.mark.parametrize("raw_phone", ["", "12345", "0612345678", "94799123456", None])
def test_normalize_sl_phone_number_invalid_formats(raw_phone):
    assert normalize_sl_phone_number(raw_phone) is None


def test_is_valid_email():
    assert is_valid_email("user@example.com") is True
    assert is_valid_email("user.name+alias@example.co.uk") is True
    assert is_valid_email("invalid-email") is False
    assert is_valid_email("") is False


def test_sanitize_recipient_returns_cleaned_values_and_errors():
    cleaned = sanitize_recipient("  Sayuru Akash Perera  ", "TEST@Example.com", "0777123456")
    assert cleaned["name"] == "Sayuru Akash"
    assert cleaned["email"] == "test@example.com"
    assert cleaned["contact_number"] == "94777123456"
    assert cleaned["is_valid"] is True

    invalid = sanitize_recipient("", "bad-email", "12345")
    assert invalid["is_valid"] is False
    assert "Missing name" in invalid["errors"]
    assert "Invalid email" in invalid["errors"]
    assert "Invalid Sri Lanka mobile number" in invalid["errors"]


def test_smssender_requires_environment_variables(monkeypatch):
    monkeypatch.delenv("SMS_USERNAME", raising=False)
    monkeypatch.delenv("SMS_PASSWORD", raising=False)
    monkeypatch.delenv("SMS_SOURCE", raising=False)
    monkeypatch.delenv("SMS_API_URL", raising=False)

    with pytest.raises(ValueError, match="Missing environment variables"):
        SMSSender()


def test_send_sms_request_success_uses_first_payload_format(sms_env):
    sender = SMSSender()
    captured_payloads = []

    def fake_post(url, data, timeout):
        captured_payloads.append((url, data, timeout))
        return DummyResponse(200, "queued")

    sender.session.post = fake_post
    result = sender._send_sms_request("94777123456", "hello")

    assert result["status"] == "success"
    assert result["api_format"] == 1
    assert captured_payloads[0][0] == "https://example.com/send"
    assert captured_payloads[0][1]["src"] == "TESTSRC"
    assert captured_payloads[0][1]["dst"] == "94777123456"
    assert captured_payloads[0][1]["text"] == "hello"


def test_send_sms_request_returns_error_after_all_payloads_fail(sms_env):
    sender = SMSSender()
    calls = []

    def fake_post(url, data, timeout):
        calls.append(data)
        return DummyResponse(400, "bad request")

    sender.session.post = fake_post
    result = sender._send_sms_request("94777123456", "hello")

    assert result["status"] == "error"
    assert result["status_code"] == 400
    assert "API returned 400" in result["error"]
    assert len(calls) == 3


def test_send_sms_get_request_can_succeed_on_second_format(sms_env):
    sender = SMSSender()
    responses = [RuntimeError("first failed"), DummyResponse(200, "ok")]

    def fake_get(url, params, timeout):
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    sender.session.get = fake_get
    result = sender._send_sms_get_request("94777123456", "hello")

    assert result["status"] == "success"
    assert result["method"] == "GET"
    assert result["format"] == 2


def test_send_sms_invalid_recipient_does_not_hit_api(sms_env):
    sender = SMSSender()

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("API should not be called for invalid recipient")

    sender._send_sms_request = fail_if_called
    result = sender.send_sms("12345", "hello", "Test", "bad-email")

    assert result["status"] == "error"
    assert "Invalid email" in result["error"]
    assert len(sender.report_data) == 1


def test_send_sms_success_appends_report_and_respects_sleep(sms_env, monkeypatch):
    sender = SMSSender()
    sleep_calls = []

    monkeypatch.setattr(sms_sender.time, "sleep", lambda seconds: sleep_calls.append(seconds))
    monkeypatch.setattr(
        sender,
        "_send_sms_request",
        lambda phone_number, message: {
            "status": "success",
            "response": "ok",
            "status_code": 200,
            "phone": phone_number,
            "timestamp": "2026-03-22T00:00:00",
        },
    )

    result = sender.send_sms("0777123456", "hello", "Test User", "test@example.com")

    assert result["status"] == "success"
    assert result["name"] == "Test User"
    assert sender.report_data[-1]["status"] == "success"
    assert sleep_calls == [2]


def test_send_bulk_sms_dataframe_handles_invalid_and_duplicate_rows(sms_env, no_sleep):
    sender = SMSSender()
    sender._send_sms_request = lambda phone_number, message: {
        "status": "success",
        "response": "ok",
        "status_code": 200,
        "phone": phone_number,
        "timestamp": "2026-03-22T00:00:00",
    }

    recipients_df = pd.DataFrame(
        [
            {"name": "Alice Silva", "email": "alice@example.com", "contact_number": "0777123456"},
            {"name": "Bad User", "email": "bad-email", "contact_number": "0777123457"},
            {"name": "Dup User", "email": "dup@example.com", "contact_number": "94777123456"},
        ]
    )

    result = sender.send_bulk_sms_dataframe(recipients_df, "Hello {name}")

    assert result["total"] == 3
    assert result["successful"] == 1
    assert result["failed"] == 2
    assert [item["status"] for item in result["details"]] == ["success", "skipped", "skipped"]


def test_send_bulk_sms_reads_csv_file(tmp_path, monkeypatch, sms_env, no_sleep):
    monkeypatch.chdir(tmp_path)
    csv_path = tmp_path / "recipients.csv"
    csv_path.write_text(
        "name,email,contact_number\nAlice,alice@example.com,0777123456\n",
        encoding="utf-8",
    )

    sender = SMSSender()
    sender._send_sms_request = lambda phone_number, message: {
        "status": "success",
        "response": "ok",
        "status_code": 200,
        "phone": phone_number,
        "timestamp": "2026-03-22T00:00:00",
    }

    result = sender.send_bulk_sms("recipients.csv", "Hello {name}")

    assert result["total"] == 1
    assert result["successful"] == 1
    assert result["details"][0]["name"] == "Alice"


def test_test_api_connection_returns_error_for_missing_csv(sms_env):
    sender = SMSSender()
    result = sender.test_api_connection("missing.csv")

    assert result["status"] == "error"
    assert "Recipients file not found" in result["error"]


def test_test_api_connection_can_fallback_to_get(tmp_path, monkeypatch, sms_env):
    csv_path = tmp_path / "recipients.csv"
    csv_path.write_text(
        "name,email,contact_number\nInvalid,bad-email,123\nValid User,valid@example.com,0777123456\n",
        encoding="utf-8",
    )

    sender = SMSSender()
    monkeypatch.setattr(
        sender,
        "_send_sms_request",
        lambda *_args, **_kwargs: {"status": "error", "error": "POST failed", "timestamp": "2026-03-22T00:00:00"},
    )
    monkeypatch.setattr(
        sender,
        "_send_sms_get_request",
        lambda *_args, **_kwargs: {
            "status": "success",
            "response": "ok",
            "status_code": 200,
            "phone": "94777123456",
            "timestamp": "2026-03-22T00:00:00",
            "method": "GET",
            "format": 2,
        },
    )

    result = sender.test_api_connection(str(csv_path))

    assert result["status"] == "success"
    assert result["method"] == "GET"
    assert result["name"] == "Valid User"


def test_save_report_writes_json_with_failed_count_for_non_success(
    sms_env, isolated_report_dir
):
    sender = SMSSender()
    sender.report_data = [
        {"status": "success", "name": "Alice"},
        {"status": "error", "name": "Bob"},
        {"status": "skipped", "name": "Carol"},
    ]

    report_path = sender.save_report()

    payload = json.loads((isolated_report_dir / Path(report_path).name).read_text(encoding="utf-8"))
    assert payload["total_sms"] == 3
    assert payload["successful"] == 1
    assert payload["failed"] == 2
