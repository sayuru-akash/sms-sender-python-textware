from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

import streamlit_app


def test_load_recipients_preserves_string_columns(tmp_path, monkeypatch):
    csv_path = tmp_path / "recipients.csv"
    csv_path.write_text(
        "contact_number\n0777123456\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    df = streamlit_app.load_recipients("recipients.csv")

    assert list(df.columns) == streamlit_app.RECIPIENT_COLUMNS
    assert df.iloc[0]["name"] == ""
    assert df.iloc[0]["email"] == ""
    assert df.iloc[0]["contact_number"] == "0777123456"


def test_get_available_csvs_includes_imported_source(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    streamlit_app.st.session_state.clear()
    streamlit_app.st.session_state["imported_recipients"] = pd.DataFrame(
        [{"name": "Import", "email": "import@example.com", "contact_number": "94770000001"}]
    )
    streamlit_app.st.session_state["imported_label"] = "Imported (demo.csv)"

    options = streamlit_app.get_available_csvs()

    assert ("Imported (demo.csv)", "__memory__") in options


def test_resolve_csv_path_uses_bundled_sample_when_local_file_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    resolved = streamlit_app.resolve_csv_path(streamlit_app.DEFAULT_SAMPLE_CSV)

    assert resolved == streamlit_app.BUNDLED_SAMPLE_CSV
    assert resolved.exists()


def test_get_current_recipients_falls_back_from_missing_memory_source(tmp_path, monkeypatch):
    sample_csv = tmp_path / "sample-recipients.csv"
    sample_csv.write_text(
        "name,email,contact_number\nSayuru,test@example.com,0777123456\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    streamlit_app.st.session_state.clear()
    streamlit_app.st.session_state["selected_source"] = "__memory__"
    streamlit_app.st.session_state["imported_recipients"] = None

    source, label, df = streamlit_app.get_current_recipients()

    assert source == "sample-recipients.csv"
    assert label == "Sample"
    assert len(df) == 1


def test_prepare_uploaded_recipients_cleans_invalid_rows_and_duplicates():
    df = pd.DataFrame(
        [
            {"name": "Alice Silva Perera", "email": "ALICE@example.com", "contact_number": "0777123456"},
            {"contact_number": "0777123457"},
            {"name": "", "email": "bad-email", "contact_number": "123"},
            {"name": "Dup User", "email": "dup@example.com", "contact_number": "94777123456"},
        ]
    )

    cleaned_df, invalid_df, duplicate_count = streamlit_app.prepare_uploaded_recipients(df)

    assert len(cleaned_df) == 2
    assert cleaned_df.iloc[0]["name"] == "Alice Silva"
    assert cleaned_df.iloc[0]["email"] == "alice@example.com"
    assert cleaned_df.iloc[0]["contact_number"] == "94777123456"
    assert cleaned_df.iloc[1]["name"] == ""
    assert cleaned_df.iloc[1]["email"] == ""
    assert cleaned_df.iloc[1]["contact_number"] == "94777123457"
    assert len(invalid_df) == 1
    assert duplicate_count == 1


def test_parse_env_file_and_mask_value(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "SMS_USERNAME=test-user\nSMS_PASSWORD=secretpass\nSMS_SOURCE=TESTSRC\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    values = streamlit_app.parse_env_file()

    assert values["SMS_USERNAME"] == "test-user"
    assert streamlit_app.mask_value("secretpass") == "sec*****ss"
    assert streamlit_app.mask_value("") == "Not set"


def test_load_reports_and_load_report_data(tmp_path, monkeypatch):
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    report_path = report_dir / "sms_report_1.json"
    report_path.write_text('{"total_sms": 1, "details": []}', encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    reports = streamlit_app.load_reports()
    payload = streamlit_app.load_report_data(report_path)

    assert reports == [Path("reports") / "sms_report_1.json"]
    assert payload["total_sms"] == 1


def test_recipients_summary_and_build_message_stats():
    invalid_df = pd.DataFrame([{"name": "OnlyName"}])
    summary = streamlit_app.recipients_summary(invalid_df)
    stats = streamlit_app.build_message_stats("Hello {name}")

    assert summary == {"rows": 1, "phones": 0, "emails": 0}
    assert stats["char_count"] == 12
    assert stats["sms_parts"] == 1
    assert stats["has_placeholder"] is True


def test_build_report_display_df_hides_full_message_body():
    details_df = pd.DataFrame(
        [
            {
                "iteration": 1,
                "status": "success",
                "contact_number": "94777123456",
                "message_preview": "Hello...",
                "message_body": "Hello full message body",
                "operation_id": "123",
            }
        ]
    )

    display_df = streamlit_app.build_report_display_df(details_df)

    assert "message_body" not in display_df.columns
    assert display_df.iloc[0]["message_preview"] == "Hello..."


def test_format_report_detail_label_prefers_name_and_iteration():
    label = streamlit_app.format_report_detail_label(
        {
            "iteration": 3,
            "name": "Alice",
            "contact_number": "94777123456",
            "status": "success",
        }
    )

    assert label == "#3 Alice (94777123456) [success]"


def test_ensure_session_state_initializes_draft_from_template(monkeypatch):
    streamlit_app.st.session_state.clear()
    monkeypatch.setattr(streamlit_app, "get_sms_message", lambda: "Template from file")

    streamlit_app.ensure_session_state()

    assert streamlit_app.st.session_state["draft_message"] == "Template from file"


def test_app_uses_imported_recipients_as_active_source():
    at = AppTest.from_file(str(Path(streamlit_app.__file__)))
    at.session_state["imported_recipients"] = pd.DataFrame(
        [
            {"name": "Import One", "email": "one@example.com", "contact_number": "94770000001"},
            {"name": "Import Two", "email": "two@example.com", "contact_number": "94770000002"},
        ]
    )
    at.session_state["imported_label"] = "Imported (demo.csv)"
    at.session_state["selected_source"] = "__memory__"

    at.run()

    assert at.session_state["csv_selector"] == "Imported (demo.csv)"
    assert at.metric[0].value == "Imported (demo.csv)"
    assert at.selectbox[0].options == ["Sample", "Imported (demo.csv)"]


def test_set_selected_source_updates_pending_source():
    streamlit_app.st.session_state.clear()

    streamlit_app.set_selected_source(streamlit_app.MEMORY_SOURCE)

    assert streamlit_app.st.session_state["selected_source"] == streamlit_app.MEMORY_SOURCE
    assert streamlit_app.st.session_state["pending_selected_source"] == streamlit_app.MEMORY_SOURCE


def test_app_uses_bundled_sample_when_no_local_csv_exists(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    at = AppTest.from_file(str(Path(streamlit_app.__file__)))
    at.run()
    assert at.session_state["csv_selector"] == "Sample"
    assert at.metric[0].value == "Sample"


def test_app_reports_missing_columns_for_selected_file(tmp_path, monkeypatch):
    bad_csv = tmp_path / "sample-recipients.csv"
    bad_csv.write_text("name,email\nOnly,missing@example.com\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    at = AppTest.from_file(str(Path(streamlit_app.__file__)))
    at.run()

    assert any("Missing column(s)" in error.value for error in at.error)
