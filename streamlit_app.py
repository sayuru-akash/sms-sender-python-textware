import json
import math
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from sms_sender import (
    APP_DIR,
    MESSAGE_TEMPLATE_FILE,
    RESOURCES_DIR,
    SMSSender,
    get_sms_message,
    is_valid_email,
    limit_name_to_two_words,
    normalize_sl_phone_number,
)

REQUIRED_RECIPIENT_COLUMNS = ["name", "email", "contact_number"]
DEFAULT_SAMPLE_CSV = "sample-recipients.csv"
DEFAULT_UPLOAD_CSV = "recipients.csv"
MEMORY_SOURCE = "__memory__"
REQUIRED_ENV_VARS = ["SMS_USERNAME",
                     "SMS_PASSWORD", "SMS_SOURCE", "SMS_API_URL"]
BUNDLED_SAMPLE_CSV = RESOURCES_DIR / DEFAULT_SAMPLE_CSV
LEGACY_SAMPLE_CSV = APP_DIR / DEFAULT_SAMPLE_CSV

st.set_page_config(
    page_title="SMS Campaign Manager",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded",
)


def apply_theme():
    """Minimal styling on top of native Streamlit components."""
    st.markdown(
        """
        <style>
        :root {
            --bg: #0b1220;
            --bg-elev: #111827;
            --bg-soft: #172033;
            --bg-sidebar: #0a1020;
            --border: rgba(148, 163, 184, 0.16);
            --text: #e5edf7;
            --muted: #94a3b8;
            --accent: #38bdf8;
            --accent-2: #22c55e;
            --warn: #fb923c;
        }
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(56, 189, 248, 0.08), transparent 24%),
                radial-gradient(circle at top right, rgba(34, 197, 94, 0.06), transparent 20%),
                linear-gradient(180deg, #0b1220 0%, #0f172a 100%);
            color: var(--text);
        }
        .block-container {
            max-width: 1100px;
            padding-top: 1.2rem;
            padding-bottom: 2rem;
        }
        [data-testid="stAppViewContainer"],
        [data-testid="stHeader"] {
            background: transparent;
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #08101f 0%, #0b1220 100%);
            border-right: 1px solid var(--border);
        }
        [data-testid="stSidebar"] * {
            color: var(--text);
        }
        .stApp,
        .stApp h1,
        .stApp h2,
        .stApp h3,
        .stApp h4,
        .stApp h5,
        .stApp h6,
        .stApp label,
        .stApp p,
        .stApp span {
            color: var(--text);
        }
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li,
        .stCaption,
        .app-subtitle {
            color: var(--muted);
        }
        .app-subtitle {
            margin-top: -0.35rem;
            font-size: 0.96rem;
        }
        .status-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin: 0.65rem 0 0.25rem;
        }
        .status-chip {
            padding: 0.28rem 0.7rem;
            border-radius: 999px;
            font-size: 0.82rem;
            font-weight: 600;
            border: 1px solid var(--border);
            background: rgba(23, 32, 51, 0.88);
            color: var(--text);
        }
        .chip-ok {
            background: rgba(34, 197, 94, 0.12);
            color: #86efac;
            border-color: rgba(34, 197, 94, 0.2);
        }
        .chip-warn {
            background: rgba(251, 146, 60, 0.12);
            color: #fdba74;
            border-color: rgba(251, 146, 60, 0.2);
        }
        [data-testid="stMetric"] {
            background: rgba(17, 24, 39, 0.9);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 0.6rem 0.8rem;
        }
        [data-testid="stMetricLabel"] p {
            color: var(--muted);
        }
        [data-testid="stMetricValue"] {
            color: var(--text);
        }
        [data-testid="stVerticalBlockBorderWrapper"] {
            background: rgba(17, 24, 39, 0.82);
            border: 1px solid var(--border);
            border-radius: 14px;
        }
        div[data-baseweb="tab-list"] {
            gap: 0.35rem;
        }
        button[data-baseweb="tab"] {
            background: rgba(17, 24, 39, 0.75);
            border: 1px solid var(--border);
            border-radius: 10px 10px 0 0;
            color: var(--muted);
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            background: rgba(23, 32, 51, 0.98);
            color: var(--text);
            border-bottom-color: rgba(56, 189, 248, 0.45);
        }
        .stButton > button,
        .stDownloadButton > button,
        .stFormSubmitButton > button {
            border-radius: 10px;
            min-height: 2.75rem;
            font-weight: 600;
            background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
            color: var(--text);
            border: 1px solid rgba(56, 189, 248, 0.18);
        }
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        div[data-baseweb="textarea"] > div {
            border-radius: 10px;
            background: rgba(17, 24, 39, 0.92);
            border-color: var(--border);
        }
        .stSelectbox [data-baseweb="select"] > div,
        .stSelectbox [data-baseweb="select"] input,
        .stSelectbox [data-baseweb="select"] span {
            color: var(--text) !important;
        }
        div[role="listbox"] {
            background: rgba(17, 24, 39, 0.98) !important;
            border: 1px solid var(--border) !important;
        }
        div[role="option"] {
            background: transparent !important;
            color: var(--text) !important;
        }
        div[role="option"][aria-selected="true"] {
            background: rgba(56, 189, 248, 0.12) !important;
        }
        .stTextInput input,
        .stTextArea textarea {
            color: var(--text);
        }
        .stSelectbox label,
        .stTextInput label,
        .stTextArea label,
        .stSlider label,
        .stCheckbox label {
            color: var(--text);
        }
        [data-baseweb="select"] svg,
        .stSlider [data-baseweb="slider"] * {
            color: var(--accent);
        }
        .stCodeBlock,
        pre,
        code {
            background: #0a1020 !important;
            color: #dbeafe !important;
        }
        [data-testid="stDataFrame"] {
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
        }
        [data-testid="stDataFrame"] [role="grid"] {
            background: rgba(17, 24, 39, 0.92);
        }
        [data-testid="stDataFrame"] div {
            color: var(--text);
        }
        .stAlert {
            background: rgba(17, 24, 39, 0.92);
            border: 1px solid var(--border);
            color: var(--text);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def ensure_session_state():
    """Initialize persistent UI state."""
    if "selected_source" not in st.session_state:
        if Path(DEFAULT_SAMPLE_CSV).exists():
            st.session_state.selected_source = DEFAULT_SAMPLE_CSV
        elif Path(DEFAULT_UPLOAD_CSV).exists():
            st.session_state.selected_source = DEFAULT_UPLOAD_CSV
        else:
            st.session_state.selected_source = DEFAULT_SAMPLE_CSV
    if "pending_selected_source" not in st.session_state:
        st.session_state.pending_selected_source = None
    if "imported_recipients" not in st.session_state:
        st.session_state.imported_recipients = None
    if "imported_label" not in st.session_state:
        st.session_state.imported_label = "Imported (unsaved)"
    if "draft_message" not in st.session_state:
        st.session_state.draft_message = get_sms_message()
    if "campaign_rate_limit" not in st.session_state:
        st.session_state.campaign_rate_limit = 2
    if "active_section" not in st.session_state:
        st.session_state.active_section = "Dashboard"


def load_recipients(file_path=None):
    """Load recipients from CSV."""
    target = resolve_csv_path(file_path or DEFAULT_UPLOAD_CSV)
    try:
        if target.exists():
            return pd.read_csv(target, dtype=str).fillna("")
        return pd.DataFrame()
    except Exception as exc:
        st.error(f"Error loading recipients: {exc}")
        return pd.DataFrame()


def resolve_csv_path(file_path):
    """Resolve known CSV names to their on-disk paths."""
    if file_path == DEFAULT_SAMPLE_CSV:
        for candidate in (Path(DEFAULT_SAMPLE_CSV), LEGACY_SAMPLE_CSV, BUNDLED_SAMPLE_CSV):
            if candidate.exists():
                return candidate
        return BUNDLED_SAMPLE_CSV
    return Path(file_path)


def get_available_csvs():
    """Return available CSV sources."""
    options = []
    if resolve_csv_path(DEFAULT_SAMPLE_CSV).exists():
        options.append(("Sample", DEFAULT_SAMPLE_CSV))
    if Path(DEFAULT_UPLOAD_CSV).exists():
        options.append(("Uploaded", DEFAULT_UPLOAD_CSV))
    if st.session_state.get("imported_recipients") is not None:
        options.append((st.session_state.get("imported_label",
                       "Imported (unsaved)"), MEMORY_SOURCE))
    return options


def set_selected_source(source):
    """Queue a source update for the next rerun."""
    st.session_state.selected_source = source
    st.session_state.pending_selected_source = source


def get_current_recipients():
    """Return active source id, label, and dataframe."""
    source = st.session_state.selected_source
    label_by_source = {value: label for label, value in get_available_csvs()}

    if source == MEMORY_SOURCE:
        imported_df = st.session_state.get("imported_recipients")
        if imported_df is not None:
            return source, label_by_source.get(source, "Imported (unsaved)"), imported_df.copy()
        if Path(DEFAULT_SAMPLE_CSV).exists():
            source = DEFAULT_SAMPLE_CSV
        elif Path(DEFAULT_UPLOAD_CSV).exists():
            source = DEFAULT_UPLOAD_CSV
        else:
            source = DEFAULT_SAMPLE_CSV
        st.session_state.selected_source = source

    return source, label_by_source.get(source, source), load_recipients(source)


def load_reports():
    """Return reports sorted by latest first."""
    report_dir = Path("reports")
    if not report_dir.exists():
        return []
    return sorted(report_dir.glob("*.json"), key=os.path.getmtime, reverse=True)


def load_report_data(report_path):
    """Load JSON report data."""
    try:
        with open(report_path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception as exc:
        st.error(f"Error loading report: {exc}")
        return None


def get_missing_columns(df):
    """Return missing required columns for recipient data."""
    if df.empty:
        return []
    return [column for column in REQUIRED_RECIPIENT_COLUMNS if column not in df.columns]


def parse_env_file():
    """Read .env values for display."""
    env_path = Path(".env")
    values = {}
    if not env_path.exists():
        return values

    with open(env_path, "r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if "=" in stripped and not stripped.startswith("#"):
                key, value = stripped.split("=", 1)
                values[key] = value
    return values


def mask_value(value):
    """Mask sensitive env values."""
    if not value:
        return "Not set"
    if len(value) <= 6:
        return "*" * len(value)
    return f"{value[:3]}{'*' * (len(value) - 5)}{value[-2:]}"


def recipients_summary(df):
    """Summarize current recipients."""
    if df.empty or get_missing_columns(df):
        return {"rows": len(df), "phones": 0, "emails": 0}

    return {
        "rows": len(df),
        "phones": df["contact_number"].astype(str).nunique(),
        "emails": df["email"].astype(str).str.lower().nunique(),
    }


def build_message_stats(message):
    """Compute message stats."""
    char_count = len(message)
    sms_parts = math.ceil(char_count / 160) if char_count else 0
    return {
        "char_count": char_count,
        "sms_parts": sms_parts,
        "has_placeholder": "{name}" in message,
    }


def prepare_uploaded_recipients(df):
    """Validate and clean uploaded CSV rows."""
    cleaned_rows = []
    invalid_rows = []

    for row_number, (_, row) in enumerate(df.iterrows(), start=2):
        name = limit_name_to_two_words(str(row.get("name", "")).strip())
        email = str(row.get("email", "")).strip().lower()
        raw_phone = str(row.get("contact_number", "")).strip()
        phone = normalize_sl_phone_number(raw_phone)

        errors = []
        if not name:
            errors.append("Missing name")
        if not is_valid_email(email):
            errors.append("Invalid email")
        if not phone:
            errors.append("Invalid phone")

        if errors:
            invalid_rows.append(
                {
                    "row": row_number,
                    "name": name,
                    "email": email,
                    "contact_number": raw_phone,
                    "errors": "; ".join(errors),
                }
            )
            continue

        cleaned_rows.append(
            {
                "name": name,
                "email": email,
                "contact_number": phone,
            }
        )

    cleaned_df = pd.DataFrame(cleaned_rows)
    duplicate_count = 0
    if not cleaned_df.empty:
        before_count = len(cleaned_df)
        cleaned_df = cleaned_df.drop_duplicates(
            subset=["contact_number"], keep="first")
        duplicate_count = before_count - len(cleaned_df)

    return cleaned_df, pd.DataFrame(invalid_rows), duplicate_count


def show_status_chips(current_file, recipients_df, env_vars, report_count):
    """Render short status badges below the title."""
    missing_env = [key for key in REQUIRED_ENV_VARS if not env_vars.get(key)]
    missing_columns = get_missing_columns(recipients_df)

    chips = [
        (
            "chip-ok" if not missing_env else "chip-warn",
            "Env ready" if not missing_env else "Env incomplete",
        ),
        (
            "chip-ok" if not missing_columns and not recipients_df.empty else "chip-warn",
            f"List: {current_file}",
        ),
        ("status-chip", f"Reports: {report_count}"),
    ]

    chip_html = "".join(
        f'<span class="status-chip {tone}">{label}</span>' for tone, label in chips
    )
    st.markdown(
        f'<div class="status-row">{chip_html}</div>', unsafe_allow_html=True)


def render_sidebar(current_file, recipients_df, env_vars):
    """Sidebar controls."""
    st.subheader("Source")

    available_csvs = get_available_csvs()
    if available_csvs:
        labels = [label for label, _ in available_csvs]
        paths = {label: path for label, path in available_csvs}
        current_label = next(
            (label for label, path in available_csvs if path == current_file),
            labels[0],
        )
        if st.session_state.get("csv_selector") not in labels:
            st.session_state.csv_selector = current_label
        selected_label = st.selectbox(
            "Recipients file",
            labels,
            index=labels.index(current_label),
            key="csv_selector",
        )
        st.session_state.selected_source = paths[selected_label]
    else:
        st.warning("No CSV found.")

    summary = recipients_summary(recipients_df)
    st.metric("Recipients", summary["rows"])
    st.metric("Unique phones", summary["phones"])

    st.divider()
    st.subheader("Checks")
    missing_env = [key for key in REQUIRED_ENV_VARS if not env_vars.get(key)]
    missing_columns = get_missing_columns(recipients_df)

    checks = [
        ("Credentials", not missing_env),
        ("Recipients loaded", not recipients_df.empty),
        ("CSV valid", not missing_columns),
        ("Message ready", bool(st.session_state.draft_message.strip())),
    ]
    for label, ok in checks:
        status = "OK" if ok else "Needs attention"
        st.caption(f"{label}: {status}")


def render_header(current_file, recipients_df, env_vars, reports):
    """Top header."""
    summary = recipients_summary(recipients_df)
    missing_env = [key for key in REQUIRED_ENV_VARS if not env_vars.get(key)]

    st.title("SMS Campaign Manager")
    st.markdown(
        '<p class="app-subtitle">Simple workflow for recipients, sending, and reports.</p>',
        unsafe_allow_html=True,
    )
    env_state = "ready" if not missing_env else "needs setup"
    st.caption(
        f"Source: {current_file} | Recipients: {summary['rows']} | Reports: {len(reports)} | Env: {env_state}"
    )


def render_dashboard_tab(current_file, recipients_df, env_vars, reports):
    """Minimal overview."""
    summary = recipients_summary(recipients_df)
    missing_env = [key for key in REQUIRED_ENV_VARS if not env_vars.get(key)]
    latest_report = reports[0].name if reports else "No reports yet"

    row1 = st.columns(2)
    with row1[0]:
        st.metric("Active list", current_file)
    with row1[1]:
        st.metric("Recipients", summary["rows"])

    row2 = st.columns(2)
    with row2[0]:
        st.metric("Reports", len(reports))
    with row2[1]:
        st.metric("Environment", "Ready" if not missing_env else "Needs setup")

    left, right = st.columns([1.4, 1], gap="large")
    with left:
        with st.container(border=True):
            st.subheader("Current list")
            missing_columns = get_missing_columns(recipients_df)
            if recipients_df.empty:
                st.info("No recipients loaded.")
            elif missing_columns:
                st.error(f"Missing column(s): {', '.join(missing_columns)}")
            else:
                st.dataframe(
                    recipients_df[REQUIRED_RECIPIENT_COLUMNS].head(8),
                    width="stretch",
                    hide_index=True,
                )

    with right:
        with st.container(border=True):
            st.subheader("Notes")
            st.caption(f"Latest report: {latest_report}")
            if missing_env:
                st.warning(f"Missing .env values: {', '.join(missing_env)}")
            else:
                st.success("All required .env values found.")
            st.caption("Use Recipients, then Campaign, then Reports.")


def render_recipients_tab(current_source, current_label, recipients_df):
    """Recipients management."""
    top_left, top_right = st.columns([1.4, 1], gap="large")

    with top_left:
        with st.container(border=True):
            st.subheader("Current recipients")
            search = st.text_input(
                "Search", placeholder="Name, email, or phone")

            if recipients_df.empty:
                st.info("No recipients in the selected file.")
            else:
                missing_columns = get_missing_columns(recipients_df)
                if missing_columns:
                    st.error(
                        f"{current_label} is missing: {', '.join(missing_columns)}")
                else:
                    visible_df = recipients_df[REQUIRED_RECIPIENT_COLUMNS].copy(
                    )
                    if search:
                        matches = visible_df.astype(str).apply(
                            lambda col: col.str.contains(
                                search, case=False, na=False)
                        )
                        visible_df = visible_df[matches.any(axis=1)]

                    st.dataframe(visible_df, width="stretch", hide_index=True)
                    st.download_button(
                        "Download CSV",
                        data=visible_df.to_csv(index=False).encode("utf-8"),
                        file_name="imported_recipients.csv" if current_source == MEMORY_SOURCE else current_source,
                        mime="text/csv",
                    )

    with top_right:
        with st.container(border=True):
            st.subheader("Add recipient")
            with st.form("add_recipient_form", clear_on_submit=True):
                name = st.text_input("Name")
                email = st.text_input("Email")
                phone = st.text_input("Phone")
                submitted = st.form_submit_button("Save")

                if submitted:
                    limited_name = limit_name_to_two_words(name)
                    cleaned_email = email.strip().lower()
                    cleaned_phone = normalize_sl_phone_number(phone)

                    if not limited_name:
                        st.error("Name is required.")
                    elif not is_valid_email(cleaned_email):
                        st.error("Invalid email.")
                    elif not cleaned_phone:
                        st.error("Invalid Sri Lanka mobile number.")
                    else:
                        if current_source == MEMORY_SOURCE and st.session_state.get("imported_recipients") is not None:
                            target_df = st.session_state.imported_recipients.copy()
                            existing_numbers = (
                                target_df["contact_number"].astype(
                                    str).tolist()
                                if not target_df.empty
                                else []
                            )
                            if cleaned_phone in existing_numbers:
                                st.error("Phone number already exists.")
                            else:
                                new_row = pd.DataFrame(
                                    {
                                        "name": [limited_name],
                                        "email": [cleaned_email],
                                        "contact_number": [cleaned_phone],
                                    }
                                )
                                st.session_state.imported_recipients = pd.concat(
                                    [target_df, new_row], ignore_index=True
                                )
                                set_selected_source(MEMORY_SOURCE)
                                st.success("Recipient added to imported list.")
                                st.rerun()
                            return

                        target_df = (
                            load_recipients(DEFAULT_UPLOAD_CSV)
                            if Path(DEFAULT_UPLOAD_CSV).exists()
                            else pd.DataFrame(columns=REQUIRED_RECIPIENT_COLUMNS)
                        )
                        target_missing = get_missing_columns(target_df)
                        if target_missing:
                            st.error(
                                f"{DEFAULT_UPLOAD_CSV} is missing: {', '.join(target_missing)}")
                        else:
                            existing_numbers = (
                                target_df["contact_number"].astype(
                                    str).tolist()
                                if not target_df.empty
                                else []
                            )
                            if cleaned_phone in existing_numbers:
                                st.error("Phone number already exists.")
                            else:
                                new_row = pd.DataFrame(
                                    {
                                        "name": [limited_name],
                                        "email": [cleaned_email],
                                        "contact_number": [cleaned_phone],
                                    }
                                )
                                target_df = pd.concat(
                                    [target_df, new_row], ignore_index=True)
                                target_df.to_csv(
                                    DEFAULT_UPLOAD_CSV, index=False)
                                set_selected_source(DEFAULT_UPLOAD_CSV)
                                st.success(
                                    "Recipient saved to recipients.csv.")
                                st.rerun()

    with st.container(border=True):
        st.subheader("Upload CSV")
        uploaded_file = st.file_uploader("Choose CSV", type=["csv"])

        if uploaded_file is not None:
            try:
                uploaded_df = pd.read_csv(uploaded_file, dtype=str).fillna("")
            except Exception as exc:
                st.error(f"Could not read CSV: {exc}")
                return

            missing_columns = get_missing_columns(uploaded_df)
            if missing_columns:
                st.error(
                    f"Uploaded CSV is missing: {', '.join(missing_columns)}")
                return

            cleaned_df, invalid_df, duplicate_count = prepare_uploaded_recipients(
                uploaded_df)

            stats = st.columns(3)
            with stats[0]:
                st.metric("Valid", len(cleaned_df))
            with stats[1]:
                st.metric("Invalid", len(invalid_df))
            with stats[2]:
                st.metric("Duplicates removed", duplicate_count)

            preview_tab, invalid_tab = st.tabs(["Clean rows", "Invalid rows"])
            with preview_tab:
                if cleaned_df.empty:
                    st.info("No valid rows.")
                else:
                    st.dataframe(cleaned_df, width="stretch", hide_index=True)
            with invalid_tab:
                if invalid_df.empty:
                    st.success("No invalid rows.")
                else:
                    st.dataframe(invalid_df, width="stretch", hide_index=True)

            action_left, action_right = st.columns(2)
            with action_left:
                if st.button("Use now", disabled=cleaned_df.empty):
                    st.session_state.imported_recipients = cleaned_df.copy()
                    st.session_state.imported_label = f"Imported ({uploaded_file.name})"
                    set_selected_source(MEMORY_SOURCE)
                    st.success(
                        f"Using {len(cleaned_df)} row(s) without saving a file.")
                    st.rerun()
            with action_right:
                if st.button("Save as recipients.csv", disabled=cleaned_df.empty):
                    cleaned_df.to_csv(DEFAULT_UPLOAD_CSV, index=False)
                    set_selected_source(DEFAULT_UPLOAD_CSV)
                    st.success(
                        f"Saved {len(cleaned_df)} row(s) to recipients.csv.")
                    st.rerun()


def render_campaign_tab(current_file, recipients_df):
    """Campaign editor and send flow."""
    if recipients_df.empty:
        st.warning("Load recipients first.")
        return

    missing_columns = get_missing_columns(recipients_df)
    if missing_columns:
        st.error(f"{current_file} is missing: {', '.join(missing_columns)}")
        return

    left, right = st.columns([1.35, 1], gap="large")

    with left:
        with st.container(border=True):
            st.subheader("Message")
            st.caption(
                f"Edits here stay in this app session. To change the default for future sessions, edit `resources/{MESSAGE_TEMPLATE_FILE.name}`."
            )

            def reset_draft_message():
                st.session_state.draft_message = get_sms_message()

            message = st.text_area(
                "SMS text",
                value=st.session_state.draft_message,
                key="draft_message",
                height=240,
                help="Use {name} for personalization.",
            )
            st.button(
                "Reset to default template",
                key="reset_draft_message",
                on_click=reset_draft_message,
            )
            stats = build_message_stats(message)
            metric_row = st.columns(3)
            with metric_row[0]:
                st.metric("Characters", stats["char_count"])
            with metric_row[1]:
                st.metric("SMS parts", stats["sms_parts"])
            with metric_row[2]:
                st.metric("Has {name}",
                          "Yes" if stats["has_placeholder"] else "No")

            preview_index = st.selectbox(
                "Preview recipient",
                options=range(len(recipients_df)),
                format_func=lambda idx: f"{recipients_df.iloc[idx]['name']} ({recipients_df.iloc[idx]['contact_number']})",
                key="preview_recipient",
            )
            preview_message = message.replace(
                "{name}", recipients_df.iloc[preview_index]["name"])
            st.code(preview_message, language=None)

    with right:
        with st.container(border=True):
            st.subheader("Send")
            rate_limit = st.slider(
                "Rate limit (seconds)",
                1,
                10,
                key="campaign_rate_limit",
            )
            estimated_seconds = len(recipients_df) * rate_limit
            st.metric("Recipients", len(recipients_df))
            st.metric("Est. duration",
                      f"{estimated_seconds // 60}m {estimated_seconds % 60}s")

            test_index = st.selectbox(
                "Test recipient",
                options=range(len(recipients_df)),
                format_func=lambda idx: f"{recipients_df.iloc[idx]['name']} ({recipients_df.iloc[idx]['contact_number']})",
                key="test_recipient",
            )
            if st.button("Send test SMS"):
                try:
                    with st.spinner("Sending test SMS..."):
                        sender = SMSSender()
                        recipient = recipients_df.iloc[test_index]
                        result = sender.send_sms(
                            phone_number=recipient["contact_number"],
                            message=message.replace(
                                "{name}", recipient["name"]),
                            name=recipient["name"],
                            email=recipient["email"],
                        )
                    if result["status"] == "success":
                        st.success("Test SMS sent.")
                    else:
                        st.error("Test SMS failed.")
                    st.json(result)
                except Exception as exc:
                    st.error(f"Error: {exc}")

            st.divider()
            confirm = st.checkbox("I reviewed the message and recipient list.")
            if st.button("Start campaign", disabled=not (confirm and message.strip())):
                try:
                    with st.spinner("Sending campaign..."):
                        sender = SMSSender()
                        sender.rate_limit_delay = rate_limit
                        if current_file == MEMORY_SOURCE:
                            results = sender.send_bulk_sms_dataframe(
                                recipients_df, message)
                        else:
                            results = sender.send_bulk_sms(
                                str(resolve_csv_path(current_file)), message)
                        report_path = sender.save_report()
                    result_row = st.columns(3)
                    with result_row[0]:
                        st.metric("Total", results["total"])
                    with result_row[1]:
                        st.metric("Successful", results["successful"])
                    with result_row[2]:
                        st.metric("Failed / skipped", results["failed"])
                    st.success(f"Done. Report: {report_path}")
                except Exception as exc:
                    st.error(f"Campaign failed: {exc}")


def render_reports_tab(reports):
    """Reports viewer."""
    if not reports:
        st.info("No reports yet.")
        return

    with st.container(border=True):
        selected_report = st.selectbox(
            "Report",
            reports,
            format_func=lambda path: path.name,
            key="report_selector",
        )
        report_data = load_report_data(selected_report)
        if not report_data:
            return

        details_df = pd.DataFrame(report_data.get("details", []))
        top = st.columns(3)
        with top[0]:
            st.metric("Total", report_data.get("total_sms", len(details_df)))
        with top[1]:
            st.metric("Successful", report_data.get("successful", 0))
        with top[2]:
            st.metric("Failed", report_data.get("failed", 0))

        if details_df.empty:
            st.info("No row-level details.")
        else:
            status_values = [
                "All"] + sorted(details_df["status"].dropna().astype(str).unique().tolist())
            status_filter = st.selectbox(
                "Status", status_values, key="report_status")
            visible_df = details_df
            if status_filter != "All":
                visible_df = details_df[details_df["status"].astype(
                    str) == status_filter]
            st.dataframe(visible_df, width="stretch", hide_index=True)

        st.download_button(
            "Download JSON",
            data=json.dumps(report_data, indent=2, ensure_ascii=False),
            file_name=selected_report.name,
            mime="application/json",
        )


def render_settings_tab(current_label, env_vars, reports):
    """Read-only operational settings."""
    left, right = st.columns([1, 1], gap="large")

    with left:
        with st.container(border=True):
            st.subheader("Environment")
            missing_env = [
                key for key in REQUIRED_ENV_VARS if not env_vars.get(key)]
            if missing_env:
                st.warning(f"Missing: {', '.join(missing_env)}")
            else:
                st.success("All required values are present.")

            env_df = pd.DataFrame(
                [
                    {"Setting": "SMS Username", "Value": mask_value(
                        env_vars.get("SMS_USERNAME", ""))},
                    {"Setting": "SMS Password", "Value": mask_value(
                        env_vars.get("SMS_PASSWORD", ""))},
                    {"Setting": "SMS Source", "Value": env_vars.get(
                        "SMS_SOURCE", "Not set")},
                    {"Setting": "SMS API URL", "Value": env_vars.get(
                        "SMS_API_URL", "Not set")},
                ]
            )
            st.dataframe(env_df, width="stretch", hide_index=True)

    with right:
        with st.container(border=True):
            st.subheader("Files")
            log_files = list(Path("logs").glob("*.log")
                             ) if Path("logs").exists() else []
            st.metric("Logs", len(log_files))
            st.metric("Reports", len(reports))
            st.metric("Selected source", current_label)
            st.caption("Use `python main.py --streamlit` from the active venv.")


def main():
    """Main entry point."""
    apply_theme()
    ensure_session_state()

    pending_selected_source = st.session_state.pending_selected_source
    if pending_selected_source:
        st.session_state.selected_source = pending_selected_source
        label_by_path = {csv_path: label for label,
                         csv_path in get_available_csvs()}
        if pending_selected_source in label_by_path:
            st.session_state.csv_selector = label_by_path[pending_selected_source]
        st.session_state.pending_selected_source = None

    env_vars = parse_env_file()
    current_file, current_label, recipients_df = get_current_recipients()
    reports = load_reports()

    with st.sidebar:
        render_sidebar(current_file, recipients_df, env_vars)

    current_file, current_label, recipients_df = get_current_recipients()
    reports = load_reports()

    render_header(current_label, recipients_df, env_vars, reports)

    st.caption("Navigate")
    section = st.segmented_control(
        "Section",
        ["Dashboard", "Recipients", "Campaign", "Reports", "Settings"],
        default=st.session_state.get("active_section", "Dashboard"),
        key="active_section",
        label_visibility="collapsed",
    )

    if section == "Dashboard":
        render_dashboard_tab(current_label, recipients_df, env_vars, reports)
    elif section == "Recipients":
        render_recipients_tab(current_file, current_label, recipients_df)
    elif section == "Campaign":
        render_campaign_tab(current_file, recipients_df)
    elif section == "Reports":
        render_reports_tab(reports)
    elif section == "Settings":
        render_settings_tab(current_label, env_vars, reports)


if __name__ == "__main__":
    main()
