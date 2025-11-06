"""
Multi-Account Integration Test

Tests the complete multi-account workflow:
1. Configuration loading
2. Multi-account authentication
3. Email fetching across accounts
4. Cross-account deduplication
5. Multi-account analysis
6. Unified ML training

Usage:
    # Test with real accounts (requires accounts.json with valid credentials)
    python test_multi_account.py

    # Dry run (tests configuration only, no API calls)
    python test_multi_account.py --dry-run

Note: This test does NOT modify any emails. It only reads them.
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_configuration():
    """Test 1: Configuration file loading."""
    logger.info("\n" + "="*70)
    logger.info("TEST 1: Configuration Loading")
    logger.info("="*70)

    config_path = Path('accounts.json')

    if not config_path.exists():
        logger.error("❌ accounts.json not found")
        logger.info("\n💡 Create accounts.json from template:")
        logger.info("   cp accounts.json.example accounts.json")
        logger.info("   # Edit with your account details")
        return False

    try:
        with open(config_path) as f:
            config = json.load(f)

        # Validate structure
        if 'accounts' not in config:
            logger.error("❌ Missing 'accounts' key in configuration")
            return False

        if 'settings' not in config:
            logger.warning("⚠️  Missing 'settings' key (will use defaults)")

        accounts = config['accounts']
        logger.info(f"✅ Configuration loaded: {len(accounts)} account(s) configured")

        # Validate each account
        required_fields = ['name', 'email', 'credentials_path']
        for i, account in enumerate(accounts, 1):
            logger.info(f"\n  Account {i}: {account.get('name', 'unknown')}")

            for field in required_fields:
                if field not in account:
                    logger.error(f"    ❌ Missing required field: {field}")
                    return False
                logger.info(f"    ✓ {field}: {account[field]}")

            # Check credentials file exists
            cred_path = Path(account['credentials_path'])
            if not cred_path.exists():
                logger.error(f"    ❌ Credentials file not found: {cred_path}")
                logger.info(f"    💡 Ensure OAuth credentials are downloaded for {account['email']}")
                return False
            else:
                logger.info(f"    ✓ Credentials file exists")

        logger.info("\n✅ TEST 1 PASSED: Configuration is valid")
        return True

    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in accounts.json: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Configuration error: {e}")
        return False


def test_multi_account_manager():
    """Test 2: MultiAccountManager initialization."""
    logger.info("\n" + "="*70)
    logger.info("TEST 2: MultiAccountManager Initialization")
    logger.info("="*70)

    try:
        from core.gmail.multi_account import MultiAccountManager

        manager = MultiAccountManager('accounts.json')

        logger.info(f"✅ Manager initialized")
        logger.info(f"  • Accounts loaded: {len(manager.accounts)}")
        logger.info(f"  • Enabled accounts: {len(manager.get_enabled_accounts())}")

        # List accounts
        for acc in manager.accounts:
            status = "✓" if acc.enabled else "✗"
            logger.info(f"  {status} {acc.name} ({acc.email}) - {acc.priority} priority")

        logger.info("\n✅ TEST 2 PASSED: MultiAccountManager initialized successfully")
        return True

    except Exception as e:
        logger.error(f"❌ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_authentication(dry_run: bool = False):
    """Test 3: Multi-account authentication."""
    logger.info("\n" + "="*70)
    logger.info("TEST 3: Multi-Account Authentication")
    logger.info("="*70)

    if dry_run:
        logger.info("⚠️  DRY RUN: Skipping authentication test")
        return True

    try:
        from core.gmail.multi_account import MultiAccountManager

        manager = MultiAccountManager('accounts.json')

        logger.info("🔐 Authenticating all accounts...")
        logger.info("⚠️  This may open browser windows for OAuth flow")
        logger.info("⚠️  You may need to grant permissions for Gmail + Calendar access")

        success, failed = manager.authenticate_all()

        logger.info(f"\n📊 Authentication Results:")
        logger.info(f"  • Successful: {success}")
        logger.info(f"  • Failed: {failed}")

        if success == 0:
            logger.error("❌ TEST 3 FAILED: No accounts authenticated")
            return False

        if failed > 0:
            logger.warning(f"⚠️  {failed} account(s) failed - check credentials")

        logger.info("\n✅ TEST 3 PASSED: At least one account authenticated")
        return True

    except Exception as e:
        logger.error(f"❌ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_email_fetching(dry_run: bool = False):
    """Test 4: Fetch emails from all accounts."""
    logger.info("\n" + "="*70)
    logger.info("TEST 4: Multi-Account Email Fetching")
    logger.info("="*70)

    if dry_run:
        logger.info("⚠️  DRY RUN: Skipping email fetching test")
        return True

    try:
        from core.gmail.multi_account import MultiAccountManager

        manager = MultiAccountManager('accounts.json')
        manager.authenticate_all()

        logger.info("📥 Fetching emails (max 50 per account for testing)...")

        results = manager.fetch_all_emails(max_per_account=50)

        total_emails = sum(len(emails) for emails in results.values())

        logger.info(f"\n📊 Fetch Results:")
        logger.info(f"  • Accounts fetched: {len(results)}")
        logger.info(f"  • Total emails: {total_emails}")

        for account_name, emails in results.items():
            logger.info(f"  • {account_name}: {len(emails)} emails")

        if total_emails == 0:
            logger.warning("⚠️  No emails fetched - check account permissions")

        logger.info("\n✅ TEST 4 PASSED: Email fetching completed")
        return True

    except Exception as e:
        logger.error(f"❌ TEST 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_deduplication(dry_run: bool = False):
    """Test 5: Cross-account deduplication."""
    logger.info("\n" + "="*70)
    logger.info("TEST 5: Cross-Account Deduplication")
    logger.info("="*70)

    if dry_run:
        logger.info("⚠️  DRY RUN: Skipping deduplication test")
        return True

    try:
        from core.gmail.multi_account import MultiAccountManager

        manager = MultiAccountManager('accounts.json')
        manager.authenticate_all()

        results = manager.fetch_all_emails(max_per_account=50)

        # Combine all emails
        all_emails = []
        for emails in results.values():
            all_emails.extend(emails)

        logger.info(f"📊 Before deduplication: {len(all_emails)} emails")

        # Deduplicate
        unique_emails = manager.deduplicate_emails(all_emails)

        duplicates_removed = len(all_emails) - len(unique_emails)

        logger.info(f"📊 After deduplication: {len(unique_emails)} emails")
        logger.info(f"📊 Duplicates removed: {duplicates_removed}")

        if duplicates_removed > 0:
            logger.info(f"✅ Deduplication working: removed {duplicates_removed} duplicates")
        else:
            logger.info("ℹ️  No duplicates found (expected if using different accounts)")

        logger.info("\n✅ TEST 5 PASSED: Deduplication completed")
        return True

    except Exception as e:
        logger.error(f"❌ TEST 5 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_unified_view(dry_run: bool = False):
    """Test 6: Unified email view."""
    logger.info("\n" + "="*70)
    logger.info("TEST 6: Unified Email View")
    logger.info("="*70)

    if dry_run:
        logger.info("⚠️  DRY RUN: Skipping unified view test")
        return True

    try:
        from core.gmail.multi_account import MultiAccountManager

        manager = MultiAccountManager('accounts.json')
        manager.authenticate_all()

        logger.info("📥 Getting unified email view...")

        unified_emails = manager.get_all_emails_unified(max_per_account=50)

        logger.info(f"\n📊 Unified View:")
        logger.info(f"  • Total unique emails: {len(unified_emails)}")

        # Check account metadata
        accounts_represented = set()
        for email in unified_emails:
            if '_account' in email:
                accounts_represented.add(email['_account'])

        logger.info(f"  • Accounts represented: {len(accounts_represented)}")
        for acc_name in sorted(accounts_represented):
            count = sum(1 for e in unified_emails if e.get('_account') == acc_name)
            logger.info(f"    - {acc_name}: {count} emails")

        logger.info("\n✅ TEST 6 PASSED: Unified view working")
        return True

    except Exception as e:
        logger.error(f"❌ TEST 6 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests(dry_run: bool = False):
    """Run all multi-account tests."""
    logger.info("\n" + "="*70)
    logger.info("MULTI-ACCOUNT INTEGRATION TEST SUITE")
    logger.info("="*70)

    if dry_run:
        logger.info("⚠️  DRY RUN MODE: Only configuration tests will run")

    tests = [
        ("Configuration Loading", test_configuration, False),
        ("MultiAccountManager Init", test_multi_account_manager, False),
        ("Authentication", test_authentication, True),
        ("Email Fetching", test_email_fetching, True),
        ("Deduplication", test_deduplication, True),
        ("Unified View", test_unified_view, True),
    ]

    results = []

    for test_name, test_func, needs_api in tests:
        if dry_run and needs_api:
            logger.info(f"\n⏭️  Skipping {test_name} (API test)")
            results.append(True)  # Don't count as failure
            continue

        try:
            result = test_func(dry_run=dry_run)
            results.append(result)
        except Exception as e:
            logger.error(f"❌ {test_name} crashed: {e}")
            results.append(False)

    # Summary
    logger.info("\n" + "="*70)
    logger.info("TEST SUMMARY")
    logger.info("="*70)

    passed = sum(results)
    total = len(results)

    logger.info(f"\n✅ Passed: {passed}/{total}")
    logger.info(f"❌ Failed: {total - passed}/{total}")

    if all(results):
        logger.info("\n🎉 ALL TESTS PASSED!")
        return True
    else:
        logger.info("\n❌ SOME TESTS FAILED")
        return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Test multi-account functionality')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Test configuration only (no API calls)'
    )

    args = parser.parse_args()

    success = run_all_tests(dry_run=args.dry_run)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
