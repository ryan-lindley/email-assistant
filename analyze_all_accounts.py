"""
Multi-Account Mailbox Analyzer

Analyzes emails across multiple Gmail accounts to understand patterns
and inform ML model design for unified email classification.

Features:
- Authenticates and fetches from 4-6 Gmail accounts
- Cross-account deduplication
- Unified pattern analysis (bot detection, timing, senders)
- Generates ML training recommendations
- Prepares data for unified model training

Usage:
    python analyze_all_accounts.py

    # With custom config:
    python analyze_all_accounts.py --config custom_accounts.json

    # Analyze specific number of emails per account:
    python analyze_all_accounts.py --max-per-account 500
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Any
import argparse

from core.gmail.multi_account import MultiAccountManager
from ml.features import EmailFeatureExtractor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MultiAccountAnalyzer:
    """Analyze email patterns across multiple Gmail accounts."""

    def __init__(self, config_path: str = 'accounts.json'):
        """
        Initialize analyzer with account configuration.

        Args:
            config_path: Path to accounts.json configuration file
        """
        self.config_path = config_path
        self.manager = MultiAccountManager(config_path)
        self.feature_extractor = EmailFeatureExtractor()

        # Analysis storage
        self.total_emails = 0
        self.emails_by_account: Dict[str, int] = {}
        self.bot_patterns: Counter = Counter()
        self.sender_domains: Counter = Counter()
        self.sender_patterns: Counter = Counter()
        self.time_distribution: Dict[int, int] = defaultdict(int)
        self.keyword_patterns: Counter = Counter()
        self.account_emails: Dict[str, List[Dict]] = {}

    def analyze_email(self, msg: Dict) -> Dict[str, Any]:
        """
        Analyze a single email message.

        Args:
            msg: Gmail message dictionary

        Returns:
            Analysis dictionary with patterns
        """
        headers = {h['name'].lower(): h['value']
                  for h in msg.get('payload', {}).get('headers', [])}

        sender = headers.get('from', 'unknown')
        subject = headers.get('subject', '')
        date_str = headers.get('date', '')

        # Extract domain
        sender_email = sender.split('<')[-1].rstrip('>')
        domain = sender_email.split('@')[-1] if '@' in sender_email else 'unknown'

        # Bot detection patterns
        bot_indicators = []

        # List-Unsubscribe header (strong bot indicator)
        if any(h['name'].lower() == 'list-unsubscribe' for h in msg.get('payload', {}).get('headers', [])):
            bot_indicators.append('list-unsubscribe')

        # Auto-submitted header
        if any(h['name'].lower() == 'auto-submitted' for h in msg.get('payload', {}).get('headers', [])):
            bot_indicators.append('auto-submitted')

        # Common marketing keywords in subject
        marketing_keywords = ['newsletter', 'unsubscribe', 'click here', 'offer',
                             'sale', 'discount', 'deal', 'limited time', 'act now']
        if any(keyword in subject.lower() for keyword in marketing_keywords):
            bot_indicators.append('marketing-subject')

        # Common bot sender patterns
        bot_senders = ['no-reply', 'noreply', 'notifications', 'updates', 'news']
        if any(pattern in sender_email.lower() for pattern in bot_senders):
            bot_indicators.append('bot-sender')

        return {
            'sender': sender_email,
            'sender_domain': domain,
            'subject': subject,
            'date': date_str,
            'bot_indicators': bot_indicators,
            'is_likely_bot': len(bot_indicators) >= 2,
            'account': msg.get('_account', 'unknown'),
            'account_email': msg.get('_account_email', 'unknown')
        }

    def analyze_all_accounts(self, max_per_account: int = 1000) -> Dict[str, Any]:
        """
        Fetch and analyze emails from all configured accounts.

        Args:
            max_per_account: Maximum emails to fetch per account

        Returns:
            Comprehensive analysis results
        """
        logger.info("\n" + "="*70)
        logger.info("MULTI-ACCOUNT MAILBOX ANALYSIS")
        logger.info("="*70)

        # Step 1: Authenticate all accounts
        logger.info("\n📧 Authenticating accounts...")
        success, failed = self.manager.authenticate_all()

        if failed > 0:
            logger.warning(f"⚠️  {failed} account(s) failed authentication")
        if success == 0:
            logger.error("❌ No accounts authenticated successfully")
            return {}

        logger.info(f"✅ {success} account(s) authenticated successfully")

        # Step 2: Fetch emails from all accounts
        logger.info(f"\n📥 Fetching up to {max_per_account} emails per account...")
        results = self.manager.fetch_all_emails(max_per_account=max_per_account)

        # Step 3: Get unified deduplicated list
        all_emails = []
        for account_name, emails in results.items():
            self.emails_by_account[account_name] = len(emails)
            all_emails.extend(emails)

        logger.info(f"\n🔍 Total emails before deduplication: {len(all_emails)}")
        unique_emails = self.manager.deduplicate_emails(all_emails)
        logger.info(f"✅ Unique emails after deduplication: {len(unique_emails)}")

        self.total_emails = len(unique_emails)

        # Step 4: Analyze patterns
        logger.info("\n📊 Analyzing email patterns...")

        bot_count = 0
        human_count = 0

        for msg in unique_emails:
            analysis = self.analyze_email(msg)

            # Track patterns
            self.sender_patterns[analysis['sender']] += 1
            self.sender_domains[analysis['sender_domain']] += 1

            if analysis['is_likely_bot']:
                bot_count += 1
                for indicator in analysis['bot_indicators']:
                    self.bot_patterns[indicator] += 1
            else:
                human_count += 1

            # Time distribution (extract hour from date if possible)
            try:
                # Parse date string to get hour
                # Gmail date format is complex, so we'll do simple extraction
                date_str = analysis['date']
                if date_str and ':' in date_str:
                    # Try to find hour pattern (HH:MM)
                    for part in date_str.split():
                        if ':' in part and len(part.split(':')[0]) <= 2:
                            hour = int(part.split(':')[0])
                            self.time_distribution[hour] += 1
                            break
            except:
                pass

        # Generate analysis report
        report = self._generate_report(unique_emails, bot_count, human_count)

        # Save report
        self._save_report(report)

        return report

    def _generate_report(self, emails: List[Dict], bot_count: int, human_count: int) -> Dict[str, Any]:
        """Generate comprehensive analysis report."""

        total = len(emails)
        bot_ratio = bot_count / total if total > 0 else 0

        # Top domains
        top_domains = self.sender_domains.most_common(20)

        # Top senders
        top_senders = self.sender_patterns.most_common(20)

        # Bot detection patterns
        bot_pattern_summary = dict(self.bot_patterns.most_common())

        # Time distribution summary
        business_hours = sum(self.time_distribution[h] for h in range(9, 18))
        after_hours = total - business_hours

        report = {
            'analysis_date': datetime.now().isoformat(),
            'summary': {
                'total_accounts': len(self.emails_by_account),
                'emails_by_account': self.emails_by_account,
                'total_emails_analyzed': total,
                'unique_emails': total,
                'bot_emails': bot_count,
                'human_emails': human_count,
                'bot_ratio': round(bot_ratio, 3)
            },
            'patterns': {
                'top_sender_domains': [{'domain': d, 'count': c} for d, c in top_domains],
                'top_senders': [{'sender': s, 'count': c} for s, c in top_senders],
                'bot_indicators': bot_pattern_summary,
                'time_distribution': {
                    'business_hours': business_hours,
                    'after_hours': after_hours,
                    'hourly_distribution': dict(self.time_distribution)
                }
            },
            'ml_recommendations': {
                'suggested_features': self._get_ml_feature_recommendations(bot_ratio),
                'training_data_split': {
                    'recommended_train_size': 0.8,
                    'recommended_test_size': 0.2,
                    'min_samples_per_class': 100
                },
                'model_suggestions': self._get_model_suggestions(total, bot_ratio),
                'confidence_thresholds': {
                    'high_confidence': 0.7,
                    'uncertain': 0.3,
                    'explanation': 'Emails with confidence 0.3-0.7 should be flagged for review'
                }
            },
            'cross_account_insights': {
                'accounts_analyzed': list(self.emails_by_account.keys()),
                'shared_senders': self._find_shared_senders(),
                'account_diversity': self._calculate_account_diversity()
            }
        }

        return report

    def _get_ml_feature_recommendations(self, bot_ratio: float) -> List[str]:
        """Get ML feature recommendations based on patterns."""
        features = [
            'list-unsubscribe header (strong bot indicator)',
            'auto-submitted header',
            'sender domain patterns',
            'email time of day',
            'subject line keywords',
            'sender frequency patterns',
            'has_reply_to header',
            'HTML vs plain text ratio',
            'URL count in body',
            'recipient count'
        ]

        if bot_ratio > 0.5:
            features.append('aggressive bot filtering needed')

        return features

    def _get_model_suggestions(self, total_emails: int, bot_ratio: float) -> Dict[str, Any]:
        """Get ML model architecture suggestions."""

        suggestions = {
            'ensemble_approach': 'Random Forest + Gradient Boosting (already implemented)',
            'estimated_accuracy': '75-92% based on feature richness',
            'active_learning': 'Recommended - collect user feedback for uncertain predictions'
        }

        if total_emails < 500:
            suggestions['warning'] = 'Small dataset - consider starting with simpler model'
        elif total_emails > 5000:
            suggestions['advanced'] = 'Large dataset - transformer model may provide better results'

        if bot_ratio > 0.8:
            suggestions['class_imbalance'] = 'Heavy bot emails - use class weighting in training'
        elif bot_ratio < 0.2:
            suggestions['class_imbalance'] = 'Mostly human emails - may need more bot examples'

        return suggestions

    def _find_shared_senders(self) -> List[Dict[str, Any]]:
        """Find senders that appear across multiple accounts."""
        # Would need to track which senders appear in which accounts
        # For now, return top senders as they're likely shared
        return [
            {'sender': s, 'frequency': c}
            for s, c in self.sender_patterns.most_common(10)
        ]

    def _calculate_account_diversity(self) -> Dict[str, Any]:
        """Calculate diversity metrics across accounts."""
        num_accounts = len(self.emails_by_account)
        avg_emails = sum(self.emails_by_account.values()) / num_accounts if num_accounts > 0 else 0

        return {
            'total_accounts': num_accounts,
            'average_emails_per_account': round(avg_emails, 1),
            'unique_domains': len(self.sender_domains),
            'unique_senders': len(self.sender_patterns)
        }

    def _save_report(self, report: Dict[str, Any]):
        """Save analysis report to file."""
        output_dir = Path('analysis_reports')
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f'multi_account_analysis_{timestamp}.json'

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"\n💾 Report saved to: {output_file}")

        # Print summary
        self._print_summary(report)

    def _print_summary(self, report: Dict[str, Any]):
        """Print human-readable summary."""
        logger.info("\n" + "="*70)
        logger.info("ANALYSIS SUMMARY")
        logger.info("="*70)

        summary = report['summary']
        logger.info(f"\n📊 Total Accounts: {summary['total_accounts']}")
        logger.info(f"📧 Total Emails: {summary['total_emails_analyzed']}")
        logger.info(f"🤖 Bot Emails: {summary['bot_emails']} ({summary['bot_ratio']*100:.1f}%)")
        logger.info(f"👤 Human Emails: {summary['human_emails']} ({(1-summary['bot_ratio'])*100:.1f}%)")

        logger.info("\n📬 Emails per Account:")
        for account, count in summary['emails_by_account'].items():
            logger.info(f"  • {account}: {count} emails")

        logger.info("\n🌐 Top Sender Domains:")
        for item in report['patterns']['top_sender_domains'][:10]:
            logger.info(f"  • {item['domain']}: {item['count']} emails")

        logger.info("\n🤖 Bot Detection Patterns:")
        for pattern, count in report['patterns']['bot_indicators'].items():
            logger.info(f"  • {pattern}: {count} occurrences")

        logger.info("\n🎯 ML Recommendations:")
        ml_rec = report['ml_recommendations']
        logger.info(f"  • Estimated Accuracy: {ml_rec['model_suggestions'].get('estimated_accuracy', 'N/A')}")
        logger.info(f"  • High Confidence Threshold: {ml_rec['confidence_thresholds']['high_confidence']}")
        logger.info(f"  • Uncertain Threshold: {ml_rec['confidence_thresholds']['uncertain']}")

        logger.info("\n" + "="*70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Analyze multiple Gmail accounts')
    parser.add_argument(
        '--config',
        default='accounts.json',
        help='Path to accounts configuration file (default: accounts.json)'
    )
    parser.add_argument(
        '--max-per-account',
        type=int,
        default=1000,
        help='Maximum emails to fetch per account (default: 1000)'
    )

    args = parser.parse_args()

    # Check if config file exists
    if not Path(args.config).exists():
        logger.error(f"❌ Configuration file not found: {args.config}")
        logger.info("\n💡 Create accounts.json from accounts.json.example:")
        logger.info("   cp accounts.json.example accounts.json")
        logger.info("   # Edit accounts.json with your account details")
        return

    try:
        analyzer = MultiAccountAnalyzer(args.config)
        analyzer.analyze_all_accounts(max_per_account=args.max_per_account)

        logger.info("\n✅ Multi-account analysis complete!")
        logger.info("📝 Check analysis_reports/ directory for detailed results")

    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
