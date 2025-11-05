"""
Database encryption using SQLCipher.

Provides AES-256 encryption for SQLite databases at rest.
"""

import logging
from pathlib import Path
from typing import Optional
import secrets

logger = logging.getLogger(__name__)


class EncryptionManager:
    """Manage database encryption with SQLCipher."""

    def __init__(self):
        """Initialize encryption manager."""
        self._verify_sqlcipher_available()

    def _verify_sqlcipher_available(self):
        """Verify SQLCipher is available."""
        try:
            import pysqlcipher3
            logger.info("SQLCipher is available for database encryption")
        except ImportError as e:
            logger.error(
                "SQLCipher not available. Database encryption will not work. "
                "Install with: pip install pysqlcipher3"
            )
            raise RuntimeError(
                "SQLCipher (pysqlcipher3) not installed. "
                "Database encryption requires SQLCipher."
            ) from e

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new 256-bit encryption key.

        Returns:
            Hex-encoded 256-bit key
        """
        return secrets.token_hex(32)  # 32 bytes = 256 bits

    @staticmethod
    def connect_encrypted_db(db_path: str, key: str):
        """
        Connect to an encrypted SQLite database.

        Args:
            db_path: Path to database file
            key: Encryption key (hex string)

        Returns:
            Database connection object

        Raises:
            Exception: If connection fails
        """
        try:
            from pysqlcipher3 import dbapi2 as sqlite

            # Connect to database
            conn = sqlite.connect(db_path)

            # Set encryption key
            conn.execute(f"PRAGMA key = '{key}'")

            # Configure SQLCipher
            conn.execute("PRAGMA cipher_page_size = 4096")
            conn.execute("PRAGMA kdf_iter = 64000")  # PBKDF2 iterations
            conn.execute("PRAGMA cipher_hmac_algorithm = HMAC_SHA256")
            conn.execute("PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA256")

            # Test that database is accessible (will fail if wrong key)
            conn.execute("SELECT count(*) FROM sqlite_master")

            logger.debug(f"Connected to encrypted database: {db_path}")
            return conn

        except Exception as e:
            logger.error(f"Failed to connect to encrypted database: {e}")
            raise

    @staticmethod
    def create_encrypted_db(db_path: str, key: str) -> bool:
        """
        Create a new encrypted database.

        Args:
            db_path: Path for new database file
            key: Encryption key (hex string)

        Returns:
            True if successful

        Raises:
            Exception: If creation fails
        """
        try:
            db_path_obj = Path(db_path)

            # Ensure parent directory exists
            db_path_obj.parent.mkdir(parents=True, exist_ok=True)

            # Connect (creates file)
            conn = EncryptionManager.connect_encrypted_db(str(db_path_obj), key)

            # Create a test table to ensure database is initialized
            conn.execute(
                "CREATE TABLE IF NOT EXISTS _encryption_test "
                "(id INTEGER PRIMARY KEY, value TEXT)"
            )
            conn.commit()
            conn.close()

            logger.info(f"Created encrypted database: {db_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to create encrypted database: {e}")
            raise

    @staticmethod
    def change_encryption_key(db_path: str, old_key: str, new_key: str) -> bool:
        """
        Change the encryption key for an existing database.

        Args:
            db_path: Path to database file
            old_key: Current encryption key
            new_key: New encryption key

        Returns:
            True if successful

        Raises:
            Exception: If key change fails
        """
        try:
            # Connect with old key
            conn = EncryptionManager.connect_encrypted_db(db_path, old_key)

            # Change to new key
            conn.execute(f"PRAGMA rekey = '{new_key}'")
            conn.commit()
            conn.close()

            # Verify new key works
            conn = EncryptionManager.connect_encrypted_db(db_path, new_key)
            conn.execute("SELECT count(*) FROM sqlite_master")
            conn.close()

            logger.info("Successfully changed database encryption key")
            return True

        except Exception as e:
            logger.error(f"Failed to change encryption key: {e}")
            raise

    @staticmethod
    def verify_database_encrypted(db_path: str) -> bool:
        """
        Check if a database file is encrypted.

        Args:
            db_path: Path to database file

        Returns:
            True if encrypted, False if not
        """
        try:
            import sqlite3

            # Try to open with standard SQLite (should fail if encrypted)
            conn = sqlite3.connect(db_path)
            conn.execute("SELECT count(*) FROM sqlite_master")
            conn.close()

            # If we got here, database is NOT encrypted
            logger.warning(f"Database is NOT encrypted: {db_path}")
            return False

        except sqlite3.DatabaseError:
            # Database is encrypted (standard SQLite can't read it)
            logger.info(f"Database is encrypted: {db_path}")
            return True

        except Exception as e:
            logger.error(f"Error checking database encryption: {e}")
            return False

    @staticmethod
    def encrypt_existing_database(
        unencrypted_path: str,
        encrypted_path: str,
        key: str
    ) -> bool:
        """
        Encrypt an existing unencrypted database.

        Args:
            unencrypted_path: Path to unencrypted database
            encrypted_path: Path for encrypted copy
            key: Encryption key

        Returns:
            True if successful

        Raises:
            Exception: If encryption fails
        """
        try:
            import sqlite3
            from pysqlcipher3 import dbapi2 as sqlite_encrypted

            # Open unencrypted database
            source = sqlite3.connect(unencrypted_path)

            # Create encrypted database
            EncryptionManager.create_encrypted_db(encrypted_path, key)
            dest = EncryptionManager.connect_encrypted_db(encrypted_path, key)

            # Copy all data
            with source:
                for line in source.iterdump():
                    if line not in (
                        'BEGIN TRANSACTION;',
                        'COMMIT;'
                    ):
                        dest.execute(line)

            dest.commit()
            dest.close()
            source.close()

            logger.info(
                f"Successfully encrypted database: "
                f"{unencrypted_path} -> {encrypted_path}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to encrypt database: {e}")
            raise

    @staticmethod
    def test_encryption_key(db_path: str, key: str) -> bool:
        """
        Test if an encryption key is valid for a database.

        Args:
            db_path: Path to database file
            key: Encryption key to test

        Returns:
            True if key is valid, False otherwise
        """
        try:
            conn = EncryptionManager.connect_encrypted_db(db_path, key)
            conn.execute("SELECT count(*) FROM sqlite_master")
            conn.close()
            return True

        except Exception:
            return False
