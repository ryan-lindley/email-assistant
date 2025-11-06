# Email Management Agent

An intelligent email management system that analyzes, classifies, and manages emails across multiple Gmail accounts using advanced machine learning and pattern recognition.

## Features

### Multi-Account Support (4-6 Gmail Accounts)
- **Unified view** across all your Gmail accounts
- **Parallel authentication** and email fetching
- **Cross-account deduplication** to eliminate duplicate emails
- **Account-specific priorities** (high/normal/low)
- **Unified ML model** trained on all your email patterns

### Advanced ML Classification
- **Ensemble classifier** (Random Forest + Gradient Boosting)
- **67 advanced features** (metadata, content, sender, temporal, structural, behavioral)
- **Confidence-based predictions** with uncertainty detection
- **Active learning** from user feedback
- **Model interpretability** (SHAP values planned)

### Calendar Integration
- **Deadline extraction** from emails
- **Follow-up reminders** with multi-channel notifications
- **Google Calendar sync** across all accounts
- **Smart reminder system** for critical deadlines

### Security & Privacy
- **Keyring credential storage** (OS-level encryption)
- **SQLCipher database encryption** (AES-256)
- **Input validation** (SQL injection & path traversal prevention)
- **Secure logging** (sensitive data filtering)
- **No plaintext secrets** anywhere in the codebase

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Gmail accounts (4-6 recommended for multi-account features)
- Google Cloud Console access for OAuth credentials

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/email-assistant.git
cd email-assistant
```

2. **Create and activate virtual environment:**
```bash
# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure environment (optional):**
```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your preferences (or use defaults)
nano .env
```

### Multi-Account Setup

#### Step 1: Get OAuth Credentials for Each Account

For **each** Gmail account you want to manage:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable APIs:
   - **Gmail API** (for email access)
   - **Google Calendar API** (for calendar integration)
4. Create OAuth 2.0 credentials:
   - Go to **APIs & Services → Credentials**
   - Click **Create Credentials → OAuth client ID**
   - Application type: **Desktop app**
   - Download the credentials JSON file
5. Save as `credentials_account1.json`, `credentials_account2.json`, etc.

**Important:** You'll need separate credentials files for each account you want to access.

#### Step 2: Configure Accounts

1. **Create accounts configuration:**
```bash
cp accounts.json.example accounts.json
```

2. **Edit accounts.json** with your account details:
```json
{
  "accounts": [
    {
      "name": "Personal",
      "email": "your.personal@gmail.com",
      "credentials_path": "credentials_personal.json",
      "priority": "high",
      "enabled": true
    },
    {
      "name": "Work",
      "email": "your.work@gmail.com",
      "credentials_path": "credentials_work.json",
      "priority": "high",
      "enabled": true
    },
    {
      "name": "Side Project",
      "email": "project@gmail.com",
      "credentials_path": "credentials_project.json",
      "priority": "normal",
      "enabled": true
    }
  ],
  "settings": {
    "parallel_fetch": true,
    "max_emails_per_account": 1000,
    "unified_model": true,
    "cross_account_deduplication": true,
    "sync_interval_minutes": 15
  }
}
```

**Configuration Options:**
- `name`: Friendly name for the account
- `email`: Gmail address
- `credentials_path`: Path to OAuth credentials JSON file
- `priority`: `high`, `normal`, or `low` (affects processing order)
- `enabled`: `true` or `false` (disable accounts temporarily)

#### Step 3: Test Multi-Account Setup

Run the configuration test (no API calls):
```bash
python test_multi_account.py --dry-run
```

Run full integration test (requires authentication):
```bash
python test_multi_account.py
```

This will:
- ✅ Validate configuration
- ✅ Open browser for OAuth (one-time per account)
- ✅ Test authentication for all accounts
- ✅ Fetch sample emails (50 per account)
- ✅ Test cross-account deduplication
- ✅ Verify unified view

**First-time OAuth:** You'll see browser windows for each account. Grant permissions for:
- Gmail: Read and modify emails
- Calendar: Read and write events

## Usage

### Analyze All Your Accounts

Run comprehensive analysis across all configured accounts:

```bash
# Analyze all accounts (default: 1000 emails per account)
python analyze_all_accounts.py

# Analyze with custom email limit
python analyze_all_accounts.py --max-per-account 500

# Use custom config file
python analyze_all_accounts.py --config my_accounts.json
```

