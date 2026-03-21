# 📱 SMS Campaign Manager

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit 1.55](https://img.shields.io/badge/streamlit-1.55-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Pytest](https://img.shields.io/badge/tests-pytest-0A9EDC?logo=pytest&logoColor=white)](https://pytest.org/)
[![Last Commit](https://img.shields.io/github/last-commit/sayuru-akash/sms-sender-python-textware)](https://github.com/sayuru-akash/sms-sender-python-textware)

**Complete SMS sending solution** with rate limiting, retry logic, error handling, logging, and reporting.

---

## ⚡ Quick Start (1 Minute)

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Launch web dashboard
python main.py --streamlit
```

Opens interactive dashboard at `http://localhost:8501` by default.

---

## 🎯 What This Does

Sends personalized SMS messages to recipients from CSV files using the Text-Ware SMS API.

**Features:**

- ✅ Flexible CSV selection (sample or uploaded)
- ✅ Unsaved imported recipient lists can be used immediately
- ✅ Single & bulk SMS sending
- ✅ Automatic name personalization {name}
- ✅ Smart name handling - limits to first 2 words
- ✅ Automatic phone cleanup to Sri Lanka format 94XXXXXXXXX
- ✅ Email format validation on import and manual add
- ✅ Invalid CSV rows are rejected with row-level reasons
- ✅ Rate limiting (adjustable) - prevents API overload
- ✅ Automatic retry (3 attempts) - handles failures
- ✅ Detailed logging - all events recorded
- ✅ JSON reports - campaign results
- ✅ Error handling - graceful failure handling
- ✅ Web dashboard - full interactive UI
- ✅ CLI tools - command line interface
- ✅ Menu system - user-friendly navigation

---

## 📁 Project Structure

```
sms-sender-python-textware/
├── sms_sender.py          Core SMS engine
├── main.py                CLI entry point
├── streamlit_app.py       Web dashboard (recommended)
├── quickstart.py          Menu system
├── .env                   SMS credentials (NOT committed - see .env.sample)
├── .env.sample            Environment template (reference)
├── recipients.csv         Optional saved recipient list
├── resources/
│   ├── message_template.txt   Default SMS template (editable)
│   └── sample-recipients.csv  Bundled sample data
├── requirements.txt       Python dependencies
├── pytest.ini             Pytest configuration
├── tests/                 Automated test suite
├── README.md              This documentation
└── venv/                  Virtual environment

Auto-generated folders:
├── logs/                  Application logs with timestamps
└── reports/               JSON campaign reports
```

**Security Note:** `.env` file is in `.gitignore` and never committed. Only `.env.sample` is in the repo as a template.

---

## 🚀 How to Use

### Web Dashboard (Recommended) ⭐

```bash
python main.py --streamlit
```

Opens at `http://localhost:8501` with full UI.

Direct Streamlit command also works:

```bash
python -m streamlit run streamlit_app.py
```

**Dashboard Features:**

**1️⃣ Recipients Tab**

- **🔄 CSV File Selection**: Switch between:
  - `Sample` (default, backed by bundled sample data)
  - `recipients.csv` (saved custom list, if you choose to persist one)
  - `Imported (...)` (temporary in-memory upload)
- **📊 View Recipients**: Table showing all current recipients
- **➕ Add Recipient**: Single form entry for one person
- **📤 Upload CSV**: Upload custom recipients file
- Show total recipient count

**2️⃣ Campaigns Tab**

- **✏️ Message Template**: Customize SMS with `{name}` placeholder
- **⚙️ Campaign Settings**:
  - Shows selected recipients count
  - Rate limit slider (1-10 seconds)
- **👁️ Preview**: See list of recipients who'll receive SMS
- **🧪 Test Send**: Send one test SMS to verify
- **🚀 Send Campaign**: Send to all recipients (with confirmation)
- **📊 Results**: View success/failure metrics

**3️⃣ Reports Tab**

- **📋 View Reports**: Select from all campaign reports
- **📈 Summary Metrics**: Total, successful, failed SMS count
- **📝 Detailed Log**: Full details of each SMS sent
- **📥 Download**: Export report as JSON

**4️⃣ Settings Tab**

- View SMS API configuration (read-only for security)
- View log and report file counts

### CLI Interface

```bash
# Menu system (interactive)
python quickstart.py

# Send test SMS
python main.py --test

# Send to all recipients
python main.py --bulk
```

### Direct Python Usage

```python
from sms_sender import SMSSender, get_sms_message

sender = SMSSender()
message = get_sms_message()
result = sender.send_sms("0768622302", message, "Name", "email@example.com")
```

---

## 📋 Recipients Management

### Using Sample Recipients (Default)

- `resources/sample-recipients.csv` is bundled with the app and always available through the Sample source
- Contains: Sayuru Akash, test@gmail.com, 0777123456
- Best option for first-time setup and quick verification

### Upload Custom Recipients

1. Go to **Recipients Tab**
2. Click **Upload Recipients CSV**
3. Select your CSV file
4. Choose **Use now** to work from the cleaned upload immediately without writing any file
5. Choose **Save as recipients.csv** only if you want the cleaned list persisted on disk

### CSV Format Required

```
name,email,contact_number
Sayuru Akash,test@gmail.com,0777123456
John Doe,john@example.com,0761234567
Jane Smith,jane@example.com,0768765432
```

**Requirements:**

- **name**: Required for personalization (automatically limited to first 2 words)
- **email**: Required and must be valid format (example: info@codezela.com)
- **contact_number**: Required and must be a valid Sri Lanka mobile number

Accepted phone input formats (all normalized to 94XXXXXXXXX):

- 7XXXXXXXX
- 07XXXXXXXX
- 947XXXXXXXX
- +94 7X XXX XXXX
- Variations with spaces, dashes, or parentheses

Upload behavior:

- CSV importer auto-cleans name, email, and phone fields
- Invalid rows are shown with row numbers and reasons
- Valid cleaned rows can be used immediately as a temporary imported source
- Saving to `recipients.csv` is optional
- Duplicate phone numbers are automatically deduplicated (first row kept)

**Name Handling:**

- Names with more than 2 words are automatically limited to the first 2 words
- Example: "Muhammad Abdullah Hassan" → "Muhammad Abdullah"
- This applies to both uploaded CSVs and manually added recipients
- Prevents long names in personalization

### File Selection at Campaign Time

- Use sidebar selector to choose which CSV to use
- Shows recipient count for selected file
- Defaults to `Sample`
- Automatically switches to uploaded file when created

---

## 📋 Configuration

### SMS Credentials (.env)

Create `.env` file from `.env.sample` with your Text-Ware credentials:

```env
SMS_USERNAME=your_textware_username_here
SMS_PASSWORD=your_textware_password_here
SMS_SOURCE=YOUR_SENDER_ID
SMS_API_URL=https://msg.text-ware.com/send_sms.php
```

**Security:**

- ✅ `.env` is in `.gitignore` - never committed to repo
- ✅ Only `.env.sample` is shared - acts as template
- ✅ Credentials are local-only
- ✅ Safe to commit the project

### Recipients File

Two options available:

1. **Sample source** (default)
   - Built-in test data
   - Always available
   - Backed by `resources/sample-recipients.csv`
   - Good for testing

2. **recipients.csv** (your uploads)
   - Optional saved list on disk
   - Persists between sessions
   - Can be edited through the dashboard or manually in a text editor / spreadsheet tool

---

## 📱 SMS Message Template

**Default Template:**

The default SMS text is loaded from `resources/message_template.txt`.

```
Dear Student, {name}

We're excited to announce that the CCA Bootcamp Programs Inauguration
Ceremony will be held today.

This will be the official launch session for our bootcamp programs under
BYOW, DDIGITAL, RANDS, and VAT0. We warmly invite you to join us and be
part of this important beginning.

Date: 22 March 2026
Time: 9.00 PM
Platform: Zoom

Join Link: https://us06web.zoom.us/j/85143454719?pwd=...

Passcode: 331423

We look forward to having you with us tonight.

SITC Campus X CodeZela
```

**Personalization:**

- Use `{name}` placeholder for recipient's name
- Example: "Dear Student, Sayuru Akash"
- If name missing, sends without replacement

**Customize in Streamlit Dashboard:**

- Go to **Campaigns > Message Template**
- Edit text directly in the web UI
- The edited message is kept in Streamlit session state for the current app session
- Sending from the dashboard uses the edited message directly without rewriting Python files
- This is the recommended way to adjust a campaign message before sending

**Or edit the default template file:**

```text
resources/message_template.txt
```

- This controls the default message used by the CLI and by new Streamlit sessions
- Streamlit message edits do not rewrite this file
- Edit this file only when you want to change the default template for future runs

---

## ⚙️ Performance & Configuration

### Default Settings

| Setting        | Value      | Adjustable           |
| -------------- | ---------- | -------------------- |
| Rate limit     | 2 seconds  | Yes (1-10 in UI)     |
| Retry attempts | 3 times    | Code only            |
| Timeout        | 30 seconds | Code only            |
| API method     | POST       | Auto fallback to GET |

### Speed Estimates

- **Speed:** ~30 SMS/minute (with 2-sec rate limit)
- **100 recipients:** ~3-4 minutes
- **500 recipients:** ~15-20 minutes
- **1000 recipients:** ~30-40 minutes
- **Success rate:** 99%+ with retry logic

### Customize Rate Limit

- **In Dashboard**: Campaigns tab > Rate Limit slider
- **In Code**: Edit `sms_sender.py`, line with `self.rate_limit_delay`

### Customize API Retry

Edit `sms_sender.py`:

```python
max_retries = 3  # Change this value
timeout = 30  # Request timeout in seconds
```

---

## 📊 Logging & Reports

### Campaign Reports

**Location:** `reports/sms_report_YYYYMMDD_HHMMSS.json`

**Contains:**

- Timestamp of campaign
- Total SMS count
- Success/failure breakdown
- Individual SMS results:
  - Status (success/error)
  - Phone number
  - Recipient name & email
  - API response
  - Error details (if failed)

**View report:**

```bash
cat reports/sms_report_*.json | python -m json.tool
```

### Application Logs

**Location:** `logs/sms_sender_YYYYMMDD_HHMMSS.log`

**Contains:**

- All API calls and responses
- Error messages with context
- Rate limiting info
- Retry attempts
- Success confirmations

**View logs:**

```bash
tail -f logs/sms_sender_*.log
```

---

## 🧪 Testing

### Automated Test Suite

Run the full suite:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=. --cov-report=term-missing
```

The suite covers:

- core SMS sender helpers and API-request behavior
- bulk sending, reports, and fallback paths
- CLI entry points in `main.py`
- quickstart/menu flows in `quickstart.py`
- Streamlit app state and recipient workflows

Current local verification:

- `85` tests passing
- `92%` total coverage from `pytest --cov=. --cov-report=term-missing`

### Quick Test: Web Dashboard

```bash
python main.py --streamlit
```

1. Open `http://localhost:8501`
2. Go to **Campaigns** tab
3. Click **Send Test SMS**
4. Check report in **Reports** tab

### Test via Command Line

```bash
python main.py --test
```

Sends one SMS to first recipient in CSV.

### Full Campaign

```bash
python main.py --bulk
```

Sends to all recipients with confirmation.

---

## ✅ Pre-Commit Checklist

- [x] `.env` file is in `.gitignore` (credentials never committed)
- [x] `.env.sample` included as template
- [x] Virtual environment in `.gitignore`
- [x] `__pycache__/` in `.gitignore`
- [x] Logs and reports auto-generated (safe to ignore)
- [x] No hardcoded credentials in code
- [x] README updated with all features
- [x] All required files present

**Before commit, verify:**

```bash
git status  # Should show no .env file
cat .gitignore | grep -E "\.env|venv"  # Should find both
```

---

## ❌ Troubleshooting

| Problem                      | Solution                                                            |
| ---------------------------- | ------------------------------------------------------------------- |
| **Streamlit not starting**   | Ensure venv is activated: `source venv/bin/activate`                |
| **Module not found errors**  | Install dependencies: `pip install -r requirements.txt`             |
| **".env not found"**         | Create `.env` from `.env.sample` with your credentials              |
| **No recipients showing**    | Use the bundled Sample source or upload a custom file               |
| **API connection failed**    | Check internet, verify SMS credentials in `.env`                    |
| **SMS not sending**          | Check phone format (07XXXXXXXX for Sri Lanka or full international) |
| **Port 8501 already in use** | Stop the existing process with `lsof -ti:8501 | xargs kill -9`, or let Streamlit choose the next free port |
| **venv not activating**      | Recreate: `python3 -m venv venv && source venv/bin/activate`        |

**Debug steps:**

1. Check if venv is active: You should see `(venv)` in terminal
2. View logs: `cat logs/sms_sender_*.log`
3. Check reports: `cat reports/sms_report_*.json | python -m json.tool`
4. Test credentials: `echo $SMS_USERNAME` (should show username)
5. Verify bundled sample: `head -5 resources/sample-recipients.csv`

---

## 🔐 Security & Privacy

**Credential Safety:**

- ✅ `.env` file is `.gitignore`d - never committed
- ✅ Only `.env.sample` in repo as reference
- ✅ Credentials never logged or displayed
- ✅ API calls use HTTPS only
- ✅ No hardcoded secrets in code

**Data Protection:**

- ✅ Recipient data in transit via HTTPS
- ✅ Reports saved locally (not uploaded)
- ✅ Logs contain no passwords
- ✅ Can safely commit project to public repo

**Best Practices:**

- Never share `.env` file
- Rotate credentials periodically
- Monitor logs for errors
- Keep dependencies updated

---

## 📈 API Information

**Provider:** Text-Ware SMS Gateway

**Request Details:**

- Endpoint: `https://msg.text-ware.com/send_sms.php`
- Method: POST (with GET fallback)
- Protocol: HTTPS
- Timeout: 30 seconds

**Required Parameters:**

- `username` - API username (from `.env`)
- `password` - API password (from `.env`)
- `src` - Sender ID (from `SMS_SOURCE`)
- `dst` - Destination phone number
- `text` - Message body

**Response:**

- Format: JSON
- Success: HTTP 200 with operation ID
- Error: HTTP 400+ with error message

**Retry Strategy:**

- Automatic on: 429, 500, 502, 503, 504
- Backoff: 1 second between attempts
- Max retries: 3 (configurable)

---

## 📞 Dependencies

**Required packages:**

```
requests           # HTTP library
python-dotenv      # Environment variables
pandas             # CSV handling
streamlit          # Web dashboard
watchdog           # Faster Streamlit file watching on macOS/Linux
pytest             # Test runner
pytest-cov         # Coverage reporting
```

**Install all:**

```bash
pip install -r requirements.txt
```

---

## ✅ Quick Checklist

Before first use:

- [ ] `.env` exists with SMS credentials
- [ ] Bundled sample source is available, or upload/create `recipients.csv`
- [ ] `pip install -r requirements.txt` completed
- [ ] Internet connection working
- [ ] Python 3.8+ installed

---

## 🎯 Common Tasks

### Add New Recipients

Best option in the dashboard:

- Use **Recipients > Upload CSV > Use now** for a temporary in-memory list
- Use **Save as recipients.csv** only when you want a reusable saved list

Manual file edit also works when needed. Edit `recipients.csv` and add rows:

```csv
name,email,contact_number
New Person,email@example.com,07XXXXXXXX
```

### Change Message

- Recommended: edit the message directly in the Streamlit **Campaigns** tab
- Optional: edit `resources/message_template.txt` if you want to change the default template shown in new app sessions and used by the CLI

### Adjust Speed

Reduce `rate_limit_delay` in `sms_sender.py` (faster but more API requests)

### Increase Reliability

Increase `max_retries` in `sms_sender.py` (slower but fewer failures)

### View Campaign Results

```bash
cat reports/sms_report_*.json | python -m json.tool
```

### Monitor Sending

```bash
tail -f logs/sms_sender_*.log
```

---

## 📊 Example Workflow

**Step 1: Choose recipients**

Recommended path:

- Start with the `Sample` source for a quick end-to-end test
- Or upload your own CSV and click **Use now** to work without writing a file

Optional saved path:

```bash
# Edit recipients.csv with your recipients
nano recipients.csv
```

**Step 2: Customize message** (optional)

Recommended path:

- Edit the draft message directly in the Streamlit **Campaigns** tab
- This uses the updated message immediately without rewriting files

Optional default-template edit:

```bash
# Edit the default message template if needed
nano resources/message_template.txt
```

**Step 3: Send test SMS**

```bash
python main.py --test
```

**Step 4: Check result**

```bash
cat reports/sms_report_*.json | python -m json.tool
```

**Step 5: Send full campaign**

```bash
python main.py --bulk
```

**Step 6: Review results**

```bash
cat reports/sms_report_*.json | python -m json.tool
tail -f logs/sms_sender_*.log
```

---

## 🎓 Understanding the System

### How SMS Sending Works

1. **Load recipients** from the selected source (`Sample`, `recipients.csv`, or an imported in-memory list)
2. **Personalize message** - replace `{name}` with recipient name
3. **Send SMS** via Text-Ware API
4. **Rate limit** - wait 2 seconds before next SMS
5. **Handle response** - log result
6. **Retry on failure** - up to 3 attempts with backoff
7. **Generate report** - save all results to JSON
8. **Create logs** - record all events

### Error Handling

- Network timeout → Automatic retry
- Connection error → Automatic retry with backoff
- HTTP error (400-599) → Log and report
- Missing data → Skip with warning
- Invalid CSV → Error message with details

### Rate Limiting

- Prevents API overload by spacing requests
- 2 seconds between SMS (default)
- Configurable based on API limits
- Important for reliability

### Retry Logic

- Tries 3 times on failure
- Exponential backoff: 1s, 2s, 4s
- Handles transient failures
- Comprehensive error reporting

---

## 🚀 Getting Started

1. **Clone/download project** to `/Users/sayuru/PycharmProjects/sms-sender-python-textware`

2. **Install dependencies:**

   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Verify setup:**

   ```bash
   python main.py --streamlit
   ```

4. **Choose recipients**: start with the `Sample` source, upload a CSV and click **Use now**, or edit `recipients.csv` if you want a saved list

5. **Send SMS:**

   ```bash
   python main.py --bulk
   ```

6. **View results:**
   ```bash
   cat reports/sms_report_*.json | python -m json.tool
   ```

---

## Troubleshooting

If something is not working as expected, start with these checks:

1. Review `logs/sms_sender_*.log` for request, retry, and error details
2. Inspect `reports/sms_report_*.json` to confirm which recipients succeeded, failed, or were skipped
3. Run `python main.py --test` to verify credentials and API connectivity before a full campaign
4. Confirm `.env` contains valid Text-Ware credentials and sender configuration
5. Reinstall dependencies with `pip install --upgrade -r requirements.txt` if your environment is out of sync

For Streamlit-specific issues, restart the app with:

```bash
python main.py --streamlit
```

For test execution and local verification, use:

```bash
python -m pytest --cov=. --cov-report=term-missing
```

---

## Repository

- GitHub: [sayuru-akash/sms-sender-python-textware](https://github.com/sayuru-akash/sms-sender-python-textware)
- Dashboard: `python main.py --streamlit`
- CLI test send: `python main.py --test`
- Full campaign: `python main.py --bulk`
- Interactive menu: `python quickstart.py`

---

## Issues

For bugs, regressions, or feature requests, use the GitHub issue tracker:

- Issues: [github.com/sayuru-akash/sms-sender-python-textware/issues](https://github.com/sayuru-akash/sms-sender-python-textware/issues)

When reporting a problem, include:

- the command you ran
- whether you used `sample-recipients.csv`, `recipients.csv`, or an imported in-memory list
- the relevant error from `logs/sms_sender_*.log`
- the related report file from `reports/` if a campaign started

---

## Contributing

Contributions are welcome through GitHub pull requests:

1. Fork the repository
2. Create a branch for your change
3. Run `pytest --cov=. --cov-report=term-missing`
4. Update documentation when behavior changes
5. Open a pull request with a clear summary

Keep changes focused, avoid committing `.env`, and include tests for any behavior change in the sender, CLI, or Streamlit app.
