from pathlib import Path

import pandas as pd

import clean_recipient_batches as cleaner


def test_clean_recipient_dataframe_keeps_only_system_columns_and_cleans_rows():
    raw_df = pd.DataFrame(
        [
            {
                "Phone Number": "0777123456",
                "Name": "Alice Silva Perera",
                "Email": "ALICE@example.com",
                "Payment Details": "FALSE",
                "Registered": "FALSE",
            },
            {
                "Phone Number": "777123457",
                "Name": "",
                "Email": "bad-email",
                "Payment Details": "FALSE",
                "Registered": "FALSE",
            },
            {
                "Phone Number": "777123458",
                "Name": "Already Paid",
                "Payment Details": "TRUE",
                "Registered": "FALSE",
            },
            {
                "Phone Number": "777123459",
                "Name": "Already Registered",
                "Payment Details": "FALSE",
                "Registered": "TRUE",
            },
            {"Phone Number": "12345", "Name": "Invalid"},
            {"Phone Number": "0777123456", "Name": "Duplicate"},
        ]
    )

    cleaned_df, stats = cleaner.clean_recipient_dataframe(raw_df)

    assert list(cleaned_df.columns) == cleaner.OUTPUT_COLUMNS
    assert cleaned_df.to_dict(orient="records") == [
        {
            "contact_number": "94777123456",
            "name": "Alice Silva",
            "email": "alice@example.com",
        },
        {
            "contact_number": "94777123457",
            "name": "",
            "email": "",
        },
    ]
    assert stats["input_rows"] == 6
    assert stats["output_rows"] == 2
    assert stats["removed_paid_or_registered"] == 2
    assert stats["removed_missing_or_invalid_phone"] == 1
    assert stats["removed_duplicate_phone"] == 1
    assert stats["blanked_invalid_email"] == 1


def test_process_input_file_writes_cleaned_output(tmp_path):
    input_path = tmp_path / "batch.csv"
    output_dir = tmp_path / "output"
    input_path.write_text(
        "Phone Number,Name\n0777123456,Alice Silva\n",
        encoding="utf-8",
    )

    result = cleaner.process_input_file(input_path, output_dir)

    output_path = Path(result["output_path"])
    assert result["status"] == "processed"
    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8-sig").startswith("contact_number,name,email")


def test_process_input_file_skips_existing_output_without_force(tmp_path):
    input_path = tmp_path / "batch.csv"
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    output_path = cleaner.cleaned_output_path(input_path, output_dir)
    input_path.write_text("Phone Number\n0777123456\n", encoding="utf-8")
    output_path.write_text("already done", encoding="utf-8")

    result = cleaner.process_input_file(input_path, output_dir, force=False)

    assert result["status"] == "skipped_existing"
    assert output_path.read_text(encoding="utf-8") == "already done"


def test_process_input_file_skips_already_cleaned_inputs_without_force(tmp_path):
    input_path = tmp_path / "batch_cleaned.csv"
    output_dir = tmp_path / "output"
    input_path.write_text("Phone Number\n0777123456\n", encoding="utf-8")

    result = cleaner.process_input_file(input_path, output_dir, force=False)

    assert result["status"] == "skipped_already_cleaned_input"


def test_process_pending_inputs_ignores_cleaned_inputs_and_processes_pending(tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()
    (input_dir / "batch.csv").write_text("Phone Number\n0777123456\n", encoding="utf-8")
    (input_dir / "batch_cleaned.csv").write_text("Phone Number\n0777123456\n", encoding="utf-8")

    results = cleaner.process_pending_inputs(input_dir=input_dir, output_dir=output_dir)

    assert len(results) == 1
    assert results[0]["status"] == "processed"
    assert Path(results[0]["output_path"]).name == "batch_cleaned.csv"


def test_process_pending_inputs_returns_error_result_without_stopping_batch(tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()
    (input_dir / "good.csv").write_text("Phone Number\n0777123456\n", encoding="utf-8")
    (input_dir / "bad.csv").write_text("Name\nAlice\n", encoding="utf-8")

    results = cleaner.process_pending_inputs(input_dir=input_dir, output_dir=output_dir)

    assert len(results) == 2
    assert [result["status"] for result in results] == ["error", "processed"]
    assert "phone number column" in results[0]["error"].lower()
    assert Path(results[1]["output_path"]).name == "good_cleaned.csv"
