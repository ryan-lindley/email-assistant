"""
Configuration management for Email Assistant.

Loads settings from environment variables with sensible defaults.
Ensures all paths exist and are properly configured.
"""

import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize settings from environment variables.

        Args:
            env_file: Path to .env file. If None, looks for .env in current directory.
        """
        # Load environment variables
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()

        self._initialize_settings()
        self._ensure_directories_exist()

    def _initialize_settings(self):
        """Load all settings from environment variables."""

        # Application directories
        self.app_data_dir = Path(
            os.getenv('APP_DATA_DIR',
                     str(Path.home() / '.local/share/email-assistant'))
        )
        self.app_config_dir = Path(
            os.getenv('APP_CONFIG_DIR',
                     str(Path.home() / '.config/email-assistant'))
        )

        # Gmail configuration
        self.gmail_credentials_path = Path(
            os.getenv('GMAIL_CREDENTIALS_PATH',
                     str(self.app_config_dir / 'gmail_credentials.json'))
        )
        self.gmail_user_email = os.getenv('GMAIL_USER_EMAIL')

        # ML configuration
        self.ml_confidence_low = float(os.getenv('ML_CONFIDENCE_THRESHOLD_LOW', '0.3'))
        self.ml_confidence_high = float(os.getenv('ML_CONFIDENCE_THRESHOLD_HIGH', '0.7'))
        self.ml_model_path = Path(
            os.getenv('ML_MODEL_PATH',
                     str(self.app_data_dir / 'models'))
        )
        self.ml_retrain_threshold = int(os.getenv('ML_RETRAIN_THRESHOLD', '50'))

        # Database configuration
        self.database_path = Path(
            os.getenv('DATABASE_PATH',
                     str(self.app_data_dir / 'email_data.db'))
        )
        self.database_encryption_key_name = os.getenv(
            'DATABASE_ENCRYPTION_KEY_NAME',
            'email-assistant-db-key'
        )

        # Calendar configuration
        reminder_intervals_str = os.getenv('CALENDAR_REMINDER_INTERVALS', '168,48,24,3')
        self.calendar_reminder_intervals = [
            int(x.strip()) for x in reminder_intervals_str.split(',')
        ]
        self.calendar_default_snooze_hours = int(
            os.getenv('CALENDAR_DEFAULT_SNOOZE_HOURS', '4')
        )
        self.calendar_sync_enabled = os.getenv('CALENDAR_SYNC_ENABLED', 'false').lower() == 'true'
        self.calendar_timezone = os.getenv('CALENDAR_TIMEZONE', 'America/New_York')

        # Notification configuration
        self.enable_desktop_notifications = os.getenv(
            'ENABLE_DESKTOP_NOTIFICATIONS', 'true'
        ).lower() == 'true'
        self.enable_email_reminders = os.getenv(
            'ENABLE_EMAIL_REMINDERS', 'true'
        ).lower() == 'true'
        self.reminder_email_address = os.getenv('REMINDER_EMAIL_ADDRESS')

        # Logging configuration
        self.log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        self.log_file = Path(
            os.getenv('LOG_FILE',
                     str(self.app_data_dir / 'email_assistant.log'))
        )
        self.log_sensitive_data = os.getenv('LOG_SENSITIVE_DATA', 'false').lower() == 'true'

    def _ensure_directories_exist(self):
        """Create necessary directories if they don't exist."""
        directories = [
            self.app_data_dir,
            self.app_config_dir,
            self.ml_model_path,
            self.log_file.parent,
            self.database_path.parent,
        ]

        for directory in directories:
            if directory and not directory.exists():
                try:
                    directory.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created directory: {directory}")
                except Exception as e:
                    logger.error(f"Failed to create directory {directory}: {e}")

    def validate(self) -> List[str]:
        """
        Validate configuration and return list of issues.

        Returns:
            List of validation error messages (empty if valid)
        """
        issues = []

        # Check required settings
        if not self.gmail_user_email:
            issues.append("GMAIL_USER_EMAIL not set")

        if not self.gmail_credentials_path.exists():
            issues.append(f"Gmail credentials not found at {self.gmail_credentials_path}")

        # Validate confidence thresholds
        if not 0 <= self.ml_confidence_low <= 1:
            issues.append(f"ML_CONFIDENCE_THRESHOLD_LOW must be between 0 and 1, got {self.ml_confidence_low}")

        if not 0 <= self.ml_confidence_high <= 1:
            issues.append(f"ML_CONFIDENCE_THRESHOLD_HIGH must be between 0 and 1, got {self.ml_confidence_high}")

        if self.ml_confidence_low >= self.ml_confidence_high:
            issues.append("ML_CONFIDENCE_THRESHOLD_LOW must be less than ML_CONFIDENCE_THRESHOLD_HIGH")

        # Validate reminder intervals
        if not self.calendar_reminder_intervals:
            issues.append("CALENDAR_REMINDER_INTERVALS cannot be empty")

        for interval in self.calendar_reminder_intervals:
            if interval <= 0:
                issues.append(f"Calendar reminder interval must be positive, got {interval}")

        return issues

    def __repr__(self) -> str:
        """String representation of settings (safe for logging)."""
        return (
            f"Settings(\n"
            f"  app_data_dir={self.app_data_dir},\n"
            f"  gmail_user={self.gmail_user_email},\n"
            f"  ml_confidence_range=[{self.ml_confidence_low}, {self.ml_confidence_high}],\n"
            f"  calendar_sync_enabled={self.calendar_sync_enabled},\n"
            f"  log_level={self.log_level}\n"
            f")"
        )


# Global settings instance
_settings: Optional[Settings] = None


def get_settings(env_file: Optional[str] = None) -> Settings:
    """
    Get the global settings instance.

    Args:
        env_file: Path to .env file (only used on first call)

    Returns:
        Settings instance
    """
    global _settings

    if _settings is None:
        _settings = Settings(env_file)

    return _settings


def reload_settings(env_file: Optional[str] = None):
    """
    Reload settings from environment variables.

    Args:
        env_file: Path to .env file
    """
    global _settings
    _settings = Settings(env_file)
