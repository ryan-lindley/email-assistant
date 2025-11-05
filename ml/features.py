"""
Feature Extraction Pipeline for Email Classification

Extracts 50+ features from emails for ML model training and prediction.

Features are grouped into categories:
- Metadata features (headers, authentication)
- Content features (length, URLs, keywords, formatting)
- Sender features (domain, patterns, reputation)
- Temporal features (timing, business hours)
- Behavioral features (historical patterns)
- Structural features (recipients, attachments, threading)
"""

import re
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class EmailFeatures:
    """Container for extracted email features."""

    # Feature dictionary
    features: Dict[str, Any]

    # Metadata
    email_id: Optional[str] = None
    extraction_time: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for ML model."""
        return self.features

    def feature_vector(self) -> List[float]:
        """Convert to numeric feature vector."""
        # Convert all features to numeric values
        vector = []
        for key in sorted(self.features.keys()):
            value = self.features[key]
            if isinstance(value, bool):
                vector.append(1.0 if value else 0.0)
            elif isinstance(value, (int, float)):
                vector.append(float(value))
            else:
                # For string features, use hash or skip
                vector.append(0.0)
        return vector


class EmailFeatureExtractor:
    """
    Extract comprehensive features from emails for ML classification.

    Extracts 50+ features covering metadata, content, sender patterns,
    temporal characteristics, and behavioral patterns.
    """

    # Bot indicator keywords
    BOT_KEYWORDS = {
        'unsubscribe', 'newsletter', 'marketing', 'subscription',
        'promotional', 'advertisement', 'click here', 'special offer',
        'limited time', 'act now', 'don\'t miss', 'exclusive deal',
        'sale', 'discount', 'coupon', 'free shipping'
    }

    # Urgency indicators
    URGENCY_WORDS = {
        'urgent', 'immediately', 'asap', 'critical', 'important',
        'action required', 'time-sensitive', 'expiring', 'deadline',
        'final notice', 'last chance', 'ending soon'
    }

    # Automated sender patterns
    AUTOMATED_SENDER_PATTERNS = [
        r'noreply', r'no-reply', r'donotreply', r'do-not-reply',
        r'auto@', r'automated@', r'robot@', r'bot@',
        r'notification', r'alert', r'system'
    ]

    def __init__(self, sender_stats: Optional[Dict[str, Dict]] = None):
        """
        Initialize feature extractor.

        Args:
            sender_stats: Historical statistics about senders
                         {sender_email: {total: int, read_rate: float, reply_rate: float, ...}}
        """
        self.sender_stats = sender_stats or {}

    def extract_features(
        self,
        message_id: str,
        sender: str,
        recipients: List[str],
        subject: str,
        body_text: Optional[str],
        body_html: Optional[str],
        headers: Dict[str, str],
        date_received: datetime,
        labels: Optional[List[str]] = None,
        thread_id: Optional[str] = None
    ) -> EmailFeatures:
        """
        Extract all features from an email.

        Args:
            message_id: Unique message identifier
            sender: Sender email address
            recipients: List of recipient email addresses
            subject: Email subject line
            body_text: Plain text body
            body_html: HTML body
            headers: Email headers dictionary
            date_received: When email was received
            labels: Email labels/categories
            thread_id: Thread identifier for conversations

        Returns:
            EmailFeatures object with all extracted features
        """
        features = {}

        # Extract features from each category
        features.update(self._extract_metadata_features(headers))
        features.update(self._extract_content_features(subject, body_text, body_html))
        features.update(self._extract_sender_features(sender))
        features.update(self._extract_temporal_features(date_received))
        features.update(self._extract_structural_features(
            recipients, headers, body_text, labels, thread_id
        ))
        features.update(self._extract_behavioral_features(sender))

        return EmailFeatures(
            features=features,
            email_id=message_id,
            extraction_time=datetime.now()
        )

    def _extract_metadata_features(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """Extract features from email headers."""
        features = {}

        # Normalize header keys to lowercase
        headers_lower = {k.lower(): v for k, v in headers.items()}

        # Bot indicator headers
        features['has_list_unsubscribe'] = 'list-unsubscribe' in headers_lower
        features['has_bulk_precedence'] = (
            'precedence' in headers_lower and
            'bulk' in headers_lower.get('precedence', '').lower()
        )
        features['has_marketing_headers'] = any(
            'marketing' in k or 'campaign' in k
            for k in headers_lower.keys()
        )
        features['has_auto_submitted'] = 'auto-submitted' in headers_lower
        features['has_autoreply'] = 'x-autoreply' in headers_lower

        # Email client detection
        mailer = headers_lower.get('x-mailer', '').lower()
        user_agent = headers_lower.get('user-agent', '').lower()
        features['sent_via_api'] = bool(mailer and not user_agent)
        features['mailer_is_automated'] = any(
            word in mailer for word in ['mailchimp', 'sendgrid', 'constant contact', 'bulk']
        )

        # Authentication results
        features['spf_pass'] = 'pass' in headers_lower.get('received-spf', '').lower()
        dkim = headers_lower.get('dkim-signature', '')
        features['has_dkim'] = bool(dkim)

        # Header count (more headers often = automated)
        features['header_count'] = len(headers)

        return features

    def _extract_content_features(
        self,
        subject: str,
        body_text: Optional[str],
        body_html: Optional[str]
    ) -> Dict[str, Any]:
        """Extract features from email content."""
        features = {}

        # Subject features
        subject_lower = subject.lower() if subject else ''
        features['subject_length'] = len(subject) if subject else 0
        features['subject_has_re'] = subject_lower.startswith('re:')
        features['subject_has_fwd'] = subject_lower.startswith('fwd:') or subject_lower.startswith('fw:')
        features['subject_all_caps_ratio'] = (
            sum(1 for c in subject if c.isupper()) / len(subject)
            if subject else 0.0
        )
        features['subject_exclamation_count'] = subject.count('!') if subject else 0

        # Body text features
        body = body_text or ''
        features['body_length'] = len(body)
        features['body_word_count'] = len(body.split()) if body else 0
        features['avg_sentence_length'] = (
            features['body_word_count'] / max(1, body.count('.') + body.count('!') + body.count('?'))
            if body else 0.0
        )

        # URL features
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, body)
        features['url_count'] = len(urls)

        # Extract unique domains from URLs
        domain_pattern = r'https?://([^/\s]+)'
        domains = set(re.findall(domain_pattern, body))
        features['unique_domain_count'] = len(domains)

        # Shortened URL detection
        short_domains = {'bit.ly', 'tinyurl.com', 'goo.gl', 't.co', 'ow.ly'}
        features['shortened_url_count'] = sum(
            1 for d in domains if any(short in d for short in short_domains)
        )

        features['url_to_text_ratio'] = (
            features['url_count'] / max(1, features['body_word_count'])
            if features['body_word_count'] > 0 else 0.0
        )

        # Marketing indicators in content
        body_lower = body.lower()
        features['unsubscribe_link_count'] = body_lower.count('unsubscribe')
        features['has_view_in_browser'] = 'view in browser' in body_lower or 'view online' in body_lower

        # Tracking pixel detection (1x1 images)
        if body_html:
            tracking_pixel_pattern = r'<img[^>]*(?:width|height)\s*=\s*["\']?1["\']?[^>]*>'
            features['tracking_pixel_count'] = len(re.findall(tracking_pixel_pattern, body_html, re.IGNORECASE))
        else:
            features['tracking_pixel_count'] = 0

        # Content patterns
        features['exclamation_count'] = body.count('!')
        features['all_caps_word_count'] = len([w for w in body.split() if w.isupper() and len(w) > 2])
        features['currency_mention_count'] = (
            body.count('$') + body.count('€') + body.count('£') +
            body_lower.count('price') + body_lower.count('cost')
        )
        features['percentage_mention_count'] = body.count('%')

        # Urgency words
        features['urgency_word_count'] = sum(
            1 for word in self.URGENCY_WORDS if word in body_lower
        )

        # Bot keywords
        features['bot_keyword_count'] = sum(
            1 for keyword in self.BOT_KEYWORDS if keyword in body_lower
        )

        features['question_count'] = body.count('?')

        # Personalization tokens (common in mass emails)
        personalization_patterns = [
            r'\{\{[^}]+\}\}',  # {{name}}
            r'\[NAME\]', r'\[FIRSTNAME\]', r'\[EMAIL\]',  # [NAME]
            r'%[A-Z_]+%'  # %FIRST_NAME%
        ]
        features['has_personalization_tokens'] = any(
            re.search(pattern, body, re.IGNORECASE)
            for pattern in personalization_patterns
        )

        # HTML features
        if body_html:
            features['html_to_text_ratio'] = len(body_html) / max(1, len(body)) if body else 0.0
            features['table_count'] = body_html.lower().count('<table')
            features['image_count'] = body_html.lower().count('<img')
            features['has_inline_css'] = 'style=' in body_html.lower()
        else:
            features['html_to_text_ratio'] = 0.0
            features['table_count'] = 0
            features['image_count'] = 0
            features['has_inline_css'] = False

        return features

    def _extract_sender_features(self, sender: str) -> Dict[str, Any]:
        """Extract features from sender email address."""
        features = {}

        sender_lower = sender.lower()

        # Extract email and domain
        if '@' in sender:
            local_part, domain = sender_lower.split('@', 1)
        else:
            local_part, domain = sender_lower, ''

        # Automated sender detection
        features['sender_is_noreply'] = any(
            pattern in sender_lower
            for pattern in ['noreply', 'no-reply', 'donotreply']
        )

        features['sender_is_automated'] = any(
            re.search(pattern, sender_lower)
            for pattern in self.AUTOMATED_SENDER_PATTERNS
        )

        # Domain characteristics
        domain_parts = domain.split('.')
        features['sender_has_subdomain'] = len(domain_parts) > 2
        features['sender_domain_length'] = len(domain)

        # Local part characteristics
        features['sender_local_has_numbers'] = bool(re.search(r'\d', local_part))
        features['sender_local_length'] = len(local_part)

        # Historical sender statistics
        if sender_lower in self.sender_stats:
            stats = self.sender_stats[sender_lower]
            features['sender_email_count'] = stats.get('total', 0)
            features['sender_read_rate'] = stats.get('read_rate', 0.0)
            features['sender_reply_rate'] = stats.get('reply_rate', 0.0)
            features['sender_archive_rate'] = stats.get('archive_rate', 0.0)
            features['avg_user_priority_from_sender'] = stats.get('avg_priority', 0.5)
        else:
            # New sender
            features['sender_email_count'] = 0
            features['sender_read_rate'] = 0.0
            features['sender_reply_rate'] = 0.0
            features['sender_archive_rate'] = 0.0
            features['avg_user_priority_from_sender'] = 0.5  # Neutral

        return features

    def _extract_temporal_features(self, date_received: datetime) -> Dict[str, Any]:
        """Extract features from email timing."""
        features = {}

        features['hour_of_day'] = date_received.hour
        features['day_of_week'] = date_received.weekday()  # 0=Monday, 6=Sunday
        features['is_weekend'] = date_received.weekday() >= 5
        features['is_business_hours'] = 9 <= date_received.hour <= 17
        features['is_night_send'] = date_received.hour < 6 or date_received.hour >= 22

        # Time buckets
        if 0 <= date_received.hour < 6:
            time_bucket = 0  # Night
        elif 6 <= date_received.hour < 12:
            time_bucket = 1  # Morning
        elif 12 <= date_received.hour < 18:
            time_bucket = 2  # Afternoon
        else:
            time_bucket = 3  # Evening

        features['time_bucket'] = time_bucket

        return features

    def _extract_structural_features(
        self,
        recipients: List[str],
        headers: Dict[str, str],
        body_text: Optional[str],
        labels: Optional[List[str]],
        thread_id: Optional[str]
    ) -> Dict[str, Any]:
        """Extract features from email structure."""
        features = {}

        # Recipient features
        features['recipient_count'] = len(recipients)
        features['is_to_multiple'] = len(recipients) > 1

        # CC/BCC (if available in headers)
        headers_lower = {k.lower(): v for k, v in headers.items()}
        cc = headers_lower.get('cc', '')
        features['cc_count'] = len(cc.split(',')) if cc else 0

        # Threading
        features['is_reply'] = headers_lower.get('in-reply-to') is not None
        features['is_forward'] = 'fwd:' in headers_lower.get('subject', '').lower()

        # Labels
        if labels:
            features['has_inbox_label'] = 'INBOX' in labels
            features['has_important_label'] = 'IMPORTANT' in labels
            features['label_count'] = len(labels)
        else:
            features['has_inbox_label'] = True  # Default assumption
            features['has_important_label'] = False
            features['label_count'] = 0

        # Attachments (if we can detect from body or headers)
        body = body_text or ''
        features['has_attachment'] = (
            'attachment' in headers_lower.get('content-type', '').lower() or
            'attached' in body.lower()
        )

        return features

    def _extract_behavioral_features(self, sender: str) -> Dict[str, Any]:
        """Extract features based on user's historical behavior with this sender."""
        features = {}

        sender_lower = sender.lower()

        if sender_lower in self.sender_stats:
            stats = self.sender_stats[sender_lower]

            # How user typically interacts with this sender
            features['user_typically_reads'] = stats.get('read_rate', 0.0) > 0.5
            features['user_typically_replies'] = stats.get('reply_rate', 0.0) > 0.3
            features['user_typically_archives'] = stats.get('archive_rate', 0.0) > 0.5
            features['user_typically_deletes'] = stats.get('delete_rate', 0.0) > 0.3
        else:
            # Unknown sender - neutral assumptions
            features['user_typically_reads'] = False
            features['user_typically_replies'] = False
            features['user_typically_archives'] = False
            features['user_typically_deletes'] = False

        return features

    def get_feature_names(self) -> List[str]:
        """Get list of all feature names in order."""
        # Extract features from a dummy email to get feature names
        dummy_features = self.extract_features(
            message_id='dummy',
            sender='dummy@example.com',
            recipients=['user@example.com'],
            subject='Dummy Subject',
            body_text='Dummy body',
            body_html=None,
            headers={'from': 'dummy@example.com'},
            date_received=datetime.now()
        )

        return sorted(dummy_features.features.keys())

    def get_feature_count(self) -> int:
        """Get total number of features extracted."""
        return len(self.get_feature_names())


# Convenience function
def extract_email_features(
    message_id: str,
    sender: str,
    recipients: List[str],
    subject: str,
    body_text: Optional[str],
    body_html: Optional[str],
    headers: Dict[str, str],
    date_received: datetime,
    labels: Optional[List[str]] = None,
    thread_id: Optional[str] = None,
    sender_stats: Optional[Dict[str, Dict]] = None
) -> EmailFeatures:
    """
    Convenience function to extract features from an email.

    Returns:
        EmailFeatures object with all extracted features
    """
    extractor = EmailFeatureExtractor(sender_stats=sender_stats)
    return extractor.extract_features(
        message_id=message_id,
        sender=sender,
        recipients=recipients,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        headers=headers,
        date_received=date_received,
        labels=labels,
        thread_id=thread_id
    )
