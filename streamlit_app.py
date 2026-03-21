import streamlit as st
import pandas as pd
import json
import os
from pathlib import Path
from datetime import datetime
from sms_sender import SMSSender, get_sms_message, limit_name_to_two_words
import logging

# Page configuration
st.set_page_config(
    page_title="SMS Campaign Manager",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 10px;
        margin: 10px 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 5px;
        padding: 10px;
        margin: 10px 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        border-radius: 5px;
        padding: 10px;
        margin: 10px 0;
    }
    </style>
""", unsafe_allow_html=True)


def load_recipients(file_path=None):
    """Load recipients from CSV"""
    try:
        if file_path is None:
            file_path = "recipients.csv"

        if Path(file_path).exists():
            return pd.read_csv(file_path)
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading recipients: {str(e)}")
        return pd.DataFrame()


def get_available_csvs():
    """Get list of available CSV files"""
    csvs = []

    # Add sample recipients
    if Path("sample-recipients.csv").exists():
        csvs.append(("📄 sample-recipients.csv", "sample-recipients.csv"))

    # Add uploaded recipients
    if Path("recipients.csv").exists():
        csvs.append(("📤 recipients.csv (uploaded)", "recipients.csv"))

    return csvs


def load_reports():
    """Load available reports"""
    report_dir = Path("reports")
    if report_dir.exists():
        return sorted(report_dir.glob("*.json"), key=os.path.getmtime, reverse=True)
    return []


def display_header():
    """Display application header"""
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("📱 SMS Campaign Manager")
        st.markdown("*Manage and send SMS campaigns efficiently*")
    with col2:
        st.metric("Current Date", datetime.now().strftime("%Y-%m-%d %H:%M"))


def tab_recipients():
    """Manage recipients"""
    st.header("👥 Recipients Management")

    # Show current selected file
    current_file = st.session_state.get(
        "selected_csv", "sample-recipients.csv")
    st.info(f"Currently using: **{current_file}**")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Current Recipients")
        recipients_df = load_recipients(current_file)

        if not recipients_df.empty:
            st.dataframe(recipients_df, use_container_width=True)
            st.markdown(f"**Total Recipients:** {len(recipients_df)}")
        else:
            st.info("No recipients loaded yet. Create or upload a CSV file.")

    with col2:
        st.subheader("Add New Recipient")
        with st.form("add_recipient"):
            name = st.text_input("Name")
            email = st.text_input("Email")
            phone = st.text_input("Contact Number")
            submitted = st.form_submit_button("Add Recipient")

            if submitted and name and email and phone:
                try:
                    # Always add to recipients.csv
                    recipients_df = load_recipients("recipients.csv") if Path(
                        "recipients.csv").exists() else pd.DataFrame()
                    # Limit name to first 2 words
                    limited_name = limit_name_to_two_words(name)
                    new_row = pd.DataFrame({
                        "name": [limited_name],
                        "email": [email],
                        "contact_number": [phone]
                    })
                    recipients_df = pd.concat(
                        [recipients_df, new_row], ignore_index=True)
                    recipients_df.to_csv("recipients.csv", index=False)
                    st.success(f"✓ {limited_name} added successfully!")
                    st.session_state.selected_csv = "recipients.csv"
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error adding recipient: {str(e)}")

    # Upload CSV
    st.divider()
    st.subheader("📤 Upload Recipients CSV")
    uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.dataframe(df)
            if st.button("Save Uploaded CSV"):
                df.to_csv("recipients.csv", index=False)
                st.session_state.selected_csv = "recipients.csv"
                st.success(f"✓ {len(df)} recipients loaded successfully!")
                st.rerun()
        except Exception as e:
            st.error(f"❌ Error processing CSV: {str(e)}")


def tab_campaigns():
    """Create and manage campaigns"""
    st.header("📧 Campaign Management")

    current_file = st.session_state.get(
        "selected_csv", "sample-recipients.csv")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Message Template")
        default_message = get_sms_message()

        message = st.text_area(
            "SMS Message",
            value=default_message,
            height=250,
            help="Use {name} placeholder for personalization"
        )

        char_count = len(message)
        st.caption(
            f"Characters: {char_count} | SMS Parts: {(char_count // 160) + 1}")

    with col2:
        st.subheader("Campaign Settings")

        recipients_df = load_recipients(current_file)
        st.metric("Recipients to Send", len(recipients_df))
        st.caption(f"Using: **{current_file}**")

        rate_limit = st.slider(
            "Rate Limit (seconds between SMS)",
            min_value=1,
            max_value=10,
            value=2,
            help="Prevent API overload by adding delay between sends"
        )

        st.info("ℹ️ **Preview Recipients:**")
        st.dataframe(
            recipients_df[["name", "contact_number"]], use_container_width=True)

    st.divider()

    # Test send
    st.subheader("🧪 Test Send")
    col1, col2 = st.columns([2, 1])

    with col1:
        test_recipient = st.selectbox(
            "Select recipient for test",
            options=range(len(recipients_df)),
            format_func=lambda i: f"{recipients_df.iloc[i]['name']} ({recipients_df.iloc[i]['contact_number']})"
        ) if not recipients_df.empty else None

    with col2:
        st.write("")
        st.write("")
        if st.button("📤 Send Test SMS", use_container_width=True):
            if test_recipient is not None:
                try:
                    with st.spinner("Sending test SMS..."):
                        sender = SMSSender()
                        recipient = recipients_df.iloc[test_recipient]
                        personalized_msg = message.replace(
                            "{name}", recipient['name'])

                        result = sender.send_sms(
                            phone_number=recipient['contact_number'],
                            message=personalized_msg,
                            name=recipient['name'],
                            email=recipient['email']
                        )

                        if result["status"] == "success":
                            st.success("✓ Test SMS sent successfully!")
                            st.json(result)
                        else:
                            st.error("❌ Failed to send test SMS")
                            st.json(result)
                except Exception as e:
                    st.error(f"❌ Error sending test SMS: {str(e)}")

    st.divider()

    # Send campaign
    st.subheader("🚀 Send Campaign")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.warning(f"⚠️ This will send SMS to {len(recipients_df)} recipients")

    with col2:
        st.write("")
        st.write("")
        confirm = st.checkbox(
            "I confirm sending to all recipients", key="confirm_send")

    with col3:
        st.write("")
        st.write("")
        if st.button("🚀 START CAMPAIGN", use_container_width=True, disabled=not confirm):
            if len(recipients_df) > 0:
                try:
                    with st.spinner("Sending SMS campaign..."):
                        sender = SMSSender()
                        sender.rate_limit_delay = rate_limit
                        results = sender.send_bulk_sms(current_file, message)
                        report_path = sender.save_report()

                        st.success("✓ Campaign completed!")

                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Sent", results["total"])
                        with col2:
                            st.metric("Successful", results["successful"])
                        with col3:
                            st.metric("Failed", results["failed"])

                        st.info(f"📄 Report saved: {report_path}")

                except Exception as e:
                    st.error(f"❌ Campaign failed: {str(e)}")
            else:
                st.error("❌ No recipients found. Please add recipients first.")


def tab_reports():
    """View reports"""
    st.header("📊 Reports & History")

    reports = load_reports()

    if reports:
        selected_report = st.selectbox(
            "Select Report",
            options=reports,
            format_func=lambda x: x.name
        )

        try:
            with open(selected_report, 'r') as f:
                report_data = json.load(f)

            # Summary
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Timestamp", report_data["timestamp"][:10])
            with col2:
                st.metric("Total SMS", report_data["total_sms"])
            with col3:
                st.metric("Successful", report_data["successful"])
            with col4:
                st.metric("Failed", report_data["failed"])

            st.divider()

            # Details
            st.subheader("Details")
            details_df = pd.DataFrame(report_data["details"])
            st.dataframe(details_df, use_container_width=True)

            # Download report
            st.download_button(
                label="📥 Download Report JSON",
                data=json.dumps(report_data, indent=2, ensure_ascii=False),
                file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

        except Exception as e:
            st.error(f"❌ Error loading report: {str(e)}")
    else:
        st.info("No reports available yet. Send a campaign to generate reports.")


def tab_settings():
    """Application settings"""
    st.header("⚙️ Settings")

    st.subheader("🔐 SMS API Configuration")

    # Check .env file
    if Path(".env").exists():
        st.success("✓ .env file found")

        env_vars = {}
        with open(".env") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    env_vars[key] = value

        col1, col2 = st.columns(2)
        with col1:
            st.text_input("SMS Username", value=env_vars.get(
                "SMS_USERNAME", ""), disabled=True)
        with col2:
            st.text_input("SMS Source", value=env_vars.get(
                "SMS_SOURCE", ""), disabled=True)

        st.text_input("API URL", value=env_vars.get(
            "SMS_API_URL", ""), disabled=True)
    else:
        st.error("❌ .env file not found. Please create it with SMS credentials.")

    st.subheader("📁 Directories")

    col1, col2 = st.columns(2)
    with col1:
        logs_exist = Path("logs").exists()
        if logs_exist:
            log_files = list(Path("logs").glob("*.log"))
            st.metric("Log Files", len(log_files))
        else:
            st.info("No logs yet")

    with col2:
        reports_exist = Path("reports").exists()
        if reports_exist:
            report_files = list(Path("reports").glob("*.json"))
            st.metric("Report Files", len(report_files))
        else:
            st.info("No reports yet")


def main():
    """Main app"""

    # Initialize session state
    if "selected_csv" not in st.session_state:
        st.session_state.selected_csv = "sample-recipients.csv"

    # Sidebar - CSV Selection
    with st.sidebar:
        st.subheader("📋 Select Recipients File")

        available_csvs = get_available_csvs()

        if available_csvs:
            csv_options = {label: path for label, path in available_csvs}
            selected_label = st.selectbox(
                "Choose a recipients CSV file:",
                options=csv_options.keys(),
                index=list(csv_options.keys()).index(
                    next((label for label, path in available_csvs if path ==
                         st.session_state.selected_csv), available_csvs[0][0])
                ) if available_csvs else 0,
                key="csv_selector"
            )
            st.session_state.selected_csv = csv_options[selected_label]

            # Show file info
            selected_file = st.session_state.selected_csv
            df = load_recipients(selected_file)
            st.metric("Recipients Count", len(df))
        else:
            st.warning(
                "No CSV files found. Please upload a file or use the sample.")
            st.session_state.selected_csv = "sample-recipients.csv"

        st.divider()

    display_header()

    st.divider()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "👥 Recipients",
        "📧 Campaigns",
        "📊 Reports",
        "⚙️ Settings",
        "ℹ️ Help"
    ])

    with tab1:
        tab_recipients()

    with tab2:
        tab_campaigns()

    with tab3:
        tab_reports()

    with tab4:
        tab_settings()

    with tab5:
        st.header("ℹ️ Help & Guide")

        st.subheader("🚀 Getting Started")
        st.markdown("""
        1. **Add Recipients** - Go to the Recipients tab and add or upload a CSV file
        2. **Customize Message** - Go to Campaigns tab and customize your SMS message
        3. **Test Send** - Send a test SMS to verify everything works
        4. **Send Campaign** - When ready, send the campaign to all recipients
        5. **Check Reports** - View detailed reports of sent campaigns
        
        ### CSV Format
        Your CSV file should have these columns:
        - `name` - Student/recipient name
        - `email` - Email address
        - `contact_number` - Phone number
        
        ### Features
        - ✅ Rate limiting to prevent API overload
        - ✅ Automatic retry logic for failed sends
        - ✅ Comprehensive error handling
        - ✅ Detailed logging and reporting
        - ✅ Message personalization with {name} placeholder
        - ✅ Test send before campaign launch
        - ✅ JSON reports for audit trail
        """)

        st.subheader("📞 SMS API Details")
        st.info("""
        **API:** Text-Ware SMS Gateway
        **Features:**
        - Reliable delivery
        - Rate limiting: 2 seconds between sends
        - Automatic retry on failures (3 attempts)
        - Timeout: 30 seconds per request
        """)


if __name__ == "__main__":
    main()
