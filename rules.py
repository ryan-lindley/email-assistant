import os
import shutil

# Define the rules content
rules = {
    "general-rules.mdc": """# General Rules for the Email Management Agent
Applies to: **/*.py

- Use Python 3.11+ syntax and features.
- Follow PEP 8 style guidelines (e.g., 4-space indentation, snake_case for variables).
- Include type hints for all function parameters and return types.
- Write concise docstrings for every function and class in Google style format.
- Handle exceptions explicitly with try-except blocks and log errors using the `logging` module.
- Prefer modular code: break functionality into small, reusable functions or classes.
- Use environment variables (via `python-dotenv`) for sensitive data like API keys or credentials.
""",
    "email-handling.mdc": """# Email Handling Rules
Applies to: **/email_*.py, **/imap_*.py, **/api_*.py

- Use the Gmail API (`google-auth`, `google-api-python-client`) for Google accounts and ProtonMail Bridge or API for Proton.me accounts.
- Implement OAuth2 authentication for Gmail and secure credential storage for ProtonMail.
- Fetch emails in batches (e.g., 50 at a time) to optimize performance.
- Include a function to classify emails as "human-generated" or "bot-generated" using headers (e.g., "Precedence: bulk") and content analysis.
- Flag important emails by checking sender whitelists, keywords (e.g., "urgent", "meeting"), or reply chains.
- For spam or bot emails (e.g., containing "loan", "mortgage", "credit"), attempt to unsubscribe using "List-Unsubscribe" headers or links, then delete them.
- Store processed email metadata (e.g., message ID, action taken) in a SQLite database to avoid reprocessing.
""",
    "nlp-analysis.mdc": """# NLP Analysis Rules
Applies to: **/nlp_*.py, **/analysis_*.py

- Use `spacy` or `transformers` (e.g., a lightweight BERT model) for natural language processing to detect email importance.
- Train or fine-tune a model to classify emails as "important" based on user-provided examples (e.g., "meeting with boss" vs. "newsletter").
- Extract a brief summary (1-2 sentences) of important emails using text summarization techniques.
- Avoid heavy NLP models unless explicitly requested; prioritize speed for real-time processing.
- Cache NLP results in the database to reduce redundant processing.
""",
    "notification-system.mdc": """# Notification System Rules
Applies to: **/notify_*.py

- Implement notifications via desktop alerts (e.g., `plyer`) and optionally SMS/email (e.g., Twilio or SMTP).
- Format notifications as: "From: [sender] | Subject: [subject] | Summary: [summary]".
- Limit notifications to important emails only, as determined by NLP or sender rules.
- Include a cooldown period (e.g., 5 minutes) to avoid spamming the user with rapid-fire alerts.
""",
    "calendar-integration.mdc": """# Calendar Integration Rules
Applies to: **/calendar_*.py

- Use Google Calendar API for Gmail accounts and CalDAV or a similar protocol for Proton.me calendars.
- Fetch events daily and set reminders for upcoming events (e.g., 15 minutes before).
- Send reminders via the same notification system as email alerts.
- Store calendar event IDs in the database to track processed reminders.
""",
    "database.mdc": """# Database Rules
Applies to: **/db_*.py, **/storage_*.py

- Use SQLite as the lightweight database for storing email metadata, preferences, and calendar events.
- Create tables with clear schemas (e.g., `emails: id, message_id, sender, action, timestamp`).
- Use SQLAlchemy or `sqlite3` with parameterized queries to prevent SQL injection.
- Include a cleanup routine to remove records older than 30 days.
"""
}

# Create .cursor/rules directory
os.makedirs(".cursor/rules", exist_ok=True)

# Write each rule file
for filename, content in rules.items():
    with open(f".cursor/rules/{filename}", "w") as f:
        f.write(content)

# Create a ZIP file
shutil.make_archive("cursor_rules", "zip", ".cursor")

print("Created cursor_rules.zip in the current directory!")