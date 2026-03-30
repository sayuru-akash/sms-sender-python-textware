import io
import json
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import streamlit_app


class SessionState(dict):
    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError as exc:
            raise AttributeError(item) from exc

    def __setattr__(self, key, value):
        self[key] = value


class FakeContext:
    def __init__(self, owner):
        self.owner = owner

    def __enter__(self):
        return self.owner

    def __exit__(self, exc_type, exc, tb):
        return False


class FakePlaceholder(FakeContext):
    def container(self, border=False):
        return FakeContext(self.owner)


class FakeRerun(RuntimeError):
    pass


class FakeStreamlit:
    def __init__(
        self,
        *,
        selectbox_values=None,
        text_input_values=None,
        text_area_values=None,
        slider_values=None,
        checkbox_values=None,
        button_values=None,
        form_submit_values=None,
        uploaded_files=None,
        session_state=None,
    ):
        self.session_state = SessionState()
        if session_state:
            self.session_state.update(session_state)
        self.selectbox_values = selectbox_values or {}
        self.text_input_values = text_input_values or {}
        self.text_area_values = text_area_values or {}
        self.slider_values = slider_values or {}
        self.checkbox_values = checkbox_values or {}
        self.button_values = button_values or {}
        self.form_submit_values = form_submit_values or {}
        self.uploaded_files = uploaded_files or {}
        self.sidebar = FakeContext(self)

        self.markdowns = []
        self.captions = []
        self.metrics = []
        self.errors = []
        self.warnings = []
        self.infos = []
        self.successes = []
        self.json_payloads = []
        self.dataframes = []
        self.downloads = []
        self.codes = []
        self.progress_updates = []

    def _lookup(self, mapping, label, key, default):
        if key is not None and key in mapping:
            return mapping[key]
        if label in mapping:
            return mapping[label]
        return default

    def markdown(self, body, unsafe_allow_html=False):
        self.markdowns.append(body)

    def title(self, body):
        self.markdowns.append(body)

    def subheader(self, body):
        self.markdowns.append(body)

    def caption(self, body):
        self.captions.append(body)

    def info(self, body):
        self.infos.append(body)

    def warning(self, body):
        self.warnings.append(body)

    def error(self, body):
        self.errors.append(body)

    def success(self, body):
        self.successes.append(body)

    def json(self, payload):
        self.json_payloads.append(payload)

    def dataframe(self, df, **kwargs):
        self.dataframes.append(df.copy() if hasattr(df, "copy") else df)

    def download_button(self, label, data=None, file_name=None, mime=None, **kwargs):
        self.downloads.append(
            {"label": label, "data": data, "file_name": file_name, "mime": mime}
        )
        return False

    def metric(self, label, value, delta=None):
        self.metrics.append((label, value, delta))

    def divider(self):
        return None

    def columns(self, spec, gap=None):
        count = spec if isinstance(spec, int) else len(spec)
        return [FakeContext(self) for _ in range(count)]

    def container(self, border=False):
        return FakeContext(self)

    def form(self, key, clear_on_submit=False):
        return FakeContext(self)

    def expander(self, label, expanded=False):
        return FakeContext(self)

    def spinner(self, text):
        return FakeContext(self)

    def tabs(self, labels):
        return [FakeContext(self) for _ in labels]

    def empty(self):
        return FakePlaceholder(self)

    def text_input(self, label, value="", key=None, **kwargs):
        selected = self._lookup(self.text_input_values, label, key, value)
        if key is not None:
            self.session_state[key] = selected
        return selected

    def text_area(self, label, value="", key=None, **kwargs):
        selected = self._lookup(self.text_area_values, label, key, value)
        if key is not None:
            self.session_state[key] = selected
        return selected

    def selectbox(self, label, options, index=0, key=None, format_func=None, **kwargs):
        option_list = list(options)
        default = option_list[index] if option_list else None
        selected = self._lookup(self.selectbox_values, label, key, default)
        if key is not None:
            self.session_state[key] = selected
        return selected

    def slider(self, label, min_value, max_value, value=None, key=None, **kwargs):
        default = value
        if default is None and key is not None and key in self.session_state:
            default = self.session_state[key]
        if default is None:
            default = min_value
        selected = self._lookup(self.slider_values, label, key, default)
        if key is not None:
            self.session_state[key] = selected
        return selected

    def checkbox(self, label, value=False, key=None, **kwargs):
        selected = self._lookup(self.checkbox_values, label, key, value)
        if key is not None:
            self.session_state[key] = selected
        return selected

    def button(self, label, key=None, on_click=None, disabled=False, **kwargs):
        selected = self._lookup(self.button_values, label, key, False)
        pressed = bool(selected) and not disabled
        if pressed and on_click:
            on_click()
        return pressed

    def form_submit_button(self, label, **kwargs):
        return bool(self.form_submit_values.get(label, False))

    def file_uploader(self, label, **kwargs):
        return self.uploaded_files.get(label)

    def code(self, body, language=None):
        self.codes.append(body)

    def progress(self, value, text=None):
        self.progress_updates.append((value, text))

    def rerun(self):
        raise FakeRerun()

    def segmented_control(self, label, options, default=None, key=None, **kwargs):
        selected = self._lookup(
            self.selectbox_values, label, key, default if default is not None else options[0]
        )
        if key is not None:
            self.session_state[key] = selected
        return selected


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