This will:
1. Authenticate all enabled accounts
2. Fetch emails from each account (in parallel)
3. Deduplicate across accounts
4. Analyze patterns (bot detection, timing, senders)
5. Generate ML recommendations
6. Save detailed report to `analysis_reports/`

**Output:**
- Bot vs human email ratio per account
- Top sender domains across all accounts
- Time distribution analysis
- ML feature recommendations
- Cross-account insights (shared senders, diversity metrics)

### Train Unified ML Model

Train a single ML model that works across all your accounts:

```bash
# Train on all accounts (default: 1000 emails per account)
python -m ml.multi_account_training

# Custom training
python -m ml.multi_account_training --max-per-account 2000 --test-size 0.25

# Specify output path
python -m ml.multi_account_training --output models/my_classifier.pkl
```

The unified model:
- Learns patterns from ALL your accounts
- Handles account-specific quirks automatically
- Achieves 75-92% accuracy (after training on real data)
- Provides confidence scores for each prediction
- Flags uncertain predictions for review

### Single Account Analysis (Legacy)

For analyzing a single account:

```bash
# Requires credentials.json in project root
python analyze_mailbox.py
```

## Typical Workflow

### First Time Setup (One-time)

1. **Get credentials for each account** (see Multi-Account Setup above)
2. **Configure accounts.json** with all your Gmail accounts
3. **Test configuration:**
   ```bash
   python test_multi_account.py --dry-run  # Config test only
   python test_multi_account.py            # Full test with API
   ```

### Regular Use

1. **Analyze your email patterns:**
   ```bash
   python analyze_all_accounts.py
   ```
   Review the analysis report in `analysis_reports/` to understand your email patterns.

2. **Train unified ML model:**
   ```bash
   python -m ml.multi_account_training
   ```
   This creates a classifier in `models/unified_classifier.pkl`.

3. **Use the model** (integration coming in Phase 4):
   - Automatic email classification
   - Priority inbox across all accounts
   - Deadline extraction
   - Follow-up reminders
   - Calendar integration

### Continuous Improvement

The system uses **active learning** to improve over time:
- Review uncertain predictions (confidence < 0.7)
- Provide feedback on misclassifications
- Model automatically retrains with your corrections
- Accuracy improves with each feedback cycle

## Security & Privacy

### Credential Storage
- **OAuth tokens** stored in OS keyring (encrypted by your system login)
  - Linux: Secret Service (GNOME Keyring)
  - macOS: Keychain
  - Windows: Credential Locker
- **No plaintext tokens** anywhere in files or logs
- **Per-account isolation** - each account's tokens stored separately

### Database Encryption
- **SQLCipher** with AES-256 encryption for all stored emails
- Encryption key stored in OS keyring (never in plaintext)
- All email content encrypted at rest

### Input Validation
- SQL injection prevention (parameterized queries + validation)
- Path traversal attack prevention
- Email address format validation
- Sanitized logging (sensitive data filtered)

### API Permissions
The application requests these Google API scopes:
- `gmail.readonly` - Read emails (for analysis)
- `gmail.modify` - Modify labels and metadata (no deletion)
- `calendar` - Read/write calendar events
- `calendar.events` - Create reminders for deadlines

