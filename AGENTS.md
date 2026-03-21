# AGENTS.md

Instructions for AI coding agents working in this repository. This file is intentionally plain Markdown so it can be used across Codex, Cursor, Claude Code, Gemini CLI, Aider, Copilot, and similar tools.

## Project overview

This repository is a Python SMS campaign application for the Text-Ware SMS API.

Main surfaces:

- `streamlit_app.py`: primary UI for recipients, campaigns, reports, and settings
- `sms_sender.py`: core SMS sending logic, validation, retries, reports, and default message loading
- `main.py`: CLI entry point for test send, bulk send, and Streamlit launch
- `quickstart.py`: interactive menu wrapper around the main entry points
- `resources/message_template.txt`: bundled default SMS template used by the CLI and by new Streamlit sessions
- `resources/sample-recipients.csv`: bundled sample list for quick end-to-end checks
- `recipients.csv`: optional saved recipient list created or updated by the user or UI

## Working principles

- Keep changes pragmatic and minimal. Prefer fixing the underlying issue over adding layers.
- Do not hardcode credentials, API secrets, or machine-specific secrets.
- Do not rewrite user data files unless the task explicitly calls for persistence.
- Preserve the current product behavior where:
  - `resources/message_template.txt` defines the bundled default SMS template
  - a root-level `message_template.txt` may exist as a local override, but it is not the standard tracked location
  - Streamlit message edits stay in session state unless the user explicitly edits the template file
  - uploaded recipients can be used in memory without forcing a write to `recipients.csv`
  - reports and logs are intentionally written to disk

## Setup and common commands

Use the local virtual environment when available.

```bash
source venv/bin/activate
pip install -r requirements.txt
```

Run the Streamlit app:

```bash
python main.py --streamlit
```

Run a test SMS flow:

```bash
python main.py --test
```

Run a bulk campaign:

```bash
python main.py --bulk
```

Run tests:

```bash
python -m pytest
python -m pytest --cov=. --cov-report=term-missing
```

Quick syntax verification:

```bash
python -m py_compile sms_sender.py streamlit_app.py main.py quickstart.py
```

## Editing guidance

- Update tests when behavior changes.
- Update `README.md` when user-visible behavior, commands, or file conventions change.
- Prefer targeted fixes over large refactors unless the task explicitly asks for restructuring.
- Keep dependencies limited. Do not add packages unless they materially improve the project.
- Preserve current CSV column requirements:
  - `name`
  - `email`
  - `contact_number`

## Streamlit-specific guidance

- Prefer native Streamlit patterns over heavy custom CSS or framework imitation.
- Keep the UI readable and functional before trying to make it look sophisticated.
- Avoid broad CSS selectors that can break Streamlit/BaseWeb widgets.
- Treat message editing as runtime state, not code generation.
- If you change the campaign editor, verify:
  - the draft message can be edited
  - test send uses the edited draft
  - bulk send uses the edited draft
  - resetting the draft reloads the default template from `resources/message_template.txt` or a local override if present
- If you change recipient flows, verify:
  - sample recipients still work with no extra setup
  - imported in-memory lists still work without saving a file
  - `recipients.csv` remains optional, not mandatory
  - the bundled sample in `resources/sample-recipients.csv` still works even if the working directory has no sample file

## Sender and data rules

- Keep Sri Lanka phone normalization behavior consistent unless the user asks for broader support.
- Keep validation centralized in sender helpers where possible.
- Avoid duplicating recipient validation logic in multiple places unless the UI needs immediate feedback.
- If changing API request logic, preserve:
  - retry behavior
  - timeout handling
  - POST-first behavior with GET fallback where currently implemented
  - JSON report generation

## Testing expectations

Before finishing a code change, run the smallest relevant check first, then broader checks when needed.

Recommended order:

1. `python -m py_compile ...` for touched Python files
2. targeted `pytest` tests for the affected module
3. full `python -m pytest` for cross-cutting changes
4. `python -m pytest --cov=. --cov-report=term-missing` when modifying core behavior, tests, or project-wide flows

If you cannot run a needed check, say so clearly in your final summary.

## Security and safety

- Never commit `.env`.
- Treat `.env.sample` as documentation only.
- Do not expose credentials in logs, reports, tests, or README changes.
- Be careful with destructive shell commands. Do not delete logs, reports, or user CSV files unless explicitly asked.

## Documentation sync

If you change any of these, update `README.md` in the same task:

- startup commands
- recipient import/save behavior
- message template behavior
- test commands
- required files or project structure

## File precedence notes

If this repository later grows subprojects, add nested `AGENTS.md` files in subdirectories. The nearest `AGENTS.md` to the edited file should be treated as the most specific project guidance.
