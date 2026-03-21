from pathlib import Path
import json

import pandas as pd
import pytest

import sms_sender
from sms_sender import (
    SMSSender,
    extract_operation_id,
    is_valid_email,
    limit_name_to_two_words,
    normalize_sl_phone_number,
    personalize_message,
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

    contact_only = sanitize_recipient("", "", "0777123457")
    assert contact_only["name"] == ""
    assert contact_only["email"] == ""
    assert contact_only["contact_number"] == "94777123457"
    assert contact_only["is_valid"] is True

    invalid = sanitize_recipient("", "bad-email", "12345")
    assert invalid["is_valid"] is False
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
    assert result["gateway_status"] == "accepted"
    assert result["delivery_confirmed"] is False
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
    assert result["gateway_status"] == "accepted"


def test_extract_operation_id_returns_id_when_present():
    assert extract_operation_id("Operation success: 1774126971489888") == "1774126971489888"


def test_extract_operation_id_returns_none_for_non_matching_text():
    assert extract_operation_id("queued") is None


def test_personalize_message_handles_missing_name_without_leaving_placeholder():
    assert personalize_message("Hello {name}", "") == "Hello"
    assert personalize_message("Dear {name}, welcome!", "") == "Dear, welcome!"


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


def test_send_bulk_sms_dataframe_allows_contact_number_only_rows(sms_env, no_sleep):
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
            {"contact_number": "0777123456"},
            {"contact_number": "0777123457", "name": "", "email": ""},
        ]
    )

    result = sender.send_bulk_sms_dataframe(recipients_df, "Hello {name}")

    assert result["total"] == 2
    assert result["successful"] == 2
    assert result["failed"] == 0


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


def test_send_sms_request_timeout_on_all_formats_returns_timeout_error(sms_env):
    import requests

    sender = SMSSender()
    sender.session.post = lambda *_args, **_kwargs: (_ for _ in ()).throw(requests.exceptions.Timeout())

    result = sender._send_sms_request("94777123456", "hello")

    assert result["status"] == "error"
    assert "Timeout on format 3" in result["error"]


def test_send_sms_request_connection_error_on_all_formats_returns_connection_error(sms_env):
    import requests

    sender = SMSSender()
    sender.session.post = lambda *_args, **_kwargs: (_ for _ in ()).throw(requests.exceptions.ConnectionError())

    result = sender._send_sms_request("94777123456", "hello")

    assert result["status"] == "error"
    assert "Connection error on format 3" in result["error"]


def test_send_sms_request_generic_error_on_all_formats_returns_last_error(sms_env):
    sender = SMSSender()
    sender.session.post = lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("bad payload"))

    result = sender._send_sms_request("94777123456", "hello")

    assert result["status"] == "error"
    assert "Error on format 3: bad payload" in result["error"]


def test_send_sms_get_request_returns_none_when_all_formats_fail(sms_env):
    sender = SMSSender()
    sender.session.get = lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("fail"))
    assert sender._send_sms_get_request("94777123456", "hello") is None


def test_test_api_connection_returns_error_when_no_valid_rows_exist(tmp_path, sms_env):
    csv_path = tmp_path / "recipients.csv"
    csv_path.write_text(
        "name,email,contact_number\nInvalid,bad-email,123\n",
        encoding="utf-8",
    )

    sender = SMSSender()
    result = sender.test_api_connection(str(csv_path))

    assert result["status"] == "error"
    assert "No valid recipients found" in result["error"]


def test_test_api_connection_returns_error_when_post_and_get_fail(tmp_path, monkeypatch, sms_env):
    csv_path = tmp_path / "recipients.csv"
    csv_path.write_text(
        "name,email,contact_number\nValid User,valid@example.com,0777123456\n",
        encoding="utf-8",
    )

    sender = SMSSender()
    monkeypatch.setattr(
        sender,
        "_send_sms_request",
        lambda *_args, **_kwargs: {"status": "error", "error": "POST failed", "timestamp": "2026-03-22T00:00:00"},
    )
    monkeypatch.setattr(sender, "_send_sms_get_request", lambda *_args, **_kwargs: None)

    result = sender.test_api_connection(str(csv_path))

    assert result["status"] == "error"
    assert result["error"] == "Both POST and GET methods failed"
    assert result["post_error"] == "POST failed"


def test_send_bulk_sms_raises_for_missing_file(sms_env):
    sender = SMSSender()
    with pytest.raises(FileNotFoundError):
        sender.send_bulk_sms("missing.csv", "Hello")


