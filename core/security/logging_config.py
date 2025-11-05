"""
Secure logging configuration.

Prevents sensitive data from being logged while maintaining useful debug information.
"""

import logging
import re
from pathlib import Path
from typing import Optional


class SensitiveDataFilter(logging.Filter):
    """
    Filter sensitive data from log messages.

    Masks:
    - Email addresses (partial masking)
    - OAuth tokens and API keys
    - Long alphanumeric strings (potential tokens)
    - Email bodies (in debug mode)
    """

    # Email pattern
    EMAIL_PATTERN = re.compile(
        r'\b([a-zA-Z0-9._%+-])([a-zA-Z0-9._%+-]*)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b'
    )

    # Token/key pattern (32+ alphanumeric characters)
    TOKEN_PATTERN = re.compile(r'\b[a-zA-Z0-9+/=]{32,}\b')

    # Password/key in parameters
    PARAM_PATTERN = re.compile(
        r'(password|key|token|secret|auth)["\']?\s*[:=]\s*["\']?([^\s"\']+)',
        re.IGNORECASE
    )

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log record to remove sensitive data.

        Args:
            record: Log record to filter

        Returns:
            True (always allow record, but modify message)
        """
        if isinstance(record.msg, str):
            record.msg = self._sanitize(record.msg)

        # Sanitize arguments
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: self._sanitize(str(v)) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    self._sanitize(str(arg)) if isinstance(arg, str) else arg
                    for arg in record.args
                )

        return True

    def _sanitize(self, text: str) -> str:
        """
        Sanitize a string by masking sensitive data.

        Args:
            text: Text to sanitize

        Returns:
            Sanitized text
        """
        # Mask email addresses (keep first char and domain)
        text = self.EMAIL_PATTERN.sub(r'\1***@\3', text)

        # Mask tokens and keys
        text = self.TOKEN_PATTERN.sub('[TOKEN]', text)

        # Mask password/key parameters
        text = self.PARAM_PATTERN.sub(r'\1=***', text)

        return text


class EmailBodyFilter(logging.Filter):
    """
    Filter email body content from logs.

    Only applies in production (when LOG_SENSITIVE_DATA=false).
    """

    BODY_INDICATORS = ['body:', 'content:', 'message:', 'text:']

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Remove email body content from logs.

        Args:
            record: Log record to filter

        Returns:
            True (always allow record, but may modify message)
        """
        if isinstance(record.msg, str):
            msg_lower = record.msg.lower()

            # Check if this looks like it contains email body
            if any(indicator in msg_lower for indicator in self.BODY_INDICATORS):
                # Truncate after indicator
                for indicator in self.BODY_INDICATORS:
                    if indicator in msg_lower:
                        idx = msg_lower.index(indicator)
                        record.msg = record.msg[:idx + len(indicator)] + ' [REDACTED]'
                        break

        return True


def setup_logging(
    log_level: str = 'INFO',
    log_file: Optional[Path] = None,
    log_sensitive_data: bool = False,
    console_output: bool = True
) -> None:
    """
    Configure secure logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (None for no file logging)
        log_sensitive_data: If True, don't filter sensitive data (debug mode)
        console_output: If True, also log to console
    """
    # Create logger
    logger = logging.getLogger('email-assistant')
    logger.setLevel(getattr(logging, log_level.upper()))

    # Clear existing handlers
    logger.handlers.clear()

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(simple_formatter)

        # Add filters for console (always filter sensitive data for console)
        console_handler.addFilter(SensitiveDataFilter())
        if not log_sensitive_data:
            console_handler.addFilter(EmailBodyFilter())

        logger.addHandler(console_handler)

    # File handler
    if log_file:
        # Ensure log directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # File gets more detail
        file_handler.setFormatter(detailed_formatter)

        # Add filters if not in debug mode
        if not log_sensitive_data:
            file_handler.addFilter(SensitiveDataFilter())
            file_handler.addFilter(EmailBodyFilter())

        logger.addHandler(file_handler)

    # Set up library loggers
    _configure_library_loggers(log_level)

    logger.info(f"Logging configured: level={log_level}, file={log_file}, sensitive_data={log_sensitive_data}")


def _configure_library_loggers(log_level: str):
    """
    Configure logging for third-party libraries.

    Args:
        log_level: Application log level
    """
    # Google API client can be very verbose
    logging.getLogger('googleapiclient').setLevel(logging.WARNING)
    logging.getLogger('google.auth').setLevel(logging.WARNING)
    logging.getLogger('google_auth_httplib2').setLevel(logging.WARNING)

    # HTTP requests
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)

    # Keyring can be noisy
    logging.getLogger('keyring').setLevel(logging.WARNING)

    # ML libraries
    logging.getLogger('transformers').setLevel(logging.WARNING)
    logging.getLogger('sentence_transformers').setLevel(logging.WARNING)
    logging.getLogger('torch').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Configured logger
    """
    return logging.getLogger(f'email-assistant.{name}')


# Convenience function for testing
def test_logging():
    """Test logging configuration with sample data."""
    logger = get_logger('test')

    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")

    # Test sensitive data filtering
    logger.info("User email: user@example.com")
    logger.info("Token: abc123xyz789abc123xyz789abc123xyz789")
    logger.info("Password: supersecret")
    logger.info("email body: This is sensitive content that should be filtered")


if __name__ == '__main__':
    # Test setup
    setup_logging(
        log_level='DEBUG',
        log_file=Path('test.log'),
        log_sensitive_data=False,
        console_output=True
    )

    test_logging()
