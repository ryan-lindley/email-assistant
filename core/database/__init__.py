"""Database module for Email Assistant."""

from .database import EmailDatabase
from .models import (
    EmailRecord,
    CalendarEvent,
    TrainingDataRecord,
    ModelVersion,
    ReminderRecord,
    ProcessingRule,
    SenderStats
)

__all__ = [
    'EmailDatabase',
    'EmailRecord',
    'CalendarEvent',
    'TrainingDataRecord',
    'ModelVersion',
    'ReminderRecord',
    'ProcessingRule',
    'SenderStats'
]
