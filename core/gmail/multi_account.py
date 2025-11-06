"""
Multi-Account Gmail Manager

Handles authentication, fetching, and management of multiple Gmail accounts.
Supports 4-6 accounts with unified view and cross-account deduplication.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


class GmailAccount:
    """Represents a single Gmail account with its credentials and service."""

    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/calendar.events'
    ]

    def __init__(
        self,
        name: str,
        email: str,
        credentials_path: str,
        priority: str = 'normal',
        enabled: bool = True
    ):
        """
        Initialize Gmail account.

        Args:
            name: Friendly name for the account
            email: Email address
            credentials_path: Path to OAuth credentials JSON
            priority: Priority level (high/normal/low)
            enabled: Whether account is active
        """
        self.name = name
        self.email = email
        self.credentials_path = Path(credentials_path)
        self.priority = priority
        self.enabled = enabled
        self.service = None  # Gmail service
        self.calendar_service = None  # Calendar service
        self.creds = None

    def authenticate(self, use_keyring: bool = True) -> bool:
        """
        Authenticate with Gmail API.

        Args:
            use_keyring: Whether to use keyring for token storage

        Returns:
            True if authentication successful
        """
        logger.info(f"Authenticating account: {self.name} ({self.email})")

        creds = None

        # Try to load from keyring
        if use_keyring:
            try:
                from core.security.credentials import CredentialManager
                cred_manager = CredentialManager()
                token_data = cred_manager.get_oauth_token(self.email)

                if token_data:
                    creds = Credentials(
                        token=token_data.get('token'),
                        refresh_token=token_data.get('refresh_token'),
                        token_uri=token_data.get('token_uri'),
                        client_id=token_data.get('client_id'),
                        client_secret=token_data.get('client_secret'),
                        scopes=token_data.get('scopes', self.SCOPES)
                    )
                    logger.info(f"  ✓ Loaded credentials from keyring")
            except Exception as e:
                logger.warning(f"  ⚠ Keyring not available: {e}")

        # Refresh or get new credentials
        if creds and creds.expired and creds.refresh_token:
            logger.info(f"  Refreshing expired credentials...")
            creds.refresh(Request())
            logger.info(f"  ✓ Credentials refreshed")

        elif not creds or not creds.valid:
            if not self.credentials_path.exists():
                logger.error(f"  ❌ Credentials file not found: {self.credentials_path}")
                return False

            logger.info(f"  Starting OAuth flow...")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_path),
                self.SCOPES
            )
            creds = flow.run_local_server(port=0)
            logger.info(f"  ✓ New credentials obtained")

        # Save to keyring
        if use_keyring and creds:
            try:
                from core.security.credentials import CredentialManager
                cred_manager = CredentialManager()
                token_data = {
                    'token': creds.token,
                    'refresh_token': creds.refresh_token,
                    'token_uri': creds.token_uri,
                    'client_id': creds.client_id,
                    'client_secret': creds.client_secret,
                    'scopes': creds.scopes,
                    'expiry': creds.expiry.isoformat() if creds.expiry else None
                }
                cred_manager.store_oauth_token(self.email, token_data)
                logger.info(f"  ✓ Credentials saved to keyring")
            except Exception as e:
                logger.warning(f"  ⚠ Could not save to keyring: {e}")

        # Build services
        self.creds = creds
        self.service = build('gmail', 'v1', credentials=creds)
        self.calendar_service = build('calendar', 'v3', credentials=creds)
        logger.info(f"✅ {self.name} authenticated successfully (Gmail + Calendar)")

        return True

    def fetch_emails(self, max_results: int = 1000, query: str = '') -> List[Dict]:
        """
        Fetch emails from this account.

        Args:
            max_results: Maximum number of emails to fetch
            query: Gmail search query

        Returns:
            List of email message dictionaries
        """
        if not self.service:
            logger.error(f"Account {self.name} not authenticated")
            return []

        logger.info(f"Fetching emails from {self.name} (max: {max_results})...")

        try:
            # Get message IDs
            messages = []
            page_token = None

            while len(messages) < max_results:
                results = self.service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=min(500, max_results - len(messages)),
                    pageToken=page_token
                ).execute()

                batch = results.get('messages', [])
                messages.extend(batch)

                page_token = results.get('nextPageToken')
                if not page_token:
                    break

            logger.info(f"  Found {len(messages)} message IDs")

            # Fetch full messages
            full_messages = []
            for i, msg in enumerate(messages, 1):
                if i % 50 == 0:
                    logger.info(f"  Progress: {i}/{len(messages)} ({i*100//len(messages)}%)")

                try:
                    full_msg = self.service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='full'
                    ).execute()

                    # Add account metadata
                    full_msg['_account'] = self.name
                    full_msg['_account_email'] = self.email
                    full_msg['_account_priority'] = self.priority

                    full_messages.append(full_msg)

                except Exception as e:
                    logger.warning(f"  Failed to fetch message {msg['id']}: {e}")
                    continue

            logger.info(f"✅ Fetched {len(full_messages)} emails from {self.name}")
            return full_messages

        except Exception as e:
            logger.error(f"❌ Error fetching emails from {self.name}: {e}")
            return []


class MultiAccountManager:
    """Manage multiple Gmail accounts with unified operations."""

    def __init__(self, config_path: str = 'accounts.json'):
        """
        Initialize multi-account manager.

        Args:
            config_path: Path to accounts configuration JSON
        """
        self.config_path = Path(config_path)
        self.accounts: List[GmailAccount] = []
        self.settings: Dict = {}

        self._load_config()

    def _load_config(self):
        """Load accounts configuration from JSON file."""
        if not self.config_path.exists():
            logger.error(f"Config file not found: {self.config_path}")
            logger.info("Create accounts.json from accounts.json.example")
            return

        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)

            # Load accounts
            for acc_config in config.get('accounts', []):
                account = GmailAccount(
                    name=acc_config['name'],
                    email=acc_config['email'],
                    credentials_path=acc_config['credentials_path'],
                    priority=acc_config.get('priority', 'normal'),
                    enabled=acc_config.get('enabled', True)
                )
                self.accounts.append(account)

            # Load settings
            self.settings = config.get('settings', {})

            logger.info(f"Loaded {len(self.accounts)} accounts from config")

            # Log account summary
            for acc in self.accounts:
                status = "✓" if acc.enabled else "✗"
                logger.info(f"  {status} {acc.name} ({acc.email}) - {acc.priority} priority")

        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise

    def authenticate_all(self, use_keyring: bool = True) -> Tuple[int, int]:
        """
        Authenticate all enabled accounts.

        Args:
            use_keyring: Whether to use keyring for token storage

        Returns:
            Tuple of (successful_count, failed_count)
        """
        logger.info("\n" + "="*70)
        logger.info("AUTHENTICATING ALL ACCOUNTS")
        logger.info("="*70)

        enabled_accounts = [acc for acc in self.accounts if acc.enabled]
        logger.info(f"Authenticating {len(enabled_accounts)} enabled accounts...")

        success_count = 0
        fail_count = 0

        for account in enabled_accounts:
            try:
                if account.authenticate(use_keyring=use_keyring):
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                logger.error(f"Failed to authenticate {account.name}: {e}")
                fail_count += 1

        logger.info("\n" + "="*70)
        logger.info(f"Authentication complete: {success_count} success, {fail_count} failed")
        logger.info("="*70)

        return success_count, fail_count

    def fetch_all_emails(
        self,
        max_per_account: Optional[int] = None,
        parallel: bool = True
    ) -> Dict[str, List[Dict]]:
        """
        Fetch emails from all authenticated accounts.

        Args:
            max_per_account: Max emails per account (from config if None)
            parallel: Whether to fetch in parallel

        Returns:
            Dictionary mapping account name to list of emails
        """
        logger.info("\n" + "="*70)
        logger.info("FETCHING EMAILS FROM ALL ACCOUNTS")
        logger.info("="*70)

        max_emails = max_per_account or self.settings.get('max_emails_per_account', 1000)
        authenticated_accounts = [acc for acc in self.accounts if acc.service]

        logger.info(f"Fetching from {len(authenticated_accounts)} authenticated accounts")
        logger.info(f"Max emails per account: {max_emails}")

        results = {}

        if parallel and self.settings.get('parallel_fetch', True):
            # Parallel fetching
            logger.info("Using parallel fetching...")

            with ThreadPoolExecutor(max_workers=len(authenticated_accounts)) as executor:
                future_to_account = {
                    executor.submit(acc.fetch_emails, max_emails): acc
                    for acc in authenticated_accounts
                }

                for future in as_completed(future_to_account):
                    account = future_to_account[future]
                    try:
                        emails = future.result()
                        results[account.name] = emails
                    except Exception as e:
                        logger.error(f"Failed to fetch from {account.name}: {e}")
                        results[account.name] = []

        else:
            # Sequential fetching
            logger.info("Using sequential fetching...")
            for account in authenticated_accounts:
                try:
                    emails = account.fetch_emails(max_emails)
                    results[account.name] = emails
                except Exception as e:
                    logger.error(f"Failed to fetch from {account.name}: {e}")
                    results[account.name] = []

        # Summary
        total_emails = sum(len(emails) for emails in results.values())
        logger.info("\n" + "="*70)
        logger.info(f"Fetched {total_emails} total emails across {len(results)} accounts")
        for account_name, emails in results.items():
            logger.info(f"  {account_name}: {len(emails)} emails")
        logger.info("="*70)

        return results

    def deduplicate_emails(self, all_emails: List[Dict]) -> List[Dict]:
        """
        Remove duplicate emails across accounts.

        Args:
            all_emails: List of all emails from all accounts

        Returns:
            Deduplicated list of emails
        """
        if not self.settings.get('cross_account_deduplication', True):
            return all_emails

        logger.info(f"Deduplicating {len(all_emails)} emails...")

        seen_hashes = set()
        unique_emails = []

        for email in all_emails:
            # Create hash from message-id or content
            headers = {h['name'].lower(): h['value']
                      for h in email.get('payload', {}).get('headers', [])}

            msg_id = headers.get('message-id', '')
            subject = headers.get('subject', '')
            sender = headers.get('from', '')

            # Hash based on message-id or subject+sender
            if msg_id:
                hash_key = hashlib.sha256(msg_id.encode()).hexdigest()
            else:
                hash_key = hashlib.sha256(f"{subject}{sender}".encode()).hexdigest()

            if hash_key not in seen_hashes:
                seen_hashes.add(hash_key)
                unique_emails.append(email)

        duplicates_removed = len(all_emails) - len(unique_emails)
        logger.info(f"  Removed {duplicates_removed} duplicates")
        logger.info(f"  {len(unique_emails)} unique emails remaining")

        return unique_emails

    def get_all_emails_unified(self, max_per_account: Optional[int] = None) -> List[Dict]:
        """
        Get all emails from all accounts in a unified list.

        Args:
            max_per_account: Max emails per account

        Returns:
            Unified, deduplicated list of all emails
        """
        # Fetch from all accounts
        results = self.fetch_all_emails(max_per_account=max_per_account)

        # Combine all emails
        all_emails = []
        for account_name, emails in results.items():
            all_emails.extend(emails)

        # Deduplicate
        unique_emails = self.deduplicate_emails(all_emails)

        return unique_emails

    def get_account_by_email(self, email: str) -> Optional[GmailAccount]:
        """Get account by email address."""
        for account in self.accounts:
            if account.email == email:
                return account
        return None

    def get_enabled_accounts(self) -> List[GmailAccount]:
        """Get list of enabled accounts."""
        return [acc for acc in self.accounts if acc.enabled]

    def get_authenticated_accounts(self) -> List[GmailAccount]:
        """Get list of authenticated accounts."""
        return [acc for acc in self.accounts if acc.service]
