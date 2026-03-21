from pathlib import Path

import pytest

import sms_sender


@pytest.fixture
def sms_env(monkeypatch):
    monkeypatch.setenv("SMS_USERNAME", "test-user")
    monkeypatch.setenv("SMS_PASSWORD", "test-pass")
    monkeypatch.setenv("SMS_SOURCE", "TESTSRC")
    monkeypatch.setenv("SMS_API_URL", "https://example.com/send")


@pytest.fixture
def no_sleep(monkeypatch):
    monkeypatch.setattr(sms_sender.time, "sleep", lambda *_args, **_kwargs: None)


@pytest.fixture
def isolated_report_dir(tmp_path, monkeypatch):
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    monkeypatch.setattr(sms_sender, "report_dir", report_dir)
    return report_dir


@pytest.fixture
def sample_csv_content():
    return "name,email,contact_number\nSayuru Akash,test@gmail.com,0777123456\n"


@pytest.fixture
def project_files(tmp_path):
    for filename in ["sms_sender.py", "streamlit_app.py", "requirements.txt", ".env", "recipients.csv"]:
        (tmp_path / filename).write_text("placeholder", encoding="utf-8")
    return tmp_path

