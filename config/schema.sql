-- Email Assistant Database Schema
-- SQLCipher encrypted database

-- Core email storage
CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT UNIQUE NOT NULL,
    thread_id TEXT,
    sender TEXT NOT NULL,
    recipients TEXT NOT NULL,  -- JSON array
    subject TEXT,
    date_received TIMESTAMP NOT NULL,
    date_processed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    body_text TEXT,
    body_html TEXT,
    headers TEXT,  -- JSON object
    labels TEXT,  -- JSON array

    -- ML Classification Results
    classification_priority TEXT,
    classification_category TEXT,
    confidence_score REAL,
    is_uncertain BOOLEAN DEFAULT 0,

    -- User Feedback
    user_priority TEXT,
    user_category TEXT,
    feedback_date TIMESTAMP,

    -- Processing Status
    is_processed BOOLEAN DEFAULT 0,
    is_archived BOOLEAN DEFAULT 0,
    needs_review BOOLEAN DEFAULT 0,

    -- Gmail specific
    gmail_labels TEXT  -- JSON array
);

CREATE INDEX IF NOT EXISTS idx_emails_message_id ON emails(message_id);
CREATE INDEX IF NOT EXISTS idx_emails_date ON emails(date_received DESC);
CREATE INDEX IF NOT EXISTS idx_emails_processed ON emails(is_processed, needs_review);
CREATE INDEX IF NOT EXISTS idx_emails_classification ON emails(classification_priority, classification_category);
CREATE INDEX IF NOT EXISTS idx_emails_sender ON emails(sender);
CREATE INDEX IF NOT EXISTS idx_emails_thread ON emails(thread_id);

-- Gmail-specific raw message storage
CREATE TABLE IF NOT EXISTS gmail_messages (
    message_id TEXT PRIMARY KEY,
    raw_message BLOB,
    gmail_internal_date TIMESTAMP,
    last_fetched TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT 0,
    FOREIGN KEY (message_id) REFERENCES emails(message_id) ON DELETE CASCADE
);

-- Training data for ML
CREATE TABLE IF NOT EXISTS training_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id INTEGER NOT NULL,
    features TEXT NOT NULL,  -- JSON of extracted features
    label_priority TEXT NOT NULL,
    label_category TEXT,
    confidence REAL,
    is_validated BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_training_validated ON training_data(is_validated);
CREATE INDEX IF NOT EXISTS idx_training_created ON training_data(created_at DESC);

-- ML Model versions
CREATE TABLE IF NOT EXISTS model_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT NOT NULL UNIQUE,
    model_type TEXT NOT NULL,
    model_path TEXT NOT NULL,
    training_samples INTEGER,
    accuracy REAL,
    precision_by_class TEXT,  -- JSON
    recall_by_class TEXT,  -- JSON
    f1_by_class TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_model_active ON model_versions(is_active);
CREATE INDEX IF NOT EXISTS idx_model_created ON model_versions(created_at DESC);

-- Feature importance (for interpretability)
CREATE TABLE IF NOT EXISTS feature_importance (
    model_version_id INTEGER NOT NULL,
    feature_name TEXT NOT NULL,
    importance_score REAL NOT NULL,
    FOREIGN KEY (model_version_id) REFERENCES model_versions(id) ON DELETE CASCADE,
    PRIMARY KEY (model_version_id, feature_name)
);

-- Calendar events extracted from emails
CREATE TABLE IF NOT EXISTS calendar_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,  -- 'deadline', 'meeting', 'followup', 'reservation', 'flight'
    title TEXT NOT NULL,
    description TEXT,
    start_datetime TIMESTAMP,
    end_datetime TIMESTAMP,
    location TEXT,

    -- Deadline/Followup specific
    due_date TIMESTAMP,
    priority TEXT,

    -- Google Calendar integration
    gcal_event_id TEXT,
    is_synced BOOLEAN DEFAULT 0,
    sync_approved BOOLEAN DEFAULT 0,

    -- Reminder system
    reminder_status TEXT DEFAULT 'pending',  -- 'pending', 'sent', 'snoozed', 'completed', 'dismissed'
    next_reminder_at TIMESTAMP,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_calendar_email ON calendar_events(email_id);
CREATE INDEX IF NOT EXISTS idx_calendar_reminders ON calendar_events(reminder_status, next_reminder_at);
CREATE INDEX IF NOT EXISTS idx_calendar_due ON calendar_events(due_date);
CREATE INDEX IF NOT EXISTS idx_calendar_type ON calendar_events(event_type);
CREATE INDEX IF NOT EXISTS idx_calendar_sync ON calendar_events(is_synced, sync_approved);

