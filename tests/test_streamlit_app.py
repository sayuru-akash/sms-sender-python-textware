from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

import streamlit_app


def test_load_recipients_preserves_string_columns(tmp_path, monkeypatch):
    csv_path = tmp_path / "recipients.csv"
    csv_path.write_text(
        "name,email,contact_number\nSayuru,test@example.com,0777123456\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    df = streamlit_app.load_recipients("recipients.csv")

    assert list(df.columns) == streamlit_app.REQUIRED_RECIPIENT_COLUMNS
    assert df.iloc[0]["contact_number"] == "0777123456"


def test_prepare_uploaded_recipients_cleans_invalid_rows_and_duplicates():
    df = pd.DataFrame(
        [
            {"name": "Alice Silva Perera", "email": "ALICE@example.com", "contact_number": "0777123456"},
            {"name": "", "email": "bad-email", "contact_number": "123"},
            {"name": "Dup User", "email": "dup@example.com", "contact_number": "94777123456"},
        ]
    )

    cleaned_df, invalid_df, duplicate_count = streamlit_app.prepare_uploaded_recipients(df)

    assert len(cleaned_df) == 1
    assert cleaned_df.iloc[0]["name"] == "Alice Silva"
    assert cleaned_df.iloc[0]["email"] == "alice@example.com"
    assert cleaned_df.iloc[0]["contact_number"] == "94777123456"
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
    assert at.selectbox[0].options == ["Import One (94770000001)", "Import Two (94770000002)"]


def test_app_add_recipient_to_imported_memory_source():
    at = AppTest.from_file(str(Path(streamlit_app.__file__)))
    at.session_state["imported_recipients"] = pd.DataFrame(
        [{"name": "Import One", "email": "one@example.com", "contact_number": "94770000001"}]
    )
    at.session_state["imported_label"] = "Imported (demo.csv)"
    at.session_state["selected_source"] = "__memory__"

    at.run()
    at.text_input[1].set_value("Added User")
    at.text_input[2].set_value("added@example.com")
    at.text_input[3].set_value("0771234568")
    at.button[0].click()
    at.run()

    imported_df = at.session_state["imported_recipients"]
    assert len(imported_df) == 2
    assert imported_df.iloc[-1]["name"] == "Added User"
    assert imported_df.iloc[-1]["contact_number"] == "94771234568"