def test_get_report_message_content_prefers_full_message_body_and_falls_back_to_preview():
    full_message = streamlit_app.get_report_message_content(
        {"message_body": "Full body", "message_preview": "Preview"}
    )
    legacy_message = streamlit_app.get_report_message_content(
        {"message_preview": "Preview only"}
    )

    assert full_message["content"] == "Full body"
    assert full_message["is_full_message"] is True
    assert legacy_message["content"] == "Preview only"
    assert legacy_message["is_full_message"] is False
    assert "full-message capture" in legacy_message["note"]


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
    assert "Sample" in at.selectbox[0].options
    assert "Imported (demo.csv)" in at.selectbox[0].options


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


def test_render_dashboard_and_settings_cover_summary_views(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "app.log").write_text("ok", encoding="utf-8")
    fake_st = FakeStreamlit(session_state={"draft_message": "Hello"})
    monkeypatch.setattr(streamlit_app, "st", fake_st)

    recipients_df = pd.DataFrame(
        [{"name": "Alice", "email": "alice@example.com", "contact_number": "94777123456"}]
    )
    env_vars = {
        "SMS_USERNAME": "user",
        "SMS_PASSWORD": "secret",
        "SMS_SOURCE": "SRC",
        "SMS_API_URL": "https://example.com",
    }
    reports = [tmp_path / "reports" / "report.json"]

    streamlit_app.apply_theme()
    streamlit_app.show_status_chips("Sample", recipients_df, env_vars, 1)
    streamlit_app.render_header("Sample", recipients_df, env_vars, reports)
    streamlit_app.render_dashboard_tab("Sample", recipients_df, env_vars, reports)
    streamlit_app.render_settings_tab("Sample", env_vars, reports)

    assert any(label == "Active list" for label, _, _ in fake_st.metrics)
    assert any(label == "Environment" for label, _, _ in fake_st.metrics)
    assert any("Latest report" in caption for caption in fake_st.captions)


