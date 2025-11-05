"""
Input validation and sanitization for security.

Protects against:
- SQL injection (via parameterized queries)
- Path traversal attacks
- Email header injection
- Message ID manipulation
- Invalid folder names
"""

import re
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SecurityValidator:
    """Validate and sanitize user inputs to prevent security vulnerabilities."""

    # Gmail message IDs are hexadecimal strings
    MESSAGE_ID_PATTERN = re.compile(r'^[a-f0-9]{16,}$', re.IGNORECASE)

    # Gmail label/folder names: alphanumeric, spaces, underscores, hyphens
    LABEL_NAME_PATTERN = re.compile(r'^[\w\s\-/]{1,100}$')

    # Email address pattern (basic validation)
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )

    # Thread ID pattern (similar to message ID)
    THREAD_ID_PATTERN = re.compile(r'^[a-f0-9]{16,}$', re.IGNORECASE)

    @staticmethod
    def validate_message_id(msg_id: str) -> str:
        """
        Validate and sanitize Gmail message ID.

        Args:
            msg_id: Gmail message ID

        Returns:
            Validated message ID

        Raises:
            ValueError: If message ID is invalid
        """
        if not isinstance(msg_id, str):
            raise ValueError(f"Message ID must be string, got {type(msg_id)}")

        msg_id = msg_id.strip()

        if not msg_id:
            raise ValueError("Message ID cannot be empty")

        if not SecurityValidator.MESSAGE_ID_PATTERN.match(msg_id):
            raise ValueError(
                f"Invalid message ID format: {msg_id[:50]}... "
                "(expected hexadecimal string)"
            )

        return msg_id

    @staticmethod
    def validate_thread_id(thread_id: str) -> str:
        """
        Validate and sanitize Gmail thread ID.

        Args:
            thread_id: Gmail thread ID

        Returns:
            Validated thread ID

        Raises:
            ValueError: If thread ID is invalid
        """
        if not isinstance(thread_id, str):
            raise ValueError(f"Thread ID must be string, got {type(thread_id)}")

        thread_id = thread_id.strip()

        if not thread_id:
            raise ValueError("Thread ID cannot be empty")

        if not SecurityValidator.THREAD_ID_PATTERN.match(thread_id):
            raise ValueError(
                f"Invalid thread ID format: {thread_id[:50]}... "
                "(expected hexadecimal string)"
            )

        return thread_id

    @staticmethod
    def validate_label_name(label: str) -> str:
        """
        Validate Gmail label/folder name.

        Args:
            label: Label name

        Returns:
            Validated label name

        Raises:
            ValueError: If label name is invalid
        """
        if not isinstance(label, str):
            raise ValueError(f"Label name must be string, got {type(label)}")

        label = label.strip()

        if not label:
            raise ValueError("Label name cannot be empty")

        if len(label) > 100:
            raise ValueError(f"Label name too long: {len(label)} chars (max 100)")

        if not SecurityValidator.LABEL_NAME_PATTERN.match(label):
            raise ValueError(
                f"Invalid label name: {label[:50]}... "
                "(allowed: letters, numbers, spaces, hyphens, underscores, slashes)"
            )

        return label

    @staticmethod
    def validate_email_address(email: str) -> str:
        """
        Validate email address format.

        Args:
            email: Email address

        Returns:
            Validated email address

        Raises:
            ValueError: If email is invalid
        """
        if not isinstance(email, str):
            raise ValueError(f"Email must be string, got {type(email)}")

        email = email.strip().lower()

        if not email:
            raise ValueError("Email address cannot be empty")

        if len(email) > 254:  # RFC 5321
            raise ValueError(f"Email address too long: {len(email)} chars")

        if not SecurityValidator.EMAIL_PATTERN.match(email):
            raise ValueError(f"Invalid email format: {email}")

        return email

    @staticmethod
    def sanitize_path(path: str, base_dir: str) -> Path:
        """
        Validate path is within allowed directory (prevent path traversal).

        Args:
            path: File path to validate
            base_dir: Base directory that path must be within

        Returns:
            Resolved Path object

        Raises:
            ValueError: If path is outside base_dir
        """
        try:
            resolved = Path(path).resolve()
            base = Path(base_dir).resolve()

            # Check if resolved path is within base directory
            if base not in resolved.parents and resolved != base:
                raise ValueError(
                    f"Path outside allowed directory: {path} "
                    f"(base: {base_dir})"
                )

            return resolved

        except Exception as e:
            raise ValueError(f"Invalid path: {path}") from e

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to prevent path traversal and injection.

        Args:
            filename: Filename to sanitize

        Returns:
            Safe filename

        Raises:
            ValueError: If filename is invalid
        """
        if not isinstance(filename, str):
            raise ValueError(f"Filename must be string, got {type(filename)}")

        filename = filename.strip()

        if not filename:
            raise ValueError("Filename cannot be empty")

        # Remove directory separators
        filename = filename.replace('/', '_').replace('\\', '_')

        # Remove null bytes
        filename = filename.replace('\x00', '')

        # Limit length
        if len(filename) > 255:
            raise ValueError(f"Filename too long: {len(filename)} chars")

        # Check for suspicious patterns
        if filename.startswith('.') or filename == '..':
            raise ValueError(f"Invalid filename: {filename}")

        return filename

    @staticmethod
    def sanitize_subject(subject: str, max_length: int = 1000) -> str:
        """
        Sanitize email subject line.

        Args:
            subject: Email subject
            max_length: Maximum allowed length

        Returns:
            Sanitized subject
        """
        if not isinstance(subject, str):
            subject = str(subject)

        # Remove null bytes and control characters
        subject = ''.join(char for char in subject if ord(char) >= 32 or char == '\n')

        # Truncate if too long
        if len(subject) > max_length:
            subject = subject[:max_length]

        return subject.strip()

    @staticmethod
    def validate_max_results(max_results: int, max_allowed: int = 500) -> int:
        """
        Validate max_results parameter for API calls.

        Args:
            max_results: Requested maximum results
            max_allowed: Maximum allowed value

        Returns:
            Validated max_results

        Raises:
            ValueError: If max_results is invalid
        """
        if not isinstance(max_results, int):
            raise ValueError(f"max_results must be integer, got {type(max_results)}")

        if max_results < 1:
            raise ValueError(f"max_results must be positive, got {max_results}")

        if max_results > max_allowed:
            raise ValueError(
                f"max_results too large: {max_results} (max: {max_allowed})"
            )

        return max_results

    @staticmethod
    def sanitize_for_log(text: str, mask_email: bool = True) -> str:
        """
        Sanitize text for logging (mask sensitive information).

        Args:
            text: Text to sanitize
            mask_email: Whether to mask email addresses

        Returns:
            Sanitized text safe for logging
        """
        if not isinstance(text, str):
            text = str(text)

        # Mask email addresses
        if mask_email:
            text = re.sub(
                r'\b([a-zA-Z0-9._%+-])([a-zA-Z0-9._%+-]*)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
                r'\1***@\3',
                text
            )

        # Mask potential tokens/keys (long alphanumeric strings)
        text = re.sub(
            r'\b[a-zA-Z0-9]{32,}\b',
            '[TOKEN]',
            text
        )

        return text

    @staticmethod
    def validate_confidence_score(score: float) -> float:
        """
        Validate ML confidence score.

        Args:
            score: Confidence score

        Returns:
            Validated score

        Raises:
            ValueError: If score is invalid
        """
        if not isinstance(score, (int, float)):
            raise ValueError(f"Score must be numeric, got {type(score)}")

        score = float(score)

        if not 0.0 <= score <= 1.0:
            raise ValueError(f"Score must be between 0 and 1, got {score}")

        return score

    @staticmethod
    def validate_priority(priority: str) -> str:
        """
        Validate priority classification.

        Args:
            priority: Priority string

        Returns:
            Validated priority

        Raises:
            ValueError: If priority is invalid
        """
        valid_priorities = {'critical', 'important', 'normal', 'low', 'archive'}

        if not isinstance(priority, str):
            raise ValueError(f"Priority must be string, got {type(priority)}")

        priority = priority.lower().strip()

        if priority not in valid_priorities:
            raise ValueError(
                f"Invalid priority: {priority} "
                f"(valid: {', '.join(sorted(valid_priorities))})"
            )

        return priority

    @staticmethod
    def validate_category(category: str) -> str:
        """
        Validate email category.

        Args:
            category: Category string

        Returns:
            Validated category

        Raises:
            ValueError: If category is invalid
        """
        valid_categories = {
            'personal', 'work', 'newsletter', 'marketing',
            'transactional', 'social', 'other'
        }

        if not isinstance(category, str):
            raise ValueError(f"Category must be string, got {type(category)}")

        category = category.lower().strip()

        if category not in valid_categories:
            raise ValueError(
                f"Invalid category: {category} "
                f"(valid: {', '.join(sorted(valid_categories))})"
            )

        return category
