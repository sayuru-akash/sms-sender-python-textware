# GitHub Copilot Instructions

## Project overview

This repository is a **Python SMS campaign application** built on top of the Text-Ware SMS API. It supports a web dashboard (Streamlit), a CLI, batch recipient cleaning, and automated reporting.

### Key files

| File | Role |
|------|------|
| `streamlit_app.py` | Primary Streamlit web UI – recipients, campaigns, reports, settings |
| `sms_sender.py` | Core SMS engine – sending, validation, retries, reporting, template loading |
| `main.py` | CLI entry point (`--test`, `--bulk`, `--streamlit`) |
| `quickstart.py` | Interactive menu wrapper around `main.py` entry points |
| `clean_recipient_batches.py` | Batch cleaner for raw CSV exports in `resources/input/` |
| `resources/message_template.txt` | Default SMS template used by the CLI and new Streamlit sessions |
| `resources/sample-recipients.csv` | Bundled sample recipient list for quick testing |
| `resources/input/` | Drop zone for raw CSV files to be cleaned |
| `resources/output/` | Cleaned CSV output files produced by the batch cleaner |
| `recipients.csv` | Optional saved recipient list (created/updated by user or UI) |

---

## Environment and dependencies

- **Python 3.10+**
- Dependencies: `requests`, `python-dotenv`, `pandas`, `streamlit`, `watchdog`, `pytest`, `pytest-cov`
- Install: `pip install -r requirements.txt`
- Credentials are stored in `.env` (never committed). Use `.env.sample` as the template.

Required `.env` keys (see `.env.sample`):

```
TEXTWARE_API_KEY=...
TEXTWARE_SENDER_ID=...
```

---

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Common commands

```bash
# Web dashboard (recommended)
python main.py --streamlit

# CLI – test send
python main.py --test

# CLI – bulk send
python main.py --bulk

# Batch recipient cleaner
python clean_recipient_batches.py
python clean_recipient_batches.py --file "resources/input/your-file.csv"

# Run tests
python -m pytest
python -m pytest --cov=. --cov-report=term-missing

# Syntax check
python -m py_compile sms_sender.py streamlit_app.py main.py quickstart.py
```

---

## Architecture and design rules

### SMS sending

- All phone numbers are normalized to Sri Lankan format `94XXXXXXXXX`.
- Validation and normalization helpers live in `sms_sender.py` and should not be duplicated in the UI.
- API calls use POST first with a GET fallback where that pattern is already in place.
- Retries: 3 attempts per message with configurable rate limiting between sends.
- Reports are written to disk as JSON; logs are written to disk with timestamps.

### Recipients and CSV

- The only required column is `contact_number`; `name` and `email` are optional.
- Uploaded CSV files can be used in memory without being saved to `recipients.csv`.
- `recipients.csv` at the project root is optional and must never be treated as mandatory.
- During batch cleaning, only `contact_number`, `name`, and `email` are kept in output.
- Rows with a truthy `Payment Details` or `Registered` column are excluded from cleaned output.
- Rows without a valid Sri Lankan mobile number are removed during cleaning.
- The batch cleaner skips already-processed files unless explicitly forced to regenerate.

### Message templates

- `resources/message_template.txt` is the tracked default template.
- A root-level `message_template.txt` can serve as a local override but is not the canonical location.
- Streamlit message edits live in session state; they do not modify the template file unless the user does so explicitly.
- The `{name}` placeholder is replaced with up to the first two words of the recipient's name.

### Streamlit UI

- Use native Streamlit patterns; avoid heavy custom CSS or broad CSS selectors.
- Treat message editing as runtime state, not file generation.
- After any campaign-editor change, verify: draft editing works, test send uses the draft, bulk send uses the draft, resetting reloads the default template.
- After any recipient-flow change, verify: sample recipients work, contact-number-only lists work, in-memory imports work, `recipients.csv` is not required.

---

## Testing

Tests live in the `tests/` directory and use `pytest`. Configuration is in `pytest.ini`.

Recommended validation order before finishing a change:

1. `python -m py_compile <touched files>` – syntax only
2. `pytest tests/test_<affected_module>.py` – targeted tests
3. `python -m pytest` – full suite for cross-cutting changes
4. `python -m pytest --cov=. --cov-report=term-missing` – coverage for core changes

Always update tests when behavior changes.

---

## Security

- Never commit `.env`.
- Never hardcode API keys, sender IDs, or any credentials anywhere in the codebase.
- Do not expose credentials in logs, reports, tests, or documentation.
- Do not delete logs, reports, or user CSV files unless explicitly instructed.

---

## Documentation

Update `README.md` whenever you change:

- startup or run commands
- recipient import/save behavior
- batch cleaning commands or folder conventions
- message template behavior
- test commands
- required files or project structure

---

## Code style

- Keep changes minimal and targeted; prefer fixing the root cause over adding layers.
- Do not add new packages unless they materially improve the project.
- Keep `resources/input/` and `resources/output/` folder placeholders tracked via `.gitkeep`; actual CSV contents are gitignored.
- Keep Sri Lanka phone normalization behavior consistent unless broader support is explicitly requested.
