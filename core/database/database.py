"""
Encrypted database access layer for Email Assistant.

Provides all database operations with SQLCipher encryption.
"""

import json
import logging
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from contextlib import contextmanager

from ..security.encryption import EncryptionManager
from .models import (
    EmailRecord,
    CalendarEvent,
    TrainingDataRecord,
    ModelVersion,
    ReminderRecord,
    ProcessingRule,
    SenderStats,
    EmailAction
)

logger = logging.getLogger(__name__)


class EmailDatabase:
    """
    Encrypted database access layer using SQLCipher.

    Provides high-level interface for all database operations with
    automatic encryption/decryption.
    """

    def __init__(self, db_path: str, encryption_key: str):
        """
        Initialize database connection.

        Args:
            db_path: Path to database file
            encryption_key: Encryption key for SQLCipher
        """
        self.db_path = Path(db_path)
        self.encryption_key = encryption_key
        self.connection = None

        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Connect and initialize
        self._connect()
        self._initialize_schema()

    def _connect(self):
        """Establish encrypted database connection."""
        try:
            self.connection = EncryptionManager.connect_encrypted_db(
                str(self.db_path),
                self.encryption_key
            )
            logger.info(f"Connected to encrypted database: {self.db_path}")

        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def _initialize_schema(self):
        """Initialize database schema if needed."""
        try:
            # Check if schema exists
            cursor = self.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='system_metadata'"
            )

            if cursor.fetchone() is None:
                # Schema doesn't exist, initialize it
                logger.info("Initializing database schema")
                self._create_schema()
            else:
                logger.debug("Database schema already exists")

        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}")
            raise

    def _create_schema(self):
        """Create database schema from SQL file."""
        try:
            schema_path = Path(__file__).parent.parent.parent / 'config' / 'schema.sql'

            with open(schema_path, 'r') as f:
                schema_sql = f.read()

            self.connection.executescript(schema_sql)
            self.connection.commit()

            logger.info("Database schema created successfully")

        except Exception as e:
            logger.error(f"Failed to create schema: {e}")
            raise

    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        try:
            yield self.connection
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Transaction failed, rolling back: {e}")
            raise

    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")

    # ===== EMAIL OPERATIONS =====

    def save_email(self, email: EmailRecord) -> int:
        """
        Save email to database.

        Args:
            email: EmailRecord to save

        Returns:
            Database ID of saved email
        """
        try:
            with self.transaction() as conn:
                cursor = conn.execute("""
                    INSERT OR REPLACE INTO emails (
                        message_id, thread_id, sender, recipients, subject,
                        date_received, date_processed, body_text, body_html,
                        headers, labels, classification_priority, classification_category,
                        confidence_score, is_uncertain, user_priority, user_category,
                        feedback_date, is_processed, is_archived, needs_review, gmail_labels
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    email.message_id,
                    email.thread_id,
                    email.sender,
                    json.dumps(email.recipients),
                    email.subject,
                    email.date_received,
                    email.date_processed or datetime.now(),
                    email.body_text,
                    email.body_html,
                    json.dumps(email.headers) if email.headers else None,
                    json.dumps(email.labels) if email.labels else None,
                    email.classification_priority,
                    email.classification_category,
                    email.confidence_score,
                    email.is_uncertain,
                    email.user_priority,
                    email.user_category,
                    email.feedback_date,
                    email.is_processed,
                    email.is_archived,
                    email.needs_review,
                    json.dumps(email.gmail_labels) if email.gmail_labels else None
                ))

                email_id = cursor.lastrowid

                # Update sender stats
                self._update_sender_stats(email.sender, email.date_received)

                logger.debug(f"Saved email: {email.message_id}")
                return email_id

        except Exception as e:
            logger.error(f"Failed to save email {email.message_id}: {e}")
            raise

    def get_email(self, email_id: int) -> Optional[EmailRecord]:
        """Get email by database ID."""
        try:
            cursor = self.connection.execute(
                "SELECT * FROM emails WHERE id = ?",
                (email_id,)
            )
            row = cursor.fetchone()

            if row:
                return self._row_to_email(row)
            return None

        except Exception as e:
            logger.error(f"Failed to get email {email_id}: {e}")
            return None

    def get_email_by_message_id(self, message_id: str) -> Optional[EmailRecord]:
        """Get email by Gmail message ID."""
        try:
            cursor = self.connection.execute(
                "SELECT * FROM emails WHERE message_id = ?",
                (message_id,)
            )
            row = cursor.fetchone()

            if row:
                return self._row_to_email(row)
            return None

        except Exception as e:
            logger.error(f"Failed to get email by message_id {message_id}: {e}")
            return None

    def get_unprocessed_emails(self, limit: int = 100) -> List[EmailRecord]:
        """Get emails that haven't been processed yet."""
        try:
            cursor = self.connection.execute("""
                SELECT * FROM emails
                WHERE is_processed = 0
                ORDER BY date_received DESC
                LIMIT ?
            """, (limit,))

            return [self._row_to_email(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Failed to get unprocessed emails: {e}")
            return []

    def get_emails_for_review(self, limit: int = 50) -> List[EmailRecord]:
        """Get uncertain emails flagged for user review."""
        try:
            cursor = self.connection.execute("""
                SELECT * FROM emails
                WHERE needs_review = 1 AND is_archived = 0
                ORDER BY date_received DESC
                LIMIT ?
            """, (limit,))

            return [self._row_to_email(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Failed to get emails for review: {e}")
            return []

    def update_classification(
        self,
        email_id: int,
        priority: str,
        category: str,
        confidence: float,
        is_uncertain: bool
    ) -> bool:
        """Update ML classification for an email."""
        try:
            with self.transaction() as conn:
                conn.execute("""
                    UPDATE emails
                    SET classification_priority = ?,
                        classification_category = ?,
                        confidence_score = ?,
                        is_uncertain = ?,
                        needs_review = ?,
                        is_processed = 1,
                        date_processed = ?
                    WHERE id = ?
                """, (
                    priority, category, confidence, is_uncertain,
                    is_uncertain, datetime.now(), email_id
                ))

            logger.debug(f"Updated classification for email {email_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update classification for {email_id}: {e}")
            return False

    def update_user_feedback(
        self,
        email_id: int,
        user_priority: str,
        user_category: Optional[str] = None
    ) -> bool:
        """Store user's correction for ML training."""
        try:
            with self.transaction() as conn:
                conn.execute("""
                    UPDATE emails
                    SET user_priority = ?,
                        user_category = ?,
                        feedback_date = ?,
                        needs_review = 0
                    WHERE id = ?
                """, (user_priority, user_category, datetime.now(), email_id))

            logger.info(f"Updated user feedback for email {email_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update user feedback for {email_id}: {e}")
            return False

    def is_duplicate(self, message_id: str, content_hash: str) -> bool:
        """Check if email already exists (deduplication)."""
        try:
            cursor = self.connection.execute(
                "SELECT 1 FROM message_hashes WHERE content_hash = ? LIMIT 1",
                (content_hash,)
            )
            return cursor.fetchone() is not None

        except Exception as e:
            logger.error(f"Failed to check duplicate: {e}")
            return False

    def store_message_hash(self, message_id: str, content: str):
        """Store content hash for deduplication."""
        try:
            content_hash = hashlib.sha256(content.encode()).hexdigest()

            with self.transaction() as conn:
                conn.execute("""
                    INSERT OR IGNORE INTO message_hashes (message_id, content_hash)
                    VALUES (?, ?)
                """, (message_id, content_hash))

            logger.debug(f"Stored message hash for {message_id}")

        except Exception as e:
            logger.error(f"Failed to store message hash: {e}")

    # ===== CALENDAR OPERATIONS =====

    def save_calendar_event(self, event: CalendarEvent) -> int:
        """Save calendar event to database."""
        try:
            with self.transaction() as conn:
                cursor = conn.execute("""
                    INSERT INTO calendar_events (
                        email_id, event_type, title, description,
                        start_datetime, end_datetime, location, due_date,
                        priority, gcal_event_id, is_synced, sync_approved,
                        reminder_status, next_reminder_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.email_id, event.event_type, event.title,
                    event.description, event.start_datetime, event.end_datetime,
                    event.location, event.due_date, event.priority,
                    event.gcal_event_id, event.is_synced, event.sync_approved,
                    event.reminder_status, event.next_reminder_at
                ))

                event_id = cursor.lastrowid
                logger.info(f"Saved calendar event: {event.title}")
                return event_id

        except Exception as e:
            logger.error(f"Failed to save calendar event: {e}")
            raise

    def get_pending_calendar_events(self) -> List[CalendarEvent]:
        """Get calendar events pending approval."""
        try:
            cursor = self.connection.execute("""
                SELECT * FROM calendar_events
                WHERE sync_approved = 0 AND is_synced = 0
                ORDER BY due_date ASC
            """)

            return [self._row_to_calendar_event(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Failed to get pending calendar events: {e}")
            return []

    def get_due_reminders(self, before: Optional[datetime] = None) -> List[Tuple[CalendarEvent, List[ReminderRecord]]]:
        """Get calendar events with due reminders."""
        try:
            if before is None:
                before = datetime.now()

            cursor = self.connection.execute("""
                SELECT * FROM calendar_events
                WHERE reminder_status IN ('pending', 'snoozed')
                    AND next_reminder_at <= ?
                ORDER BY next_reminder_at ASC
            """, (before,))

            events_with_reminders = []
            for row in cursor.fetchall():
                event = self._row_to_calendar_event(row)
                reminders = self.get_reminders_for_event(event.id)
                events_with_reminders.append((event, reminders))

            return events_with_reminders

        except Exception as e:
            logger.error(f"Failed to get due reminders: {e}")
            return []

    # ===== TRAINING DATA OPERATIONS =====

    def save_training_data(self, training_data: TrainingDataRecord) -> int:
        """Save training data for ML model."""
        try:
            with self.transaction() as conn:
                cursor = conn.execute("""
                    INSERT INTO training_data (
                        email_id, features, label_priority, label_category,
                        confidence, is_validated
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    training_data.email_id,
                    json.dumps(training_data.features),
                    training_data.label_priority,
                    training_data.label_category,
                    training_data.confidence,
                    training_data.is_validated
                ))

                return cursor.lastrowid

        except Exception as e:
            logger.error(f"Failed to save training data: {e}")
            raise

    def get_validated_training_data(self, limit: Optional[int] = None) -> List[Tuple[Dict, str, Optional[str]]]:
        """Get validated training data for model training."""
        try:
            query = """
                SELECT features, label_priority, label_category
                FROM training_data
                WHERE is_validated = 1
                ORDER BY created_at DESC
            """

            if limit:
                query += f" LIMIT {limit}"

            cursor = self.connection.execute(query)

            return [
                (json.loads(row[0]), row[1], row[2])
                for row in cursor.fetchall()
            ]

        except Exception as e:
            logger.error(f"Failed to get validated training data: {e}")
            return []

    # ===== HELPER METHODS =====

    def _row_to_email(self, row) -> EmailRecord:
        """Convert database row to EmailRecord."""
        return EmailRecord(
            id=row[0],
            message_id=row[1],
            thread_id=row[2],
            sender=row[3],
            recipients=json.loads(row[4]) if row[4] else [],
            subject=row[5],
            date_received=datetime.fromisoformat(row[6]) if isinstance(row[6], str) else row[6],
            date_processed=datetime.fromisoformat(row[7]) if isinstance(row[7], str) else row[7],
            body_text=row[8],
            body_html=row[9],
            headers=json.loads(row[10]) if row[10] else None,
            labels=json.loads(row[11]) if row[11] else None,
            classification_priority=row[12],
            classification_category=row[13],
            confidence_score=row[14],
            is_uncertain=bool(row[15]),
            user_priority=row[16],
            user_category=row[17],
            feedback_date=datetime.fromisoformat(row[18]) if isinstance(row[18], str) and row[18] else None,
            is_processed=bool(row[19]),
            is_archived=bool(row[20]),
            needs_review=bool(row[21]),
            gmail_labels=json.loads(row[22]) if row[22] else None
        )

    def _row_to_calendar_event(self, row) -> CalendarEvent:
        """Convert database row to CalendarEvent."""
        return CalendarEvent(
            id=row[0],
            email_id=row[1],
            event_type=row[2],
            title=row[3],
            description=row[4],
            start_datetime=datetime.fromisoformat(row[5]) if row[5] else None,
            end_datetime=datetime.fromisoformat(row[6]) if row[6] else None,
            location=row[7],
            due_date=datetime.fromisoformat(row[8]) if row[8] else None,
            priority=row[9],
            gcal_event_id=row[10],
            is_synced=bool(row[11]),
            sync_approved=bool(row[12]),
            reminder_status=row[13],
            next_reminder_at=datetime.fromisoformat(row[14]) if row[14] else None,
            created_at=datetime.fromisoformat(row[15]) if row[15] else None,
            updated_at=datetime.fromisoformat(row[16]) if row[16] else None
        )

    def _update_sender_stats(self, sender_email: str, last_seen: datetime):
        """Update statistics for a sender."""
        try:
            sender_domain = sender_email.split('@')[1] if '@' in sender_email else ''

            with self.transaction() as conn:
                conn.execute("""
                    INSERT INTO sender_stats (sender_email, sender_domain, total_emails, last_seen)
                    VALUES (?, ?, 1, ?)
                    ON CONFLICT(sender_email) DO UPDATE SET
                        total_emails = total_emails + 1,
                        last_seen = ?
                """, (sender_email, sender_domain, last_seen, last_seen))

        except Exception as e:
            logger.error(f"Failed to update sender stats: {e}")

    def get_reminders_for_event(self, event_id: int) -> List[ReminderRecord]:
        """Get all reminders for a calendar event."""
        try:
            cursor = self.connection.execute(
                "SELECT * FROM reminders WHERE event_id = ? ORDER BY reminder_time ASC",
                (event_id,)
            )

            reminders = []
            for row in cursor.fetchall():
                reminders.append(ReminderRecord(
                    id=row[0],
                    event_id=row[1],
                    reminder_time=datetime.fromisoformat(row[2]) if isinstance(row[2], str) else row[2],
                    reminder_type=row[3],
                    sent_at=datetime.fromisoformat(row[4]) if row[4] and isinstance(row[4], str) else row[4],
                    user_action=row[5],
                    snooze_until=datetime.fromisoformat(row[6]) if row[6] and isinstance(row[6], str) else row[6],
                    notes=row[7]
                ))

            return reminders

        except Exception as e:
            logger.error(f"Failed to get reminders for event {event_id}: {e}")
            return []
