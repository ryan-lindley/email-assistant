# Email Management Agent

An intelligent email management system that can analyze, classify, and manage emails from multiple providers (Gmail, ProtonMail) using machine learning and pattern recognition.

## Features

- Multi-provider support (Gmail, ProtonMail)
- Bot-generated email detection
- Historical email analysis
- Email classification with confidence scores
- Email actions (read, move, delete, forward, reply, star)
- Pattern-based learning and weight management
- Support for multiple test accounts

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/email-agent.git
cd email-agent
```

2. Create and activate a virtual environment:
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up credentials:
   - For Gmail:
     1. Go to [Google Cloud Console](https://console.cloud.google.com/)
     2. Create a project and enable Gmail API
     3. Create OAuth credentials for each test user
     4. Save credentials as `credentials_user1.json`, `credentials_user2.json`, etc.
   
   - For ProtonMail:
     1. Create a developer account at [ProtonMail](https://account.proton.me/signup?plan=developer)
     2. Generate API credentials
     3. Save as `protonmail_credentials.json`

5. Configure accounts:
   - Create `account_config.json` with your account details:
   ```json
   {
       "accounts": [
           {
               "name": "Gmail Test User 1",
               "provider": "gmail",
               "credentials_path": "credentials_user1.json"
           },
           {
               "name": "Gmail Test User 2",
               "provider": "gmail",
               "credentials_path": "credentials_user2.json"
           },
           {
               "name": "ProtonMail Test User",
               "provider": "protonmail",
               "credentials_path": "protonmail_credentials.json"
           }
       ]
   }
   ```

## Usage

1. Run the test script for all configured accounts:
```bash
python test_multiple_accounts.py
```

2. For individual account testing:
```bash
python test_gmail_setup.py  # For Gmail
```

## Security

- All credential files are ignored by Git
- Each account uses separate credential files
- Bot detection weights are saved per account
- Sensitive data is never logged

## Project Structure

```
email-agent/
├── .gitignore
├── README.md
├── requirements.txt
├── account_config.json
├── email_handler.py
├── protonmail_handler.py
├── test_gmail_setup.py
└── test_multiple_accounts.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 