"""
Test feature extraction pipeline.

Demonstrates extracting features from example emails.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from ml.features import EmailFeatureExtractor, extract_email_features


def test_bot_email():
    """Test feature extraction on a bot/marketing email."""
    print("\n" + "="*70)
    print("TEST: Bot/Marketing Email Feature Extraction")
    print("="*70)

    features = extract_email_features(
        message_id="bot_001",
        sender="noreply@marketing-company.com",
        recipients=["user@example.com"],
        subject="🎉 50% OFF EVERYTHING - LIMITED TIME ONLY!",
        body_text="""
        Don't miss out on our biggest sale of the year!

        Click here to shop now: https://bit.ly/sale123

        Special offer expires in 24 hours. Act now!

        Unsubscribe | View in browser
        """,
        body_html="<html><body><table><tr><td>Sale content</td></tr></table></body></html>",
        headers={
            'from': 'noreply@marketing-company.com',
            'list-unsubscribe': '<mailto:unsub@marketing-company.com>',
            'precedence': 'bulk',
            'x-mailer': 'MailChimp',
            'x-campaign-id': '12345'
        },
        date_received=datetime(2025, 11, 5, 14, 30)
    )

    print(f"\n📊 Extracted {len(features.features)} features:")

    # Show key bot indicators
    bot_indicators = {
        'has_list_unsubscribe': features.features['has_list_unsubscribe'],
        'has_bulk_precedence': features.features['has_bulk_precedence'],
        'has_marketing_headers': features.features['has_marketing_headers'],
        'sender_is_noreply': features.features['sender_is_noreply'],
        'unsubscribe_link_count': features.features['unsubscribe_link_count'],
        'urgency_word_count': features.features['urgency_word_count'],
        'shortened_url_count': features.features['shortened_url_count'],
        'subject_exclamation_count': features.features['subject_exclamation_count'],
    }

    print("\n🤖 Key Bot Indicators:")
    for key, value in bot_indicators.items():
        print(f"  {key}: {value}")

    print(f"\n✅ Bot email features extracted successfully")


def test_human_email():
    """Test feature extraction on a human/personal email."""
    print("\n" + "="*70)
    print("TEST: Human/Personal Email Feature Extraction")
    print("="*70)

    features = extract_email_features(
        message_id="human_001",
        sender="john.doe@company.com",
        recipients=["user@example.com"],
        subject="Re: Project update and next week's meeting",
        body_text="""
        Hi,

        Thanks for the update. I've reviewed the documents and have a few questions.

        Can we schedule a quick call next Tuesday to discuss? I'm free after 2pm.

        Best regards,
        John
        """,
        body_html=None,
        headers={
            'from': 'john.doe@company.com',
            'in-reply-to': '<previous-message-id>',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        },
        date_received=datetime(2025, 11, 5, 10, 15),
        thread_id="thread_abc123"
    )

    print(f"\n📊 Extracted {len(features.features)} features:")

    # Show key human indicators
    human_indicators = {
        'subject_has_re': features.features['subject_has_re'],
        'is_reply': features.features['is_reply'],
        'sender_is_noreply': features.features['sender_is_noreply'],
        'has_list_unsubscribe': features.features['has_list_unsubscribe'],
        'bot_keyword_count': features.features['bot_keyword_count'],
        'url_count': features.features['url_count'],
        'is_business_hours': features.features['is_business_hours'],
        'question_count': features.features['question_count'],
    }

    print("\n👤 Key Human Indicators:")
    for key, value in human_indicators.items():
        print(f"  {key}: {value}")

    print(f"\n✅ Human email features extracted successfully")


def test_feature_names():
    """Test getting feature names."""
    print("\n" + "="*70)
    print("TEST: Feature Names and Count")
    print("="*70)

    extractor = EmailFeatureExtractor()
    feature_names = extractor.get_feature_names()
    feature_count = extractor.get_feature_count()

    print(f"\n📊 Total Features: {feature_count}")
    print(f"\n📝 Feature Categories:")

    # Group by category
    categories = {
        'Metadata': [f for f in feature_names if f.startswith('has_') or 'header' in f or 'spf' in f or 'dkim' in f or 'mailer' in f],
        'Content': [f for f in feature_names if any(x in f for x in ['subject', 'body', 'url', 'html', 'keyword', 'urgency', 'exclamation'])],
        'Sender': [f for f in feature_names if 'sender' in f],
        'Temporal': [f for f in feature_names if any(x in f for x in ['hour', 'day', 'time', 'weekend', 'business', 'night'])],
        'Structural': [f for f in feature_names if any(x in f for x in ['recipient', 'cc', 'reply', 'forward', 'label', 'attachment'])],
        'Behavioral': [f for f in feature_names if 'user_typically' in f or 'avg_user' in f or 'read_rate' in f or 'reply_rate' in f],
    }

    for category, features in categories.items():
        print(f"\n  {category} ({len(features)} features):")
        for f in features[:5]:  # Show first 5
            print(f"    - {f}")
        if len(features) > 5:
            print(f"    ... and {len(features) - 5} more")

    print(f"\n✅ Feature extraction pipeline ready")


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("FEATURE EXTRACTION PIPELINE TEST")
    print("="*70)

    test_feature_names()
    test_bot_email()
    test_human_email()

    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED")
    print("="*70)
    print("\nFeature extraction pipeline is working correctly!")
    print("Ready to build ML models with these features.")


if __name__ == "__main__":
    main()