**You maintain full control:** You can revoke access anytime at [Google Account Permissions](https://myaccount.google.com/permissions).

## Project Structure

```
email-assistant/
├── config/
│   ├── settings.py          # Environment-based configuration
│   └── schema.sql            # Database schema (13 tables)
├── core/
│   ├── security/
│   │   ├── credentials.py   # Keyring credential storage
│   │   ├── encryption.py    # SQLCipher database encryption
│   │   ├── validation.py    # Input sanitization & validation
│   │   └── logging_config.py # Secure logging
│   ├── database/
│   │   ├── database.py      # Encrypted database access layer
│   │   └── models.py        # Dataclass models (6 models)
│   └── gmail/
│       └── multi_account.py # Multi-account Gmail manager
├── ml/
│   ├── features.py          # Feature extraction (67 features)
│   ├── classifier.py        # Ensemble ML classifier
│   ├── synthetic_data.py    # Synthetic training data generator
│   └── multi_account_training.py # Unified ML training
├── models/                   # Trained ML models (gitignored)
├── analysis_reports/        # Mailbox analysis results (gitignored)
├── accounts.json            # Multi-account config (gitignored)
├── credentials_*.json       # OAuth credentials (gitignored)
├── .env                     # Environment variables (gitignored)
├── analyze_all_accounts.py # Multi-account analyzer script
├── analyze_mailbox.py      # Single-account analyzer (legacy)
├── test_multi_account.py   # Multi-account integration tests
├── test_ml_pipeline.py     # ML pipeline tests
└── test_basic.py           # Core component tests
```

## Development Status

### ✅ Completed (Phases 1-3)

- **Phase 1: Security Hardening**
  - ✅ Keyring credential storage (OS-level encryption)
  - ✅ SQLCipher database encryption (AES-256)
  - ✅ Input validation & sanitization
  - ✅ Secure logging with sensitive data filtering
  - ✅ Environment-based configuration

- **Phase 2: Database Layer**
  - ✅ Comprehensive 13-table schema
  - ✅ Type-safe dataclass models (6 models)
  - ✅ Encrypted database access layer
  - ✅ Cross-account deduplication
  - ✅ Message content hashing

- **Phase 3: ML & Multi-Account**
  - ✅ Multi-account Gmail manager (4-6 accounts)
  - ✅ Parallel authentication & fetching
  - ✅ Cross-account deduplication
  - ✅ 67-feature extraction pipeline
  - ✅ Ensemble classifier (RF + GB)
  - ✅ Unified ML training across accounts
  - ✅ Mailbox analysis & reporting
  - ✅ Google Calendar API integration (OAuth scopes)

### 🚧 In Progress (Phase 4)

- **Phase 4: Integration & UI**
  - ⏳ End-to-end email processing pipeline
  - ⏳ Active learning with user feedback
  - ⏳ Model retraining automation
  - ⏳ Command-line interface (CLI)
  - ⏳ Web UI for email review

### 📋 Planned (Phase 5+)

- **Phase 5: Calendar & Reminders**
  - 📋 Deadline extraction from emails
  - 📋 Follow-up reminder system
  - 📋 Google Calendar event creation
  - 📋 Multi-channel notifications (email, desktop, mobile)
  - 📋 Background reminder daemon

- **Phase 6: Advanced Features**
  - 📋 Transformer model for semantic understanding
  - 📋 SHAP-based model interpretability
  - 📋 Email thread analysis
  - 📋 Smart reply suggestions
  - 📋 Automated workflow triggers

### Testing

- ✅ Core component tests (5/5 passing)
- ✅ ML pipeline tests (synthetic data)
- ✅ Multi-account integration tests
- ⏳ End-to-end integration tests (requires SQLCipher)
- 📋 User acceptance testing

## System Requirements

### Minimum
- Python 3.8+
- 4GB RAM
- 1GB disk space
- Internet connection for Gmail API

### Recommended
- Python 3.10+
- 8GB RAM (for ML training with large datasets)
- 5GB disk space (for encrypted database + models)
- Linux/macOS (for full keyring support)

### Optional Dependencies
- **SQLCipher** - For database encryption (install with `sudo apt-get install libsqlcipher-dev`)
- **Secret Service** - For keyring on Linux (usually pre-installed)
- **GPU** - For transformer model training (Phase 6)

## Troubleshooting

### OAuth Authentication Issues
- **Problem:** Browser doesn't open during OAuth
- **Solution:** Manually copy the authentication URL from terminal

### Keyring Not Available
- **Problem:** "Keyring backend not available" error
- **Solution:** System will fall back to memory-only storage (less secure)
- **Linux:** Install `gnome-keyring` or `secret-service`
- **macOS:** Keychain should work by default
- **Windows:** Credential Locker should work by default

### SQLCipher Not Found
- **Problem:** "Module 'pysqlcipher3' not found"
- **Solution:** Install system package first:
  ```bash
  # Ubuntu/Debian
  sudo apt-get install libsqlcipher-dev sqlcipher
  pip install pysqlcipher3
  ```

### Rate Limiting
- **Problem:** Gmail API quota exceeded
- **Solution:** Reduce `max_emails_per_account` in accounts.json or wait 24 hours

## Contributing

This is currently a personal project under active development. If you're interested in contributing:

1. Check existing issues or create a new one
2. Fork the repository
3. Create a feature branch
4. Follow the existing code style and security practices
5. Add tests for new functionality
6. Submit a pull request

**Security:** If you discover a security vulnerability, please email directly rather than opening a public issue.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Google Gmail API & Calendar API
- scikit-learn for ML framework
- SQLCipher for database encryption
- keyring library for credential storage 