-- Reminder history
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    reminder_time TIMESTAMP NOT NULL,
    reminder_type TEXT,  -- 'desktop', 'email', 'cli'
    sent_at TIMESTAMP,
    user_action TEXT,  -- 'dismissed', 'snoozed', 'completed', 'pending'
    snooze_until TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (event_id) REFERENCES calendar_events(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_reminders_event ON reminders(event_id);
CREATE INDEX IF NOT EXISTS idx_reminders_sent ON reminders(sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_reminders_snooze ON reminders(snooze_until);

-- User preferences
CREATE TABLE IF NOT EXISTS user_preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    value_type TEXT DEFAULT 'string',  -- 'string', 'int', 'float', 'bool', 'json'
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Email processing rules (user-defined)
CREATE TABLE IF NOT EXISTS processing_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    condition_type TEXT NOT NULL,  -- 'sender', 'subject_contains', 'category', 'domain', etc.
    condition_value TEXT NOT NULL,
    action_type TEXT NOT NULL,  -- 'set_priority', 'auto_archive', 'create_task', 'label', etc.
    action_value TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    priority INTEGER DEFAULT 0,  -- Rule execution order (lower = higher priority)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rules_active ON processing_rules(is_active, priority);

-- Message deduplication tracking
CREATE TABLE IF NOT EXISTS message_hashes (
    message_id TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES emails(message_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_content_hash ON message_hashes(content_hash);

-- Sender patterns and statistics
CREATE TABLE IF NOT EXISTS sender_stats (
    sender_email TEXT PRIMARY KEY,
    sender_domain TEXT,
    total_emails INTEGER DEFAULT 0,
    read_count INTEGER DEFAULT 0,
    reply_count INTEGER DEFAULT 0,
    archive_count INTEGER DEFAULT 0,
    delete_count INTEGER DEFAULT 0,
    avg_user_priority REAL,  -- Average priority assigned by user
    is_automated BOOLEAN DEFAULT 0,  -- Detected as automated sender
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sender_domain ON sender_stats(sender_domain);
CREATE INDEX IF NOT EXISTS idx_sender_automated ON sender_stats(is_automated);
CREATE INDEX IF NOT EXISTS idx_sender_last_seen ON sender_stats(last_seen DESC);

-- Email action history (for behavioral analysis)
CREATE TABLE IF NOT EXISTS email_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id INTEGER NOT NULL,
    action_type TEXT NOT NULL,  -- 'read', 'reply', 'forward', 'archive', 'delete', 'star', 'label'
    action_value TEXT,  -- Additional action data (label name, forward recipient, etc.)
    action_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_actions_email ON email_actions(email_id);
CREATE INDEX IF NOT EXISTS idx_actions_type ON email_actions(action_type);
CREATE INDEX IF NOT EXISTS idx_actions_timestamp ON email_actions(action_timestamp DESC);

-- System metadata
CREATE TABLE IF NOT EXISTS system_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert initial system metadata
INSERT OR IGNORE INTO system_metadata (key, value) VALUES ('schema_version', '1.0.0');
INSERT OR IGNORE INTO system_metadata (key, value) VALUES ('created_at', datetime('now'));
INSERT OR IGNORE INTO system_metadata (key, value) VALUES ('last_migration', datetime('now'));

-- Insert default user preferences
INSERT OR IGNORE INTO user_preferences (key, value, value_type, description)
VALUES ('confidence_threshold_low', '0.3', 'float', 'Lower confidence threshold for uncertain emails');

INSERT OR IGNORE INTO user_preferences (key, value, value_type, description)
VALUES ('confidence_threshold_high', '0.7', 'float', 'Upper confidence threshold for certain emails');

INSERT OR IGNORE INTO user_preferences (key, value, value_type, description)
VALUES ('auto_sync_calendar', 'false', 'bool', 'Automatically sync events to Google Calendar');

INSERT OR IGNORE INTO user_preferences (key, value, value_type, description)
VALUES ('reminder_intervals', '[168, 48, 24, 3]', 'json', 'Reminder intervals in hours');

INSERT OR IGNORE INTO user_preferences (key, value, value_type, description)
VALUES ('default_snooze_hours', '4', 'int', 'Default snooze duration in hours');
