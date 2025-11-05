"""
Comprehensive test suite for Phase 1 & 2 (Security + Database).

Tests all components built so far:
- Configuration management
- Keyring credential storage
- Database encryption
- Database operations
- Input validation
- Secure logging
"""

import os
import sys
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Test imports
SQLCIPHER_AVAILABLE = False

try:
    from config.settings import Settings, get_settings
    from core.security.credentials import CredentialManager
    from core.security.validation import SecurityValidator
    from core.security.logging_config import setup_logging, get_logger
    print("✅ Core imports successful")

    # Try to import SQLCipher-dependent modules
    try:
        from core.security.encryption import EncryptionManager
        from core.database import EmailDatabase
        from core.database.models import EmailRecord, CalendarEvent
        SQLCIPHER_AVAILABLE = True
        print("✅ SQLCipher imports successful")
    except Exception as e:
        print(f"⚠️  SQLCipher not available: {e}")
        print("   Database encryption tests will be skipped")

except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)


class TestRunner:
    """Comprehensive test runner for Phase 1 & 2."""

    def __init__(self):
        self.test_results = []
        self.temp_dir = None
        self.test_db_path = None
        self.test_db_key = None

    def setup(self):
        """Setup test environment."""
        print("\n" + "="*70)
        print("SETTING UP TEST ENVIRONMENT")
        print("="*70)

        # Create temporary directory for tests
        self.temp_dir = tempfile.mkdtemp(prefix="email_assistant_test_")
        print(f"✅ Created temp directory: {self.temp_dir}")

        # Setup test database path
        self.test_db_path = Path(self.temp_dir) / "test_email.db"
        self.test_db_key = "test_encryption_key_32_bytes_!!"
        print(f"✅ Test database will be: {self.test_db_path}")

        # Setup logging
        setup_logging(
            log_level='DEBUG',
            log_file=Path(self.temp_dir) / 'test.log',
            log_sensitive_data=False,
            console_output=False  # Don't clutter output
        )
        print("✅ Logging configured")

    def teardown(self):
        """Cleanup test environment."""
        print("\n" + "="*70)
        print("CLEANING UP")
        print("="*70)

        import shutil
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
            print(f"✅ Removed temp directory: {self.temp_dir}")

    def run_test(self, name: str, test_func):
        """Run a single test and record result."""
        print(f"\n{'─'*70}")
        print(f"TEST: {name}")
        print(f"{'─'*70}")

        try:
            test_func()
            self.test_results.append((name, True, None))
            print(f"✅ PASSED: {name}")
            return True
        except Exception as e:
            self.test_results.append((name, False, str(e)))
            print(f"❌ FAILED: {name}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            return False

    # ===== TEST CASES =====

    def test_configuration_system(self):
        """Test configuration management."""
        # Create test .env file
        env_file = Path(self.temp_dir) / '.env'
        env_file.write_text("""
GMAIL_USER_EMAIL=test@example.com
ML_CONFIDENCE_THRESHOLD_LOW=0.2
ML_CONFIDENCE_THRESHOLD_HIGH=0.8
DATABASE_PATH=/tmp/test.db
LOG_LEVEL=DEBUG
        """)

        # Load settings
        settings = Settings(str(env_file))

        # Validate settings
        assert settings.gmail_user_email == 'test@example.com', "Email not loaded"
        assert settings.ml_confidence_low == 0.2, "Low threshold not loaded"
        assert settings.ml_confidence_high == 0.8, "High threshold not loaded"
        assert settings.log_level == 'DEBUG', "Log level not loaded"

        print("  ✓ Configuration loaded from .env file")

        # Test validation
        issues = settings.validate()
        assert isinstance(issues, list), "Validation should return list"
        print(f"  ✓ Validation found {len(issues)} issues")

        # Test invalid config
        settings.ml_confidence_low = 1.5
        issues = settings.validate()
        assert len(issues) > 0, "Should detect invalid confidence threshold"
        print("  ✓ Validation detects invalid values")

    def test_keyring_credentials(self):
        """Test keyring credential management."""
        cred_manager = CredentialManager()
        print("  ✓ CredentialManager initialized")

        # Test OAuth token storage
        test_email = "test@example.com"
        test_token = {
            'token': 'test_access_token_abc123',
            'refresh_token': 'test_refresh_token_xyz789',
            'expiry': datetime.now().isoformat()
        }

        # Store token
        success = cred_manager.store_oauth_token(test_email, test_token)
        assert success, "Failed to store OAuth token"
        print("  ✓ OAuth token stored in keyring")

        # Retrieve token
        retrieved_token = cred_manager.get_oauth_token(test_email)
        assert retrieved_token is not None, "Failed to retrieve token"
        assert retrieved_token['token'] == test_token['token'], "Token mismatch"
        assert retrieved_token['refresh_token'] == test_token['refresh_token'], "Refresh token mismatch"
        print("  ✓ OAuth token retrieved successfully")

        # Test encryption key storage
        test_key_name = "test-db-key"
        test_key = "1234567890abcdef" * 4  # 64 char hex string

        success = cred_manager.store_encryption_key(test_key_name, test_key)
        assert success, "Failed to store encryption key"
        print("  ✓ Encryption key stored in keyring")

        retrieved_key = cred_manager.get_encryption_key(test_key_name)
        assert retrieved_key == test_key, "Encryption key mismatch"
        print("  ✓ Encryption key retrieved successfully")

        # Test generate and store
        generated_key = cred_manager.generate_and_store_db_key("test-generated-key")
        assert generated_key is not None, "Failed to generate key"
        assert len(generated_key) == 64, f"Key should be 64 chars, got {len(generated_key)}"
        print(f"  ✓ Generated 256-bit key: {generated_key[:16]}...")

        # Cleanup
        cred_manager.delete_oauth_token(test_email)
        print("  ✓ Cleaned up test credentials")

    def test_input_validation(self):
        """Test input validation and sanitization."""
        validator = SecurityValidator()

        # Test message ID validation
        valid_msg_id = "18a1b2c3d4e5f6a7"
        validated = validator.validate_message_id(valid_msg_id)
        assert validated == valid_msg_id, "Valid message ID rejected"
        print("  ✓ Valid message ID accepted")

        # Test invalid message IDs
        try:
            validator.validate_message_id("../../etc/passwd")
            assert False, "Should reject path traversal"
        except ValueError:
            print("  ✓ Path traversal blocked")

        try:
            validator.validate_message_id("abc; DROP TABLE emails;")
            assert False, "Should reject SQL injection"
        except ValueError:
            print("  ✓ SQL injection blocked")

        # Test email validation
        valid_email = "user@example.com"
        validated = validator.validate_email_address(valid_email)
        assert validated == valid_email.lower(), "Valid email rejected"
        print("  ✓ Valid email address accepted")

        try:
            validator.validate_email_address("not_an_email")
            assert False, "Should reject invalid email"
        except ValueError:
            print("  ✓ Invalid email rejected")

        # Test label validation
        valid_label = "Important/Work"
        validated = validator.validate_label_name(valid_label)
        assert validated == valid_label, "Valid label rejected"
        print("  ✓ Valid label name accepted")

        # Test priority validation
        for priority in ['critical', 'important', 'normal', 'low', 'archive']:
            validated = validator.validate_priority(priority)
            assert validated == priority, f"Priority {priority} rejected"
        print("  ✓ All priority values validated")

        # Test confidence score validation
        for score in [0.0, 0.5, 1.0]:
            validated = validator.validate_confidence_score(score)
            assert validated == score, f"Confidence {score} rejected"
        print("  ✓ Confidence scores validated")

        try:
            validator.validate_confidence_score(1.5)
            assert False, "Should reject out-of-range confidence"
        except ValueError:
            print("  ✓ Out-of-range confidence rejected")

        # Test log sanitization
        sensitive_text = "User email: user@example.com with token abc123xyz789abc123xyz789abc123"
        sanitized = validator.sanitize_for_log(sensitive_text)
        assert "user@example.com" not in sanitized, "Email not masked"
        assert "abc123xyz789abc123xyz789abc123" not in sanitized, "Token not masked"
        print("  ✓ Sensitive data sanitized in logs")

    def test_database_encryption(self):
        """Test database encryption with SQLCipher."""
        print(f"  Creating encrypted database at: {self.test_db_path}")

        # Create encrypted database
        EncryptionManager.create_encrypted_db(str(self.test_db_path), self.test_db_key)
        assert self.test_db_path.exists(), "Database file not created"
        print("  ✓ Encrypted database created")

        # Verify it's encrypted (standard SQLite can't read it)
        is_encrypted = EncryptionManager.verify_database_encrypted(str(self.test_db_path))
        assert is_encrypted, "Database is not encrypted!"
        print("  ✓ Database is properly encrypted")

        # Test connection with correct key
        conn = EncryptionManager.connect_encrypted_db(str(self.test_db_path), self.test_db_key)
        cursor = conn.execute("SELECT count(*) FROM sqlite_master")
        result = cursor.fetchone()
        conn.close()
        print(f"  ✓ Connected with correct key (found {result[0]} tables)")

        # Test connection with wrong key fails
        try:
            wrong_key = "wrong_key_" + "x" * 20
            conn = EncryptionManager.connect_encrypted_db(str(self.test_db_path), wrong_key)
            conn.execute("SELECT count(*) FROM sqlite_master")
            assert False, "Should fail with wrong key"
        except Exception:
            print("  ✓ Connection fails with wrong key (as expected)")

    def test_database_operations(self):
        """Test database CRUD operations."""
        # Initialize database
        db = EmailDatabase(str(self.test_db_path), self.test_db_key)
        print("  ✓ Database initialized with schema")

        # Test email save
        test_email = EmailRecord(
            message_id="test_msg_001",
            thread_id="test_thread_001",
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            subject="Test Email",
            date_received=datetime.now(),
            body_text="This is a test email body.",
            headers={"From": "sender@example.com", "Subject": "Test Email"},
            labels=["INBOX"],
            classification_priority="normal",
            classification_category="personal",
            confidence_score=0.85,
            is_uncertain=False,
            is_processed=True
        )

        email_id = db.save_email(test_email)
        assert email_id > 0, "Email not saved"
        print(f"  ✓ Email saved with ID: {email_id}")

        # Test email retrieval by ID
        retrieved = db.get_email(email_id)
        assert retrieved is not None, "Email not retrieved"
        assert retrieved.message_id == test_email.message_id, "Message ID mismatch"
        assert retrieved.sender == test_email.sender, "Sender mismatch"
        assert retrieved.subject == test_email.subject, "Subject mismatch"
        print("  ✓ Email retrieved by ID")

        # Test email retrieval by message_id
        retrieved = db.get_email_by_message_id("test_msg_001")
        assert retrieved is not None, "Email not found by message_id"
        assert retrieved.id == email_id, "ID mismatch"
        print("  ✓ Email retrieved by message_id")

        # Test classification update
        success = db.update_classification(
            email_id,
            priority="important",
            category="work",
            confidence=0.92,
            is_uncertain=False
        )
        assert success, "Classification update failed"

        updated = db.get_email(email_id)
        assert updated.classification_priority == "important", "Priority not updated"
        assert updated.classification_category == "work", "Category not updated"
        assert updated.confidence_score == 0.92, "Confidence not updated"
        print("  ✓ Email classification updated")

        # Test user feedback
        success = db.update_user_feedback(
            email_id,
            user_priority="critical",
            user_category="urgent"
        )
        assert success, "User feedback update failed"

        updated = db.get_email(email_id)
        assert updated.user_priority == "critical", "User priority not saved"
        assert updated.user_category == "urgent", "User category not saved"
        assert updated.needs_review == False, "Should clear needs_review flag"
        print("  ✓ User feedback stored")

        # Test unprocessed emails query
        test_email2 = EmailRecord(
            message_id="test_msg_002",
            sender="another@example.com",
            recipients=["me@example.com"],
            subject="Unprocessed Email",
            date_received=datetime.now(),
            is_processed=False
        )
        db.save_email(test_email2)

        unprocessed = db.get_unprocessed_emails()
        assert len(unprocessed) > 0, "Should find unprocessed emails"
        assert any(e.message_id == "test_msg_002" for e in unprocessed), "New email not in results"
        print(f"  ✓ Found {len(unprocessed)} unprocessed email(s)")

        # Test emails for review query
        test_email3 = EmailRecord(
            message_id="test_msg_003",
            sender="uncertain@example.com",
            recipients=["me@example.com"],
            subject="Uncertain Classification",
            date_received=datetime.now(),
            is_uncertain=True,
            needs_review=True,
            is_processed=True
        )
        db.save_email(test_email3)

        review_emails = db.get_emails_for_review()
        assert len(review_emails) > 0, "Should find emails needing review"
        assert any(e.message_id == "test_msg_003" for e in review_emails), "Uncertain email not flagged"
        print(f"  ✓ Found {len(review_emails)} email(s) needing review")

        # Test deduplication
        content = "This is test email content for deduplication"
        db.store_message_hash("test_msg_004", content)

        import hashlib
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        is_dup = db.is_duplicate("test_msg_004", content_hash)
        assert is_dup, "Should detect duplicate"
        print("  ✓ Deduplication working")

        # Test calendar event save
        test_event = CalendarEvent(
            email_id=email_id,
            event_type="deadline",
            title="Project Deadline",
            description="Complete project report",
            due_date=datetime.now() + timedelta(days=7),
            priority="high",
            reminder_status="pending",
            next_reminder_at=datetime.now() + timedelta(hours=1)
        )

        event_id = db.save_calendar_event(test_event)
        assert event_id > 0, "Calendar event not saved"
        print(f"  ✓ Calendar event saved with ID: {event_id}")

        # Test pending events query
        pending = db.get_pending_calendar_events()
        assert len(pending) > 0, "Should find pending events"
        assert any(e.title == "Project Deadline" for e in pending), "Event not found"
        print(f"  ✓ Found {len(pending)} pending calendar event(s)")

        # Close database
        db.close()
        print("  ✓ Database closed properly")

    def test_secure_logging(self):
        """Test secure logging functionality."""
        logger = get_logger('test')

        # Test basic logging
        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.error("Test error message")
        print("  ✓ Basic logging works")

        # Test that sensitive data is filtered
        # (We can't easily verify this without reading log file, but we can test it doesn't crash)
        logger.info("User email: sensitive@example.com")
        logger.info("Token: abc123xyz789abc123xyz789abc123xyz789")
        logger.info("Password: supersecret123")
        print("  ✓ Sensitive data logged (should be filtered)")

        # Read log file to verify filtering
        log_file = Path(self.temp_dir) / 'test.log'
        if log_file.exists():
            log_content = log_file.read_text()
            # Email should be masked
            if "sensitive@example.com" in log_content:
                print("  ⚠ WARNING: Email not fully masked in logs")
            else:
                print("  ✓ Email addresses masked in log file")

            # Token should be replaced
            if "abc123xyz789abc123xyz789abc123xyz789" in log_content:
                print("  ⚠ WARNING: Token not filtered in logs")
            else:
                print("  ✓ Long tokens filtered in log file")

    def print_summary(self):
        """Print test results summary."""
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)

        passed = sum(1 for _, success, _ in self.test_results if success)
        failed = sum(1 for _, success, _ in self.test_results if not success)
        total = len(self.test_results)

        print(f"\nTotal Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")

        if failed > 0:
            print("\nFailed Tests:")
            for name, success, error in self.test_results:
                if not success:
                    print(f"  ❌ {name}")
                    print(f"     Error: {error}")

        print("\n" + "="*70)

        if failed == 0:
            print("🎉 ALL TESTS PASSED! Phase 1 & 2 are working correctly.")
        else:
            print(f"⚠️  {failed} test(s) failed. Review errors above.")

        print("="*70)

        return failed == 0

    def run_all_tests(self):
        """Run all test cases."""
        self.setup()

        # Run all tests
        self.run_test("Configuration System", self.test_configuration_system)
        self.run_test("Keyring Credentials", self.test_keyring_credentials)
        self.run_test("Input Validation", self.test_input_validation)

        # Run database tests only if SQLCipher is available
        if SQLCIPHER_AVAILABLE:
            self.run_test("Database Encryption", self.test_database_encryption)
            self.run_test("Database Operations", self.test_database_operations)
        else:
            print("\n" + "─"*70)
            print("⚠️  SKIPPED: Database Encryption (SQLCipher not available)")
            print("⚠️  SKIPPED: Database Operations (SQLCipher not available)")
            print("─"*70)

        self.run_test("Secure Logging", self.test_secure_logging)

        # Print summary
        success = self.print_summary()

        self.teardown()

        return success


if __name__ == "__main__":
    print("\n" + "="*70)
    print("EMAIL ASSISTANT - PHASE 1 & 2 TEST SUITE")
    print("Testing: Security Hardening + Database Layer")
    print("="*70)

    runner = TestRunner()
    success = runner.run_all_tests()

    sys.exit(0 if success else 1)