def test_send_bulk_sms_wraps_csv_error(tmp_path, monkeypatch, sms_env):
    csv_path = tmp_path / "recipients.csv"
    csv_path.write_text("name,email,contact_number\n", encoding="utf-8")

    sender = SMSSender()

    def bad_open(*_args, **_kwargs):
        raise sms_sender.csv.Error("bad csv")

    monkeypatch.setattr(sms_sender, "open", bad_open, raising=False)
    with pytest.raises(ValueError, match="Error reading CSV file"):
        sender.send_bulk_sms(str(csv_path), "Hello")


def test_send_bulk_sms_reraises_unexpected_error(tmp_path, monkeypatch, sms_env):
    csv_path = tmp_path / "recipients.csv"
    csv_path.write_text("name,email,contact_number\nAlice,alice@example.com,0777123456\n", encoding="utf-8")
    sender = SMSSender()
    monkeypatch.setattr(sender, "_send_bulk_rows", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")))

    with pytest.raises(RuntimeError, match="boom"):
        sender.send_bulk_sms(str(csv_path), "Hello")


def test_send_bulk_sms_dataframe_rejects_empty_dataframe(sms_env):
    sender = SMSSender()
    with pytest.raises(ValueError, match="Recipients dataframe is empty"):
        sender.send_bulk_sms_dataframe(pd.DataFrame(), "Hello")


def test_send_bulk_rows_counts_error_status_as_failed(sms_env, monkeypatch):
    sender = SMSSender()
    monkeypatch.setattr(
        sender,
        "send_sms",
        lambda *_args, **_kwargs: {"status": "error", "timestamp": "2026-03-22T00:00:00"},
    )
    rows = [{"name": "Alice", "email": "alice@example.com", "contact_number": "0777123456"}]

    result = sender._send_bulk_rows(rows, "Hello {name}")

    assert result["successful"] == 0
    assert result["failed"] == 1


def test_send_bulk_rows_reraises_unexpected_error(sms_env, monkeypatch):
    sender = SMSSender()
    monkeypatch.setattr(sender, "send_sms", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("send failed")))
    rows = [{"name": "Alice", "email": "alice@example.com", "contact_number": "0777123456"}]

    with pytest.raises(RuntimeError, match="send failed"):
        sender._send_bulk_rows(rows, "Hello {name}")


def test_save_report_reraises_when_write_fails(sms_env, monkeypatch):
    sender = SMSSender()
    sender.report_data = [{"status": "success"}]

    def bad_open(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(sms_sender, "open", bad_open, raising=False)
    with pytest.raises(OSError, match="disk full"):
        sender.save_report()


def test_get_sms_message_returns_non_empty_template():
    message = sms_sender.get_sms_message()
    assert isinstance(message, str)
    assert message.strip()


def test_get_sms_message_reads_from_template_file(tmp_path):
    template_path = tmp_path / "message_template.txt"
    template_path.write_text("Hello {name}\nFrom file", encoding="utf-8")

    message = sms_sender.get_sms_message(template_path)

    assert message == "Hello {name}\nFrom file"


def test_get_sms_message_falls_back_when_template_file_missing(tmp_path):
    message = sms_sender.get_sms_message(tmp_path / "missing_template.txt")

    assert message == sms_sender.DEFAULT_MESSAGE_TEMPLATE


def test_get_sms_message_falls_back_when_template_file_empty(tmp_path):
    template_path = tmp_path / "message_template.txt"
    template_path.write_text("   \n", encoding="utf-8")

    message = sms_sender.get_sms_message(template_path)

    assert message == sms_sender.DEFAULT_MESSAGE_TEMPLATE


def test_sms_sender_main_success(monkeypatch, sms_env):
    class FakeSender:
        def send_bulk_sms(self, recipients_file, message):
            assert recipients_file == "recipients.csv"
            return {"total": 1}

        def save_report(self):
            return "reports/test.json"

    monkeypatch.setattr(sms_sender, "SMSSender", FakeSender)
    monkeypatch.setattr(sms_sender, "get_sms_message", lambda: "message")

    result = sms_sender.main()
    assert result == {"total": 1}


def test_sms_sender_main_reraises_errors(monkeypatch, sms_env):
    class BrokenSender:
        def send_bulk_sms(self, recipients_file, message):
            raise RuntimeError("fatal")

        def save_report(self):
            return "reports/test.json"

    monkeypatch.setattr(sms_sender, "SMSSender", lambda: BrokenSender())
    monkeypatch.setattr(sms_sender, "get_sms_message", lambda: "message")

    with pytest.raises(RuntimeError, match="fatal"):
        sms_sender.main()
