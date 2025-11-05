"""
Mailbox Analysis Script

Analyzes your entire Gmail mailbox to understand patterns and inform ML approach.

This script:
1. Connects to Gmail via OAuth
2. Fetches emails (entire mailbox or large sample)
3. Analyzes sender patterns, content, headers, timing
4. Generates statistics and visualizations
5. Recommends optimal ML approach

Run this BEFORE building the ML model to understand your data.
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional
import base64
import pickle

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Check for required dependencies
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    print("✅ Google API libraries available")
except ImportError as e:
    print(f"❌ Missing Google API libraries: {e}")
    print("Install with: pip install google-auth-oauthlib google-api-python-client")
    sys.exit(1)

# Optional: Load our security modules
try:
    from core.security.credentials import CredentialManager
    from core.security.validation import SecurityValidator
    USE_SECURE_STORAGE = True
    print("✅ Using secure credential storage")
except ImportError:
    USE_SECURE_STORAGE = False
    print("⚠️  Secure storage not available, using legacy token.pickle")


class MailboxAnalyzer:
    """Analyze Gmail mailbox to understand patterns for ML model."""

    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify'
    ]

    def __init__(self, credentials_path: str, user_email: str):
        """
        Initialize mailbox analyzer.

        Args:
            credentials_path: Path to Gmail OAuth credentials JSON
            user_email: User's email address
        """
        self.credentials_path = Path(credentials_path)
        self.user_email = user_email
        self.service = None
        self.stats = defaultdict(int)
        self.sender_patterns = defaultdict(int)
        self.subject_keywords = Counter()
        self.domain_stats = defaultdict(int)
        self.bot_indicators = defaultdict(int)
        self.time_patterns = defaultdict(int)
        self.content_stats = {
            'avg_length': 0,
            'url_count': 0,
            'html_ratio': 0,
            'attachment_count': 0
        }

        if USE_SECURE_STORAGE:
            self.cred_manager = CredentialManager()
        else:
            self.cred_manager = None

    def authenticate(self):
        """Authenticate with Gmail API."""
        print("\n" + "="*70)
        print("AUTHENTICATING WITH GMAIL")
        print("="*70)

        creds = None

        # Try to load existing credentials
        if USE_SECURE_STORAGE:
            token_data = self.cred_manager.get_oauth_token(self.user_email)
            if token_data:
                creds = Credentials(
                    token=token_data.get('token'),
                    refresh_token=token_data.get('refresh_token'),
                    token_uri=token_data.get('token_uri'),
                    client_id=token_data.get('client_id'),
                    client_secret=token_data.get('client_secret'),
                    scopes=token_data.get('scopes', self.SCOPES)
                )
                print("✓ Loaded credentials from secure keyring")
        else:
            # Legacy token.pickle method
            token_path = Path('token.pickle')
            if token_path.exists():
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)
                print("✓ Loaded credentials from token.pickle")

        # Refresh or get new credentials
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired credentials...")
            creds.refresh(Request())
            print("✓ Credentials refreshed")
        elif not creds or not creds.valid:
            print("Starting OAuth flow...")
            if not self.credentials_path.exists():
                print(f"❌ Credentials file not found: {self.credentials_path}")
                print("\nTo get credentials:")
                print("1. Go to https://console.cloud.google.com/")
                print("2. Create a project and enable Gmail API")
                print("3. Create OAuth 2.0 credentials (Desktop app)")
                print("4. Download JSON and save as credentials.json")
                sys.exit(1)

            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_path),
                self.SCOPES
            )
            creds = flow.run_local_server(port=0)
            print("✓ New credentials obtained")

        # Save credentials
        if USE_SECURE_STORAGE:
            token_data = {
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': creds.scopes,
                'expiry': creds.expiry.isoformat() if creds.expiry else None
            }
            self.cred_manager.store_oauth_token(self.user_email, token_data)
            print("✓ Credentials saved to secure keyring")
        else:
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
            print("✓ Credentials saved to token.pickle")

        # Build service
        self.service = build('gmail', 'v1', credentials=creds)
        print("✓ Gmail API service initialized")

        return True

    def fetch_emails(self, max_emails: int = 1000, months_back: int = 24):
        """
        Fetch emails for analysis.

        Args:
            max_emails: Maximum number of emails to fetch
            months_back: How many months back to analyze

        Returns:
            List of email message objects
        """
        print(f"\n" + "="*70)
        print(f"FETCHING EMAILS (up to {max_emails} from last {months_back} months)")
        print("="*70)

        # Calculate date range
        after_date = datetime.now() - timedelta(days=months_back * 30)
        query = f'after:{after_date.strftime("%Y/%m/%d")}'

        try:
            # Get message IDs
            print("Fetching message list...")
            messages = []
            page_token = None

            while len(messages) < max_emails:
                results = self.service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=min(500, max_emails - len(messages)),
                    pageToken=page_token
                ).execute()

                batch = results.get('messages', [])
                messages.extend(batch)

                page_token = results.get('nextPageToken')
                print(f"  Found {len(messages)} messages so far...")

                if not page_token:
                    break

            print(f"✓ Found {len(messages)} total messages")

            # Fetch full message details (in batches for efficiency)
            print("\nFetching message details...")
            full_messages = []

            for i, msg in enumerate(messages, 1):
                if i % 50 == 0:
                    print(f"  Progress: {i}/{len(messages)} ({i*100//len(messages)}%)")

                try:
                    full_msg = self.service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='full'
                    ).execute()
                    full_messages.append(full_msg)
                except Exception as e:
                    print(f"  ⚠ Failed to fetch message {msg['id']}: {e}")
                    continue

            print(f"✓ Fetched {len(full_messages)} complete messages")
            return full_messages

        except Exception as e:
            print(f"❌ Error fetching emails: {e}")
            return []

    def analyze_email(self, message: Dict) -> Dict:
        """Analyze a single email for patterns."""
        headers = {h['name'].lower(): h['value'] for h in message['payload'].get('headers', [])}

        # Extract key fields
        sender = headers.get('from', '')
        subject = headers.get('subject', '')
        date_str = headers.get('date', '')

        # Parse sender domain
        sender_domain = ''
        if '@' in sender:
            sender_domain = sender.split('@')[-1].strip('>')

        # Get body
        body = self._get_body(message['payload'])

        # Analyze bot indicators
        bot_score = 0
        bot_indicators_found = []

        # Header-based indicators
        if 'list-unsubscribe' in headers:
            bot_score += 0.8
            bot_indicators_found.append('list-unsubscribe')
        if 'precedence' in headers and 'bulk' in headers['precedence'].lower():
            bot_score += 0.9
            bot_indicators_found.append('precedence: bulk')
        if any(h.startswith('x-marketing') or h.startswith('x-campaign') for h in headers):
            bot_score += 0.85
            bot_indicators_found.append('marketing headers')
        if 'auto-submitted' in headers:
            bot_score += 0.9
            bot_indicators_found.append('auto-submitted')

        # Sender-based indicators
        sender_lower = sender.lower()
        if any(keyword in sender_lower for keyword in ['noreply', 'no-reply', 'donotreply', 'auto@']):
            bot_score += 0.85
            bot_indicators_found.append('noreply sender')

        # Content-based indicators
        if body:
            body_lower = body.lower()
            keywords = ['unsubscribe', 'click here', 'special offer', 'limited time']
            found_keywords = [kw for kw in keywords if kw in body_lower]
            if found_keywords:
                bot_score += len(found_keywords) * 0.3
                bot_indicators_found.extend(found_keywords)

            # URL count
            url_count = len(re.findall(r'https?://', body))
            if url_count > 5:
                bot_score += 0.5
                bot_indicators_found.append(f'{url_count} URLs')

        # Parse time
        hour_of_day = None
        try:
            # Parse date header (format varies)
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(date_str)
            hour_of_day = dt.hour
        except:
            pass

        return {
            'sender': sender,
            'sender_domain': sender_domain,
            'subject': subject,
            'date': date_str,
            'hour': hour_of_day,
            'body_length': len(body) if body else 0,
            'headers': headers,
            'bot_score': min(bot_score, 1.0),
            'bot_indicators': bot_indicators_found,
            'is_likely_bot': bot_score > 0.5
        }

    def _get_body(self, payload: Dict) -> str:
        """Extract email body from payload."""
        body = ""

        if 'body' in payload and 'data' in payload['body']:
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
        elif 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                        break

        return body

    def analyze_patterns(self, messages: List[Dict]):
        """Analyze all messages for patterns."""
        print("\n" + "="*70)
        print("ANALYZING EMAIL PATTERNS")
        print("="*70)

        total_body_length = 0
        human_count = 0
        bot_count = 0

        for i, msg in enumerate(messages, 1):
            if i % 100 == 0:
                print(f"  Analyzing: {i}/{len(messages)} ({i*100//len(messages)}%)")

            analysis = self.analyze_email(msg)

            # Update statistics
            self.sender_patterns[analysis['sender']] += 1
            self.domain_stats[analysis['sender_domain']] += 1

            if analysis['is_likely_bot']:
                bot_count += 1
            else:
                human_count += 1

            # Subject keywords
            subject_words = analysis['subject'].lower().split()
            for word in subject_words:
                if len(word) > 3:  # Ignore short words
                    self.subject_keywords[word] += 1

            # Bot indicators
            for indicator in analysis['bot_indicators']:
                self.bot_indicators[indicator] += 1

            # Time patterns
            if analysis['hour'] is not None:
                self.time_patterns[analysis['hour']] += 1

            # Body length
            total_body_length += analysis['body_length']

        # Calculate averages
        self.content_stats['avg_length'] = total_body_length / len(messages) if messages else 0

        # Store counts
        self.stats['total_emails'] = len(messages)
        self.stats['human_emails'] = human_count
        self.stats['bot_emails'] = bot_count
        self.stats['unique_senders'] = len(self.sender_patterns)
        self.stats['unique_domains'] = len(self.domain_stats)

        print(f"✓ Analysis complete!")

    def print_report(self):
        """Print comprehensive analysis report."""
        print("\n" + "="*70)
        print("MAILBOX ANALYSIS REPORT")
        print("="*70)

        # Overall stats
        print("\n📊 OVERALL STATISTICS")
        print(f"  Total Emails Analyzed: {self.stats['total_emails']}")
        print(f"  Human-generated: {self.stats['human_emails']} ({self.stats['human_emails']*100//self.stats['total_emails']}%)")
        print(f"  Bot-generated: {self.stats['bot_emails']} ({self.stats['bot_emails']*100//self.stats['total_emails']}%)")
        print(f"  Unique Senders: {self.stats['unique_senders']}")
        print(f"  Unique Domains: {self.stats['unique_domains']}")
        print(f"  Avg Email Length: {self.content_stats['avg_length']:.0f} characters")

        # Top senders
        print("\n📧 TOP 15 SENDERS")
        for sender, count in sorted(self.sender_patterns.items(), key=lambda x: x[1], reverse=True)[:15]:
            print(f"  {count:4d}x {sender[:60]}")

        # Top domains
        print("\n🌐 TOP 15 DOMAINS")
        for domain, count in sorted(self.domain_stats.items(), key=lambda x: x[1], reverse=True)[:15]:
            print(f"  {count:4d}x {domain}")

        # Bot indicators
        print("\n🤖 TOP BOT INDICATORS FOUND")
        for indicator, count in sorted(self.bot_indicators.items(), key=lambda x: x[1], reverse=True)[:15]:
            print(f"  {count:4d}x {indicator}")

        # Subject keywords
        print("\n📝 TOP 20 SUBJECT KEYWORDS")
        for word, count in self.subject_keywords.most_common(20):
            print(f"  {count:4d}x {word}")

        # Time patterns
        print("\n🕐 EMAIL TIMING PATTERNS (by hour)")
        if self.time_patterns:
            for hour in range(24):
                count = self.time_patterns.get(hour, 0)
                bar = "█" * (count // 10) if count > 0 else ""
                print(f"  {hour:02d}:00 {count:4d} {bar}")

        # ML Recommendations
        print("\n" + "="*70)
        print("ML MODEL RECOMMENDATIONS")
        print("="*70)

        bot_ratio = self.stats['bot_emails'] / self.stats['total_emails'] if self.stats['total_emails'] > 0 else 0

        print(f"\n📊 Data Characteristics:")
        print(f"  - Bot/Human ratio: {bot_ratio:.1%} bots")
        print(f"  - Sender diversity: {self.stats['unique_senders']} unique senders")
        print(f"  - Domain diversity: {self.stats['unique_domains']} unique domains")

        print(f"\n💡 Recommended ML Approach:")

        if self.stats['total_emails'] < 500:
            print("  ⚠️  LIMITED DATA: Consider using rule-based + simple ML")
            print("     - Start with enhanced rule-based classification")
            print("     - Add Random Forest for pattern learning")
            print("     - Collect more data through active learning")
        elif bot_ratio > 0.7:
            print("  ✅ HIGH BOT VOLUME: Ensemble approach ideal")
            print("     - Random Forest for rule-based patterns")
            print("     - Gradient Boosting for edge cases")
            print("     - Lightweight transformer for semantic understanding")
            print("     - Clear bot/human separation should yield high accuracy")
        else:
            print("  ✅ BALANCED DATA: Full ensemble recommended")
            print("     - Traditional ML (RF + GB) for explicit patterns")
            print("     - Transformer model for nuanced human emails")
            print("     - Ensemble voting for best accuracy")
            print("     - Active learning crucial for edge cases")

        print(f"\n🎯 Key Features to Extract:")
        print("  1. Sender patterns (email, domain, noreply indicators)")
        print("  2. Header analysis (authentication, bulk, automation markers)")
        print("  3. Content features (length, URLs, keywords, formatting)")
        print("  4. Temporal patterns (send time, business hours)")
        print("  5. Historical behavior (user's past interactions)")

        print(f"\n📈 Expected Performance:")
        if bot_ratio > 0.7:
            print("  - Estimated accuracy: 90-95% (clear bot patterns)")
            print("  - Main challenge: Nuanced human emails")
            print("  - Active learning impact: High (for human edge cases)")
        else:
            print("  - Estimated accuracy: 85-92% (mixed patterns)")
            print("  - Main challenge: Distinguishing automated vs personal")
            print("  - Active learning impact: Critical")

    def save_report(self, output_path: str = "mailbox_analysis.json"):
        """Save analysis results to JSON file."""
        report = {
            'stats': dict(self.stats),
            'top_senders': dict(sorted(self.sender_patterns.items(), key=lambda x: x[1], reverse=True)[:50]),
            'top_domains': dict(sorted(self.domain_stats.items(), key=lambda x: x[1], reverse=True)[:50]),
            'bot_indicators': dict(sorted(self.bot_indicators.items(), key=lambda x: x[1], reverse=True)),
            'subject_keywords': dict(self.subject_keywords.most_common(100)),
            'time_patterns': dict(self.time_patterns),
            'content_stats': self.content_stats,
            'analysis_date': datetime.now().isoformat()
        }

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n✓ Report saved to: {output_path}")


def main():
    """Main analysis workflow."""
    print("\n" + "="*70)
    print("GMAIL MAILBOX ANALYZER")
    print("="*70)

    # Get configuration
    credentials_path = input("\nPath to Gmail credentials.json [./credentials.json]: ").strip() or "./credentials.json"
    user_email = input("Your Gmail address: ").strip()

    if not user_email:
        print("❌ Email address required")
        sys.exit(1)

    # Analysis parameters
    print("\nAnalysis Parameters:")
    max_emails_str = input("  Max emails to analyze [1000]: ").strip() or "1000"
    months_back_str = input("  Months back to analyze [24]: ").strip() or "24"

    try:
        max_emails = int(max_emails_str)
        months_back = int(months_back_str)
    except ValueError:
        print("❌ Invalid number")
        sys.exit(1)

    # Run analysis
    analyzer = MailboxAnalyzer(credentials_path, user_email)

    if not analyzer.authenticate():
        print("❌ Authentication failed")
        sys.exit(1)

    messages = analyzer.fetch_emails(max_emails, months_back)

    if not messages:
        print("❌ No messages fetched")
        sys.exit(1)

    analyzer.analyze_patterns(messages)
    analyzer.print_report()
    analyzer.save_report()

    print("\n" + "="*70)
    print("✅ ANALYSIS COMPLETE")
    print("="*70)
    print("\nNext steps:")
    print("1. Review the analysis above")
    print("2. Check mailbox_analysis.json for detailed data")
    print("3. Ready to build ML model based on these insights!")


if __name__ == "__main__":
    main()
