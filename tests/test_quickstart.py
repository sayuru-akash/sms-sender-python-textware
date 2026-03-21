import subprocess

import quickstart


def test_print_header_outputs_banner(capsys):
    quickstart.print_header()
    output = capsys.readouterr().out
    assert "SMS CAMPAIGN MANAGER - QUICK START" in output


def test_check_setup_returns_true_when_required_files_exist(project_files, monkeypatch, capsys):
    monkeypatch.chdir(project_files)
    assert quickstart.check_setup() is True
    assert "✓ .env file" in capsys.readouterr().out


def test_check_setup_returns_false_when_files_are_missing(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert quickstart.check_setup() is False
    assert "✗ .env file" in capsys.readouterr().out


def test_show_menu_returns_input(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _prompt: "4")
    assert quickstart.show_menu() == "4"


def test_run_test_invokes_main_test(monkeypatch):
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda args: calls.append(args))
    quickstart.run_test()
    assert calls == [[quickstart.sys.executable, "main.py", "--test"]]


def test_run_bulk_does_not_invoke_subprocess_when_cancelled(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")
    monkeypatch.setattr(subprocess, "run", lambda args: calls.append(args))
    quickstart.run_bulk()
    assert calls == []
    assert "Cancelled" in capsys.readouterr().out


def test_run_bulk_invokes_subprocess_on_confirmation(monkeypatch):
    calls = []
    monkeypatch.setattr("builtins.input", lambda _prompt: "y")
    monkeypatch.setattr(subprocess, "run", lambda args: calls.append(args))
    quickstart.run_bulk()
    assert calls == [[quickstart.sys.executable, "main.py", "--bulk"]]


def test_run_dashboard_invokes_streamlit(monkeypatch):
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda args: calls.append(args))
    quickstart.run_dashboard()
    assert calls == [[quickstart.sys.executable, "main.py", "--streamlit"]]


def test_view_reports_lists_recent_reports(tmp_path, monkeypatch, capsys):
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    (report_dir / "sms_report_1.json").write_text("{}", encoding="utf-8")
    (report_dir / "sms_report_2.json").write_text("{}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    quickstart.view_reports()
    output = capsys.readouterr().out
    assert "Recent reports" in output
    assert "sms_report_1.json" in output or "sms_report_2.json" in output


def test_view_reports_handles_missing_directory(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    quickstart.view_reports()
    assert "No reports directory found" in capsys.readouterr().out


def test_view_reports_handles_empty_directory(tmp_path, monkeypatch, capsys):
    (tmp_path / "reports").mkdir()
    monkeypatch.chdir(tmp_path)
    quickstart.view_reports()
    assert "No reports found" in capsys.readouterr().out


def test_check_status_reports_available_modules(capsys):
    quickstart.check_status()
    output = capsys.readouterr().out
    assert "SYSTEM STATUS" in output
    assert "Python Environment" in output


def test_view_docs_prints_reference(capsys):
    quickstart.view_docs()
    output = capsys.readouterr().out
    assert "QUICK REFERENCE" in output
    assert "python main.py --streamlit" in output


def test_main_returns_early_when_setup_is_incomplete(monkeypatch, capsys):
    monkeypatch.setattr(quickstart, "check_setup", lambda: False)
    quickstart.main()
    assert "Some files are missing" in capsys.readouterr().out


def test_main_handles_invalid_choice_then_exit(monkeypatch, capsys):
    monkeypatch.setattr(quickstart, "check_setup", lambda: True)
    choices = iter(["9", "7"])
    monkeypatch.setattr(quickstart, "show_menu", lambda: next(choices))
    quickstart.main()
    output = capsys.readouterr().out
    assert "Invalid choice" in output
    assert "Goodbye" in output
