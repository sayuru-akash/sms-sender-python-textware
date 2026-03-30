#!/usr/bin/env python3
"""Clean recipient CSV batches from resources/input into resources/output."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

from sms_sender import is_valid_email, limit_name_to_two_words, normalize_sl_phone_number

APP_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT_DIR = APP_DIR / "resources" / "input"
DEFAULT_OUTPUT_DIR = APP_DIR / "resources" / "output"
OUTPUT_COLUMNS = ["contact_number", "name", "email"]
TRUTHY_VALUES = {"1", "true", "yes", "y", "paid", "registered"}

FIELD_ALIASES = {
    "contact_number": {
        "contact number",
        "contact_number",
        "mobile",
        "mobile number",
        "mobile_number",
        "number",
        "phone",
        "phone number",
        "phone_number",
        "telephone",
        "telephone number",
        "whatsapp",
        "whatsapp number",
        "whatsapp_number",
    },
    "name": {
        "candidate name",
        "full name",
        "full_name",
        "name",
        "student name",
        "student_name",
    },
    "email": {
        "e-mail",
        "email",
        "email address",
        "email_address",
        "mail",
    },
    "payment_details": {
        "payment",
        "payment detail",
        "payment details",
        "payment_details",
    },
    "registered": {
        "registered",
        "registration",
        "is registered",
        "is_registered",
    },
}


def normalize_header(header: str) -> str:
    """Normalize CSV header text for fuzzy matching."""
    return re.sub(r"[^a-z0-9]+", " ", str(header).strip().lower()).strip()


def find_matching_column(columns, field_name: str) -> str | None:
    """Find the first source column that matches a supported field alias."""
    aliases = FIELD_ALIASES[field_name]
    for column in columns:
        if normalize_header(column) in aliases:
            return column
    return None


def cleaned_output_path(input_path: Path, output_dir: Path) -> Path:
    """Return the canonical cleaned CSV path for an input file."""
    return output_dir / f"{input_path.stem}_cleaned.csv"


def is_cleaned_input_file(input_path: Path) -> bool:
    """Return True when the input filename already looks like a cleaned export."""
    return input_path.stem.endswith("_cleaned")


def is_truthy_cell(value) -> bool:
    """Return True for spreadsheet values that should count as an enabled boolean."""
    if value is None:
        return False
    return str(value).strip().lower() in TRUTHY_VALUES


def clean_recipient_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Clean raw recipient data into the system-ready output schema."""
    source_df = df.fillna("")
    phone_column = find_matching_column(source_df.columns, "contact_number")
    if not phone_column:
        raise ValueError("Could not find a phone number column in the CSV.")

    name_column = find_matching_column(source_df.columns, "name")
    email_column = find_matching_column(source_df.columns, "email")
    payment_column = find_matching_column(source_df.columns, "payment_details")
    registered_column = find_matching_column(source_df.columns, "registered")

    cleaned_rows = []
    seen_numbers = set()
    stats = {
        "input_rows": len(source_df),
        "output_rows": 0,
        "removed_paid_or_registered": 0,
        "removed_missing_or_invalid_phone": 0,
        "removed_duplicate_phone": 0,
        "blanked_invalid_email": 0,
    }

    for _, row in source_df.iterrows():
        if (
            payment_column
            and is_truthy_cell(row.get(payment_column, ""))
        ) or (
            registered_column
            and is_truthy_cell(row.get(registered_column, ""))
        ):
            stats["removed_paid_or_registered"] += 1
            continue

        raw_phone = str(row.get(phone_column, "")).strip()
        normalized_phone = normalize_sl_phone_number(raw_phone)

        if not normalized_phone:
            stats["removed_missing_or_invalid_phone"] += 1
            continue

        if normalized_phone in seen_numbers:
            stats["removed_duplicate_phone"] += 1
            continue

        seen_numbers.add(normalized_phone)

        cleaned_name = ""
        if name_column:
            cleaned_name = limit_name_to_two_words(str(row.get(name_column, "")).strip())

        cleaned_email = ""
        if email_column:
            candidate_email = str(row.get(email_column, "")).strip().lower()
            if candidate_email:
                if is_valid_email(candidate_email):
                    cleaned_email = candidate_email
                else:
                    stats["blanked_invalid_email"] += 1

        cleaned_rows.append(
            {
                "contact_number": normalized_phone,
                "name": cleaned_name,
                "email": cleaned_email,
            }
        )

    cleaned_df = pd.DataFrame(cleaned_rows, columns=OUTPUT_COLUMNS)
    stats["output_rows"] = len(cleaned_df)
    return cleaned_df, stats


def process_input_file(input_path: Path, output_dir: Path, force: bool = False) -> dict:
    """Clean one input CSV and write its cleaned output file."""
    input_path = Path(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        return {
            "input_path": str(input_path),
            "status": "error",
            "error": "Input file does not exist.",
        }

    if input_path.suffix.lower() != ".csv":
        return {
            "input_path": str(input_path),
            "status": "error",
            "error": "Input file must be a .csv file.",
        }

    if is_cleaned_input_file(input_path) and not force:
        return {
            "input_path": str(input_path),
            "status": "skipped_already_cleaned_input",
        }

    output_path = cleaned_output_path(input_path, output_dir)

    if output_path.exists() and not force:
        return {
            "input_path": str(input_path),
            "output_path": str(output_path),
            "status": "skipped_existing",
        }

    try:
        raw_df = pd.read_csv(input_path, dtype=str, encoding="utf-8-sig")
        cleaned_df, stats = clean_recipient_dataframe(raw_df)
        cleaned_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    except Exception as exc:
        return {
            "input_path": str(input_path),
            "output_path": str(output_path),
            "status": "error",
            "error": str(exc),
        }

    return {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "status": "processed",
        **stats,
    }


def process_pending_inputs(
    input_dir: Path = DEFAULT_INPUT_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    force: bool = False,
) -> list[dict]:
    """Process all pending CSVs in the input directory."""
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for input_path in sorted(input_dir.glob("*.csv")):
        if is_cleaned_input_file(input_path):
            continue
        results.append(process_input_file(input_path, output_dir, force=force))
    return results


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(
        description="Clean recipient CSV files into system-ready Sri Lankan contact lists."
    )
    parser.add_argument(
        "--file",
        help="Process one specific CSV file. Defaults to scanning resources/input for pending CSVs.",
    )
    parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_INPUT_DIR),
        help="Directory to scan for pending CSVs when --file is not provided.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where cleaned CSV outputs should be written.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild outputs even if a cleaned file already exists.",
    )
    return parser


def main() -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()

    if args.file:
        input_path = Path(args.file).expanduser().resolve()
        result = process_input_file(input_path, output_dir, force=args.force)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result.get("status") != "error" else 1

    input_dir = Path(args.input_dir).expanduser().resolve()
    results = process_pending_inputs(input_dir=input_dir, output_dir=output_dir, force=args.force)
    if not results:
        print(
            json.dumps(
                {
                    "status": "no_pending_files",
                    "input_dir": str(input_dir),
                    "output_dir": str(output_dir),
                },
                ensure_ascii=False,
            )
        )
        return 0

    exit_code = 0
    for result in results:
        if result.get("status") == "error":
            exit_code = 1
        print(json.dumps(result, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
