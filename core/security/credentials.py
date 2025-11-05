"""
Secure credential management using OS keyring.

This module provides a secure way to store and retrieve sensitive credentials
like OAuth tokens and encryption keys using the operating system's credential
storage system (Secret Service on Linux, Keychain on macOS, Credential Locker on Windows).
"""

import json
import logging
from typing import Optional, Dict, Any
import keyring
from keyring.errors import PasswordDeleteError, KeyringError

logger = logging.getLogger(__name__)


class CredentialManager:
    """
    Manage credentials securely using OS keyring.

    Credentials are stored encrypted by the OS and protected by user login credentials.
    """

    SERVICE_NAME = "email-assistant"

    def __init__(self):
        """Initialize credential manager."""
        self._verify_keyring_available()

    def _verify_keyring_available(self):
        """Verify that keyring backend is available and working."""
        try:
            # Test keyring availability
            backend = keyring.get_keyring()
            logger.info(f"Using keyring backend: {backend.__class__.__name__}")

            # Check if it's the fail keyring (no actual storage)
            if 'fail' in backend.__class__.__name__.lower():
                logger.warning(
                    "No secure keyring backend available. "
                    "Credentials may not persist across sessions."
                )
        except Exception as e:
            logger.error(f"Keyring initialization failed: {e}")
            raise RuntimeError(
                "Failed to initialize secure credential storage. "
                "Please ensure your system's keyring service is available."
            ) from e

    def store_oauth_token(self, email: str, token_data: Dict[str, Any]) -> bool:
        """
        Store OAuth token securely in keyring.

        Args:
            email: User's email address (used as username)
            token_data: OAuth token dictionary containing access_token, refresh_token, etc.

        Returns:
            True if successful, False otherwise
        """
        try:
            username = f"gmail_token_{email}"
            token_json = json.dumps(token_data)

            keyring.set_password(self.SERVICE_NAME, username, token_json)
            logger.info(f"Stored OAuth token for {email}")
            return True

        except Exception as e:
            logger.error(f"Failed to store OAuth token for {email}: {e}")
            return False

    def get_oauth_token(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve OAuth token from keyring.

        Args:
            email: User's email address

        Returns:
            Token dictionary or None if not found
        """
        try:
            username = f"gmail_token_{email}"
            token_json = keyring.get_password(self.SERVICE_NAME, username)

            if token_json is None:
                logger.debug(f"No OAuth token found for {email}")
                return None

            token_data = json.loads(token_json)
            logger.debug(f"Retrieved OAuth token for {email}")
            return token_data

        except json.JSONDecodeError as e:
            logger.error(f"Corrupted token data for {email}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve OAuth token for {email}: {e}")
            return None

    def delete_oauth_token(self, email: str) -> bool:
        """
        Delete OAuth token from keyring.

        Args:
            email: User's email address

        Returns:
            True if successful, False otherwise
        """
        try:
            username = f"gmail_token_{email}"
            keyring.delete_password(self.SERVICE_NAME, username)
            logger.info(f"Deleted OAuth token for {email}")
            return True

        except PasswordDeleteError:
            logger.warning(f"No token to delete for {email}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete OAuth token for {email}: {e}")
            return False

    def store_encryption_key(self, key_name: str, key: str) -> bool:
        """
        Store encryption key securely in keyring.

        Args:
            key_name: Name/identifier for the key
            key: The encryption key (hex string or base64)

        Returns:
            True if successful, False otherwise
        """
        try:
            keyring.set_password(self.SERVICE_NAME, key_name, key)
            logger.info(f"Stored encryption key: {key_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to store encryption key {key_name}: {e}")
            return False

    def get_encryption_key(self, key_name: str) -> Optional[str]:
        """
        Retrieve encryption key from keyring.

        Args:
            key_name: Name/identifier for the key

        Returns:
            Encryption key or None if not found
        """
        try:
            key = keyring.get_password(self.SERVICE_NAME, key_name)

            if key is None:
                logger.debug(f"No encryption key found: {key_name}")
                return None

            logger.debug(f"Retrieved encryption key: {key_name}")
            return key

        except Exception as e:
            logger.error(f"Failed to retrieve encryption key {key_name}: {e}")
            return None

    def generate_and_store_db_key(self, key_name: str) -> Optional[str]:
        """
        Generate a new database encryption key and store it.

        Args:
            key_name: Name/identifier for the key

        Returns:
            The generated key or None if failed
        """
        try:
            import secrets

            # Generate 256-bit (32 byte) key
            key = secrets.token_hex(32)

            if self.store_encryption_key(key_name, key):
                logger.info(f"Generated and stored new encryption key: {key_name}")
                return key
            else:
                return None

        except Exception as e:
            logger.error(f"Failed to generate encryption key {key_name}: {e}")
            return None

    def get_or_create_db_key(self, key_name: str) -> Optional[str]:
        """
        Get existing database key or create a new one.

        Args:
            key_name: Name/identifier for the key

        Returns:
            The encryption key or None if failed
        """
        # Try to get existing key
        key = self.get_encryption_key(key_name)

        if key is not None:
            return key

        # Generate new key
        logger.info(f"No existing key found for {key_name}, generating new key")
        return self.generate_and_store_db_key(key_name)

    def list_stored_accounts(self) -> list[str]:
        """
        List all email accounts with stored OAuth tokens.

        Returns:
            List of email addresses
        """
        # Note: keyring doesn't provide a list operation
        # This would need to be tracked separately in the database
        logger.warning("list_stored_accounts not fully implemented - requires database tracking")
        return []

    def migrate_from_pickle(self, pickle_path: str, email: str) -> bool:
        """
        Migrate OAuth token from pickle file to keyring.

        Args:
            pickle_path: Path to the pickle file
            email: Email address for this token

        Returns:
            True if successful, False otherwise
        """
        try:
            import pickle
            from pathlib import Path

            pickle_file = Path(pickle_path)

            if not pickle_file.exists():
                logger.warning(f"Pickle file not found: {pickle_path}")
                return False

            # Load token from pickle
            with open(pickle_file, 'rb') as f:
                token_data = pickle.load(f)

            # Convert to dict if necessary
            if hasattr(token_data, '__dict__'):
                token_dict = {
                    'token': token_data.token,
                    'refresh_token': getattr(token_data, 'refresh_token', None),
                    'token_uri': getattr(token_data, 'token_uri', None),
                    'client_id': getattr(token_data, 'client_id', None),
                    'client_secret': getattr(token_data, 'client_secret', None),
                    'scopes': getattr(token_data, 'scopes', []),
                    'expiry': getattr(token_data, 'expiry', None).isoformat()
                    if hasattr(token_data, 'expiry') and token_data.expiry else None
                }
            else:
                token_dict = token_data

            # Store in keyring
            if self.store_oauth_token(email, token_dict):
                logger.info(f"Successfully migrated token from {pickle_path}")

                # Optionally delete pickle file
                # pickle_file.unlink()
                # logger.info(f"Deleted old pickle file: {pickle_path}")

                return True
            else:
                return False

        except Exception as e:
            logger.error(f"Failed to migrate from pickle: {e}")
            return False