def test_render_reports_tab_shows_filtered_downloadable_details(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    report_path = reports_dir / "sms_report_demo.json"
    report_path.write_text(
        json.dumps(
            {
                "total_sms": 2,
                "accepted_by_gateway": 1,
                "errors": 1,
                "skipped": 0,
                "started_at": "2026-03-30T12:00:00",
                "finished_at": "2026-03-30T12:05:00",
                "duration_seconds": 300,
                "context": {"channel": "streamlit", "source_label": "Sample"},
                "details": [
                    {
                        "iteration": 1,
                        "status": "success",
                        "contact_number": "94777123456",
                        "name": "Alice",
                        "email": "alice@example.com",
                        "message_body": "Hello Alice",
                        "message_preview": "Hello Alice",
                        "operation_id": "op-1",
                    },
                    {
                        "iteration": 2,
                        "status": "error",
                        "contact_number": "94777123457",
                        "name": "Bob",
                        "message_preview": "Hello Bob",
                        "error": "Gateway error",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    fake_st = FakeStreamlit(selectbox_values={"Status": "success"})
    monkeypatch.setattr(streamlit_app, "st", fake_st)

    streamlit_app.render_reports_tab([report_path])

    assert any(label == "Accepted by gateway" for label, _, _ in fake_st.metrics)
    assert any(download["label"] == "Download CSV" for download in fake_st.downloads)
    assert any(download["label"] == "Download JSON" for download in fake_st.downloads)
    assert any(payload.get("channel") == "streamlit" for payload in fake_st.json_payloads)
    assert fake_st.codes == ["Hello Alice"]


def test_render_recipients_tab_saves_manual_recipient_to_uploaded_csv(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    fake_st = FakeStreamlit(
        text_input_values={
            "Search": "",
            "Name": "Alice Silva Perera",
            "Email": "ALICE@example.com",
            "Phone": "0777123456",
        },
        form_submit_values={"Save": True},
    )
    monkeypatch.setattr(streamlit_app, "st", fake_st)

    with pytest.raises(FakeRerun):
        streamlit_app.render_recipients_tab(
            streamlit_app.DEFAULT_UPLOAD_CSV,
            "Uploaded",
            pd.DataFrame(columns=streamlit_app.RECIPIENT_COLUMNS),
        )

    saved_df = pd.read_csv(tmp_path / streamlit_app.DEFAULT_UPLOAD_CSV, dtype=str).fillna("")
    assert saved_df.to_dict(orient="records") == [
        {
            "name": "Alice Silva",
            "email": "alice@example.com",
            "contact_number": "94777123456",
        }
    ]
    assert fake_st.session_state["selected_source"] == streamlit_app.DEFAULT_UPLOAD_CSV


def test_render_recipients_tab_adds_manual_recipient_to_memory_list(monkeypatch):
    imported_df = pd.DataFrame(
        [{"name": "Existing", "email": "", "contact_number": "94777123456"}]
    )
    fake_st = FakeStreamlit(
        text_input_values={
            "Search": "",
            "Name": "New User",
            "Email": "",
            "Phone": "0777123457",
        },
        form_submit_values={"Save": True},
        session_state={"imported_recipients": imported_df.copy()},
    )
    monkeypatch.setattr(streamlit_app, "st", fake_st)

    with pytest.raises(FakeRerun):
        streamlit_app.render_recipients_tab(
            streamlit_app.MEMORY_SOURCE,
            "Imported (demo.csv)",
            imported_df,
        )

    updated_df = fake_st.session_state["imported_recipients"]
    assert len(updated_df) == 2
    assert updated_df.iloc[1]["contact_number"] == "94777123457"
    assert fake_st.session_state["selected_source"] == streamlit_app.MEMORY_SOURCE


def test_render_recipients_tab_uses_uploaded_csv_without_saving(monkeypatch):
    uploaded_csv = io.StringIO(
        "name,email,contact_number\nAlice,alice@example.com,0777123456\nBob,,0777123457\n"
    )
    uploaded_csv.name = "demo.csv"
    fake_st = FakeStreamlit(
        text_input_values={"Search": ""},
        uploaded_files={"Choose CSV": uploaded_csv},
        button_values={"Use now": True},
    )
    monkeypatch.setattr(streamlit_app, "st", fake_st)

    with pytest.raises(FakeRerun):
        streamlit_app.render_recipients_tab(
            streamlit_app.DEFAULT_SAMPLE_CSV,
            "Sample",
            pd.DataFrame(columns=streamlit_app.RECIPIENT_COLUMNS),
        )

    imported_df = fake_st.session_state["imported_recipients"]
    assert len(imported_df) == 2
    assert fake_st.session_state["imported_label"] == "Imported (demo.csv)"
    assert fake_st.session_state["selected_source"] == streamlit_app.MEMORY_SOURCE


def test_render_campaign_tab_sends_test_sms(monkeypatch):
    recipients_df = pd.DataFrame(
        [{"name": "Alice", "email": "alice@example.com", "contact_number": "94777123456"}]
    )
    fake_st = FakeStreamlit(
        text_area_values={"draft_message": "Hello {name}"},
        button_values={"Send test SMS": True},
        session_state={"draft_message": "Hello {name}", "campaign_rate_limit": 2},
    )
    monkeypatch.setattr(streamlit_app, "st", fake_st)

    class FakeSender:
        def __init__(self, progress_callback=None):
            self.progress_callback = progress_callback

        def send_sms(self, phone_number, message, name, email):
            assert phone_number == "94777123456"
            assert message == "Hello Alice"
            return {"status": "success", "operation_id": "op-123"}

    monkeypatch.setattr(streamlit_app, "SMSSender", FakeSender)

    streamlit_app.render_campaign_tab("Sample", "Sample", recipients_df)

    assert "Gateway accepted the test SMS request." in fake_st.successes
    assert any("Delivery to the handset" in message for message in fake_st.infos)
    assert fake_st.json_payloads[0]["operation_id"] == "op-123"


def test_render_campaign_tab_starts_bulk_campaign_for_memory_source(monkeypatch):
    recipients_df = pd.DataFrame(
        [
            {"name": "Alice", "email": "alice@example.com", "contact_number": "94777123456"},
            {"name": "Bob", "email": "", "contact_number": "94777123457"},
        ]
    )
    fake_st = FakeStreamlit(
        text_area_values={"draft_message": "Hello {name}"},
        checkbox_values={"I reviewed the message and recipient list.": True},
        button_values={"Start campaign": True},
        session_state={"draft_message": "Hello {name}", "campaign_rate_limit": 3},
    )
    monkeypatch.setattr(streamlit_app, "st", fake_st)

    class FakeSender:
        last_instance = None

        def __init__(self, progress_callback=None):
            self.progress_callback = progress_callback
            self.rate_limit_delay = None
            self.context = None
            FakeSender.last_instance = self

        def set_report_context(self, **kwargs):
            self.context = kwargs

        def send_bulk_sms_dataframe(self, df, message):
            self.progress_callback(
                {
                    "current": 2,
                    "total": 2,
                    "successful": 2,
                    "failed": 0,
                    "errors": 0,
                    "skipped": 0,
                    "status": "sent",
                    "recipient_info": "Bob (94777123457)",
                }
            )
            return {"total": 2, "successful": 2, "errors": 0, "skipped": 0}

        def save_report(self):
            return "reports/sms_report_demo.json"

    monkeypatch.setattr(streamlit_app, "SMSSender", FakeSender)

    streamlit_app.render_campaign_tab(streamlit_app.MEMORY_SOURCE, "Imported", recipients_df)

    assert any("Campaign complete" in message for message in fake_st.successes)
    assert any("Gateway acceptance does not guarantee handset delivery" in msg for msg in fake_st.infos)
    assert any(label == "Total" and value == 2 for label, value, _ in fake_st.metrics)
    assert FakeSender.last_instance.context["source_type"] == "memory"
    assert FakeSender.last_instance.rate_limit_delay == 3
