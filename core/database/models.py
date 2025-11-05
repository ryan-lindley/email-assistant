"""
Database models for Email Assistant.

Dataclasses representing database entities with type hints.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class EmailRecord:
    """Database model for emails."""

    # Required fields
    message_id: str
    sender: str
    recipients: List[str]
    subject: str
    date_received: datetime

    # Optional fields
    id: Optional[int] = None
    thread_id: Optional[str] = None
    date_processed: Optional[datetime] = None
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    labels: Optional[List[str]] = None

    # ML Classification
    classification_priority: Optional[str] = None
    classification_category: Optional[str] = None
    confidence_score: Optional[float] = None
    is_uncertain: bool = False

    # User Feedback
    user_priority: Optional[str] = None
    user_category: Optional[str] = None
    feedback_date: Optional[datetime] = None

    # Processing Status
    is_processed: bool = False
    is_archived: bool = False
    needs_review: bool = False

    # Gmail specific
    gmail_labels: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'id': self.id,
            'message_id': self.message_id,
            'thread_id': self.thread_id,
            'sender': self.sender,
            'recipients': self.recipients,
            'subject': self.subject,
            'date_received': self.date_received,
            'date_processed': self.date_processed,
            'body_text': self.body_text,
            'body_html': self.body_html,
            'headers': self.headers,
            'labels': self.labels,
            'classification_priority': self.classification_priority,
            'classification_category': self.classification_category,
            'confidence_score': self.confidence_score,
            'is_uncertain': self.is_uncertain,
            'user_priority': self.user_priority,
            'user_category': self.user_category,
            'feedback_date': self.feedback_date,
            'is_processed': self.is_processed,
            'is_archived': self.is_archived,
            'needs_review': self.needs_review,
            'gmail_labels': self.gmail_labels
        }


@dataclass
class CalendarEvent:
    """Database model for calendar events."""

    # Required fields
    email_id: int
    event_type: str  # 'deadline', 'meeting', 'followup', etc.
    title: str

    # Optional fields
    id: Optional[int] = None
    description: Optional[str] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    location: Optional[str] = None

    # Deadline specific
    due_date: Optional[datetime] = None
    priority: Optional[str] = None

    # Google Calendar
    gcal_event_id: Optional[str] = None
    is_synced: bool = False
    sync_approved: bool = False

    # Reminder system
    reminder_status: str = 'pending'
    next_reminder_at: Optional[datetime] = None

    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'id': self.id,
            'email_id': self.email_id,
            'event_type': self.event_type,
            'title': self.title,
            'description': self.description,
            'start_datetime': self.start_datetime,
            'end_datetime': self.end_datetime,
            'location': self.location,
            'due_date': self.due_date,
            'priority': self.priority,
            'gcal_event_id': self.gcal_event_id,
            'is_synced': self.is_synced,
            'sync_approved': self.sync_approved,
            'reminder_status': self.reminder_status,
            'next_reminder_at': self.next_reminder_at,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


@dataclass
class TrainingDataRecord:
    """Database model for ML training data."""

    email_id: int
    features: Dict[str, Any]
    label_priority: str
    label_category: Optional[str] = None
    confidence: Optional[float] = None
    is_validated: bool = False
    id: Optional[int] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'id': self.id,
            'email_id': self.email_id,
            'features': self.features,
            'label_priority': self.label_priority,
            'label_category': self.label_category,
            'confidence': self.confidence,
            'is_validated': self.is_validated,
            'created_at': self.created_at
        }


@dataclass
class ModelVersion:
    """Database model for ML model versions."""

    version: str
    model_type: str
    model_path: str
    training_samples: int
    accuracy: float
    precision_by_class: Dict[str, float]
    recall_by_class: Dict[str, float]
    f1_by_class: Dict[str, float]
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    is_active: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'id': self.id,
            'version': self.version,
            'model_type': self.model_type,
            'model_path': self.model_path,
            'training_samples': self.training_samples,
            'accuracy': self.accuracy,
            'precision_by_class': self.precision_by_class,
            'recall_by_class': self.recall_by_class,
            'f1_by_class': self.f1_by_class,
            'created_at': self.created_at,
            'is_active': self.is_active
        }


@dataclass
class ReminderRecord:
    """Database model for reminders."""

    event_id: int
    reminder_time: datetime
    reminder_type: str  # 'desktop', 'email', 'cli'
    id: Optional[int] = None
    sent_at: Optional[datetime] = None
    user_action: Optional[str] = None
    snooze_until: Optional[datetime] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'id': self.id,
            'event_id': self.event_id,
            'reminder_time': self.reminder_time,
            'reminder_type': self.reminder_type,
            'sent_at': self.sent_at,
            'user_action': self.user_action,
            'snooze_until': self.snooze_until,
            'notes': self.notes
        }


@dataclass
class ProcessingRule:
    """Database model for email processing rules."""

    name: str
    condition_type: str
    condition_value: str
    action_type: str
    action_value: str
    id: Optional[int] = None
    is_active: bool = True
    priority: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'id': self.id,
            'name': self.name,
            'condition_type': self.condition_type,
            'condition_value': self.condition_value,
            'action_type': self.action_type,
            'action_value': self.action_value,
            'is_active': self.is_active,
            'priority': self.priority,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


@dataclass
class SenderStats:
    """Database model for sender statistics."""

    sender_email: str
    sender_domain: str
    total_emails: int = 0
    read_count: int = 0
    reply_count: int = 0
    archive_count: int = 0
    delete_count: int = 0
    avg_user_priority: Optional[float] = None
    is_automated: bool = False
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'sender_email': self.sender_email,
            'sender_domain': self.sender_domain,
            'total_emails': self.total_emails,
            'read_count': self.read_count,
            'reply_count': self.reply_count,
            'archive_count': self.archive_count,
            'delete_count': self.delete_count,
            'avg_user_priority': self.avg_user_priority,
            'is_automated': self.is_automated,
            'first_seen': self.first_seen,
            'last_seen': self.last_seen
        }


@dataclass
class EmailAction:
    """Database model for email actions."""

    email_id: int
    action_type: str
    action_value: Optional[str] = None
    id: Optional[int] = None
    action_timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'id': self.id,
            'email_id': self.email_id,
            'action_type': self.action_type,
            'action_value': self.action_value,
            'action_timestamp': self.action_timestamp
        }
