import subprocess

import pytest

import main


def test_run_test_campaign_success(monkeypatch, capsys):
    class FakeSender:
        def test_api_connection(self):
            return {
                "status": "success",
                "phone": "94777123456",
                "timestamp": "2026-03-22T00:00:00",
                "response": "ok",
                "status_code": 200,
                "method": "GET",
                "api_format": 2,
            }

        def save_report(self):
            return "reports/test.json"

    monkeypatch.setattr(main, "SMSSender", FakeSender)
    assert main.run_test_campaign() is True
    captured = capsys.readouterr()
    assert "TEST RESULT" in captured.out
    assert "Method Used: GET" in captured.out
    assert "Parameter Format: 2" in captured.out
    assert "Report saved" in captured.out


def test_run_test_campaign_returns_false_on_exception(monkeypatch, capsys):
    class BrokenSender:
        def __init__(self):
            raise RuntimeError("boom")

    monkeypatch.setattr(main, "SMSSender", BrokenSender)
    assert main.run_test_campaign() is False
    assert "Test failed" in capsys.readouterr().out


def test_run_test_campaign_returns_false_for_error_result(monkeypatch, capsys):
    class FakeSender:
        def test_api_connection(self):
            return {
                "status": "error",
                "phone": "94777123456",
                "timestamp": "2026-03-22T00:00:00",
                "error": "bad request",
            }

        def save_report(self):
            return "reports/test.json"

    monkeypatch.setattr(main, "SMSSender", FakeSender)
    assert main.run_test_campaign() is False
    assert "bad request" in capsys.readouterr().out


def test_run_bulk_campaign_returns_false_when_file_missing(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main.run_bulk_campaign() is False
    assert "Recipients file not found" in capsys.readouterr().out


def test_run_bulk_campaign_success(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "recipients.csv").write_text(
        "name,email,contact_number\nAlice,alice@example.com,0777123456\n",
        encoding="utf-8",
    )

    class FakeSender:
        def send_bulk_sms(self, recipients_file, message):
            assert recipients_file == "recipients.csv"
            assert message == "message"
            return {"total": 1, "successful": 1, "failed": 0, "details": []}

        def save_report(self):
            return "reports/test.json"

    monkeypatch.setattr(main, "SMSSender", FakeSender)
    monkeypatch.setattr(main, "get_sms_message", lambda: "message")

    assert main.run_bulk_campaign() is True
    assert "Campaign completed" in capsys.readouterr().out


def test_run_bulk_campaign_returns_false_on_exception(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "recipients.csv").write_text("name,email,contact_number\n", encoding="utf-8")

    class FakeSender:
        def send_bulk_sms(self, recipients_file, message):
            raise RuntimeError("send failed")

    monkeypatch.setattr(main, "SMSSender", FakeSender)
    monkeypatch.setattr(main, "get_sms_message", lambda: "message")

    assert main.run_bulk_campaign() is False
    assert "Campaign failed: send failed" in capsys.readouterr().out


def test_main_without_args_prints_help(monkeypatch, capsys):
    monkeypatch.setattr(main.sys, "argv", ["main.py"])
    main.main()
    output = capsys.readouterr().out
    assert "SMS Campaign Sender" in output
    assert "Use --test" in output


def test_main_test_flag_exits_zero(monkeypatch):
    monkeypatch.setattr(main.sys, "argv", ["main.py", "--test"])
    monkeypatch.setattr(main, "run_test_campaign", lambda: True)
    with pytest.raises(SystemExit) as exc:
        main.main()
    assert exc.value.code == 0


def test_main_bulk_flag_exits_one_when_campaign_fails(monkeypatch):
    monkeypatch.setattr(main.sys, "argv", ["main.py", "--bulk"])
    monkeypatch.setattr(main, "run_bulk_campaign", lambda: False)
    with pytest.raises(SystemExit) as exc:
        main.main()
    assert exc.value.code == 1


def test_main_streamlit_runs_module(monkeypatch, capsys):
    monkeypatch.setattr(main.sys, "argv", ["main.py", "--streamlit"])
    calls = []

    def fake_run(args, check):
        calls.append((args, check))

    monkeypatch.setattr(subprocess, "run", fake_run)
    main.main()
    assert calls == [([main.sys.executable, "-m", "streamlit", "run", "streamlit_app.py"], True)]
    assert "Launching Streamlit dashboard" in capsys.readouterr().out


def test_main_streamlit_exits_with_subprocess_error(monkeypatch, capsys):
    monkeypatch.setattr(main.sys, "argv", ["main.py", "--streamlit"])

    def fake_run(*_args, **_kwargs):
        raise subprocess.CalledProcessError(returncode=3, cmd=["streamlit"])

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(SystemExit) as exc:
        main.main()

    assert exc.value.code == 3
    assert "failed to start" in capsys.readouterr().out.lower()


def test_main_streamlit_handles_keyboard_interrupt(monkeypatch, capsys):
    monkeypatch.setattr(main.sys, "argv", ["main.py", "--streamlit"])

    def fake_run(*_args, **_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(subprocess, "run", fake_run)
    main.main()
    assert "dashboard stopped" in capsys.readouterr().out.lower()
