"""
Simple test to validate Phase 1 & 2 core components.

Tests components that don't require system dependencies:
- Configuration management
- Input validation
- Code structure and imports
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported."""
    print("\n" + "="*70)
    print("TEST: Module Imports")
    print("="*70)

    try:
        from config.settings import Settings
        print("  ✓ Config module imports")

        from core.security.validation import SecurityValidator
        print("  ✓ Validation module imports")

        from core.security.logging_config import setup_logging
        print("  ✓ Logging module imports")

        from core.database.models import EmailRecord, CalendarEvent
        print("  ✓ Database models import")

        print("\n✅ All core modules import successfully")
        return True

    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_validation():
    """Test input validation and sanitization."""
    print("\n" + "="*70)
    print("TEST: Input Validation & Sanitization")
    print("="*70)

    try:
        from core.security.validation import SecurityValidator
        validator = SecurityValidator()

        # Test message ID validation
        valid_id = "18a1b2c3d4e5f6a7"
        assert validator.validate_message_id(valid_id) == valid_id
        print("  ✓ Valid message ID accepted")

        # Test invalid message ID rejection
        try:
            validator.validate_message_id("../../etc/passwd")
            return False
        except ValueError:
            print("  ✓ Path traversal blocked")

        try:
            validator.validate_message_id("'; DROP TABLE emails;")
            return False
        except ValueError:
            print("  ✓ SQL injection attempt blocked")

        # Test email validation
        email = "user@example.com"
        assert validator.validate_email_address(email) == email.lower()
        print("  ✓ Valid email address accepted")

        try:
            validator.validate_email_address("not_an_email")
            return False
        except ValueError:
            print("  ✓ Invalid email rejected")

        # Test priority validation
        priorities = ['critical', 'important', 'normal', 'low', 'archive']
        for priority in priorities:
            assert validator.validate_priority(priority) == priority
        print(f"  ✓ All {len(priorities)} priority values validated")

        # Test category validation
        categories = ['personal', 'work', 'newsletter', 'marketing',
                     'transactional', 'social', 'other']
        for category in categories:
            assert validator.validate_category(category) == category
        print(f"  ✓ All {len(categories)} category values validated")

        # Test confidence score validation
        for score in [0.0, 0.25, 0.5, 0.75, 1.0]:
            assert validator.validate_confidence_score(score) == score
        print("  ✓ Confidence score validation working")

        try:
            validator.validate_confidence_score(1.5)
            return False
        except ValueError:
            print("  ✓ Out-of-range confidence rejected")

        # Test log sanitization
        sensitive = "Email: user@example.com Token: abc123xyz789abc123xyz789abc123xyz789"
        sanitized = validator.sanitize_for_log(sensitive)
        assert "@example.com" in sanitized  # Domain preserved
        assert "user@example.com" not in sanitized  # Email masked
        assert "abc123xyz789abc123xyz789abc123xyz789" not in sanitized  # Token masked
        print("  ✓ Sensitive data sanitization working")

        # Test label name validation
        valid_labels = ["INBOX", "Important/Work", "Test-Label"]
        for label in valid_labels:
            assert validator.validate_label_name(label) == label
        print("  ✓ Label name validation working")

        print("\n✅ All validation tests passed")
        return True

    except AssertionError as e:
        print(f"\n❌ Validation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_configuration():
    """Test configuration management."""
    print("\n" + "="*70)
    print("TEST: Configuration Management")
    print("="*70)

    try:
        import tempfile
        from config.settings import Settings

        # Create test .env file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("""
GMAIL_USER_EMAIL=test@example.com
ML_CONFIDENCE_THRESHOLD_LOW=0.2
ML_CONFIDENCE_THRESHOLD_HIGH=0.8
LOG_LEVEL=INFO
""")
            env_file = f.name

        # Load settings
        settings = Settings(env_file)
        print("  ✓ Settings loaded from .env file")

        # Verify values
        assert settings.gmail_user_email == "test@example.com"
        print("  ✓ Gmail email setting correct")

        assert settings.ml_confidence_low == 0.2
        assert settings.ml_confidence_high == 0.8
        print("  ✓ ML confidence thresholds correct")

        assert settings.log_level == "INFO"
        print("  ✓ Log level setting correct")

        # Test validation
        issues = settings.validate()
        print(f"  ✓ Validation check ran ({len(issues)} issues found)")

        # Test invalid configuration detection
        settings.ml_confidence_low = 1.5  # Invalid
        issues = settings.validate()
        assert len(issues) > 0
        print("  ✓ Invalid configuration detected")

        # Cleanup
        Path(env_file).unlink()

        print("\n✅ Configuration system working correctly")
        return True

    except Exception as e:
        print(f"\n❌ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_models():
    """Test database model creation."""
    print("\n" + "="*70)
    print("TEST: Database Models")
    print("="*70)

    try:
        from datetime import datetime
        from core.database.models import (
            EmailRecord, CalendarEvent, TrainingDataRecord,
            ModelVersion, ReminderRecord, ProcessingRule
        )

        # Test EmailRecord
        email = EmailRecord(
            message_id="test123",
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            subject="Test",
            date_received=datetime.now(),
            classification_priority="normal",
            confidence_score=0.85
        )
        assert email.message_id == "test123"
        assert email.confidence_score == 0.85
        email_dict = email.to_dict()
        assert isinstance(email_dict, dict)
        print("  ✓ EmailRecord model working")

        # Test CalendarEvent
        event = CalendarEvent(
            email_id=1,
            event_type="deadline",
            title="Test Deadline",
            due_date=datetime.now(),
            priority="high"
        )
        assert event.event_type == "deadline"
        assert event.priority == "high"
        event_dict = event.to_dict()
        assert isinstance(event_dict, dict)
        print("  ✓ CalendarEvent model working")

        # Test TrainingDataRecord
        training = TrainingDataRecord(
            email_id=1,
            features={"feature1": 0.5, "feature2": 0.8},
            label_priority="important",
            is_validated=True
        )
        assert training.is_validated == True
        training_dict = training.to_dict()
        assert isinstance(training_dict, dict)
        print("  ✓ TrainingDataRecord model working")

        # Test ModelVersion
        model = ModelVersion(
            version="1.0.0",
            model_type="random_forest",
            model_path="/path/to/model",
            training_samples=1000,
            accuracy=0.92,
            precision_by_class={"important": 0.91},
            recall_by_class={"important": 0.89},
            f1_by_class={"important": 0.90}
        )
        assert model.version == "1.0.0"
        assert model.accuracy == 0.92
        print("  ✓ ModelVersion model working")

        # Test ReminderRecord
        reminder = ReminderRecord(
            event_id=1,
            reminder_time=datetime.now(),
            reminder_type="desktop"
        )
        assert reminder.reminder_type == "desktop"
        print("  ✓ ReminderRecord model working")

        # Test ProcessingRule
        rule = ProcessingRule(
            name="Test Rule",
            condition_type="sender",
            condition_value="bot@example.com",
            action_type="auto_archive",
            action_value="true"
        )
        assert rule.name == "Test Rule"
        print("  ✓ ProcessingRule model working")

        print("\n✅ All database models working correctly")
        return True

    except Exception as e:
        print(f"\n❌ Database model test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_project_structure():
    """Test that project structure is correct."""
    print("\n" + "="*70)
    print("TEST: Project Structure")
    print("="*70)

    base_path = Path(__file__).parent

    required_files = [
        "config/settings.py",
        "config/schema.sql",
        "core/security/credentials.py",
        "core/security/encryption.py",
        "core/security/validation.py",
        "core/security/logging_config.py",
        "core/database/database.py",
        "core/database/models.py",
        "requirements.txt",
        ".env.example"
    ]

    missing = []
    for file_path in required_files:
        full_path = base_path / file_path
        if full_path.exists():
            print(f"  ✓ {file_path}")
        else:
            print(f"  ❌ {file_path} MISSING")
            missing.append(file_path)

    if missing:
        print(f"\n❌ {len(missing)} required file(s) missing")
        return False

    print("\n✅ All required files present")
    return True


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("EMAIL ASSISTANT - BASIC VALIDATION TEST")
    print("Phase 1 & 2: Core Components")
    print("="*70)

    results = []

    results.append(("Project Structure", test_project_structure()))
    results.append(("Module Imports", test_imports()))
    results.append(("Input Validation", test_validation()))
    results.append(("Configuration Management", test_configuration()))
    results.append(("Database Models", test_database_models()))

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for _, success in results if success)
    failed = sum(1 for _, success in results if not success)

    print(f"\nTotal Tests: {len(results)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")

    if failed > 0:
        print("\nFailed Tests:")
        for name, success in results:
            if not success:
                print(f"  ❌ {name}")

    print("\n" + "="*70)

    if failed == 0:
        print("🎉 ALL TESTS PASSED!")
        print("\nPhase 1 & 2 core components are working correctly.")
        print("\nNote: Full keyring and database tests require system dependencies:")
        print("  - SQLCipher for database encryption")
        print("  - Secret Service backend for keyring")
        print("  These can be tested once system packages are installed.")
    else:
        print(f"⚠️  {failed} test(s) failed")

    print("="*70)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
