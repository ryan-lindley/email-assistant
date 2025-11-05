"""
Synthetic Email Data Generator

Generates realistic synthetic email data for ML model training and testing.
Creates both bot/marketing emails and human/personal emails with realistic patterns.
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import logging

from .features import EmailFeatureExtractor

logger = logging.getLogger(__name__)


class SyntheticEmailGenerator:
    """Generate synthetic email data for ML training."""

    # Bot/Marketing templates
    BOT_SENDERS = [
        "noreply@marketing.com",
        "notifications@newsletter.io",
        "deals@promotional-mail.net",
        "auto@system-alerts.com",
        "campaigns@email-service.com",
        "no-reply@shopping-site.com",
        "updates@social-network.com",
        "alerts@bank-system.com",
    ]

    BOT_SUBJECTS = [
        "🎉 {percent}% OFF - {urgency}!",
        "Your {item} is waiting - {urgency}",
        "EXCLUSIVE: Special offer just for you",
        "Don't miss out on this amazing deal",
        "[Newsletter] Weekly digest - {topic}",
        "You have {num} new notifications",
        "Your subscription will expire soon",
        "Update your account information",
    ]

    BOT_BODIES = [
        """
        Hi there!

        Don't miss our biggest sale of the year! Click here to shop now: {url}

        Special offer: {percent}% off everything
        Limited time only - expires {urgency_time}!

        Shop now: {url}

        Unsubscribe | View in browser
        """,
        """
        Hello,

        We noticed you haven't completed your purchase. Your items are still in your cart!

        Complete your order now: {url}

        This offer expires in {hours} hours.

        {multiple_urls}

        Unsubscribe from these emails
        """,
        """
        Newsletter: {topic}

        Here's what's new this week:
        - Article 1: {topic_detail}
        - Article 2: {topic_detail}
        - Article 3: {topic_detail}

        Read more: {url}

        You're receiving this because you subscribed to our newsletter.
        Unsubscribe anytime.
        """
    ]

    # Human/Personal templates
    HUMAN_SENDERS = [
        "john.smith@company.com",
        "sarah.johnson@workplace.org",
        "mike.brown@business.net",
        "emily.davis@enterprise.com",
        "alex.wilson@firm.com",
        "jessica.moore@corp.com",
        "david.taylor@organization.org",
        "amanda.anderson@group.com",
    ]

    HUMAN_SUBJECTS = [
        "Re: {topic} - follow up",
        "Quick question about {topic}",
        "Meeting next {day}?",
        "Fwd: {topic} - your input needed",
        "{topic} discussion",
        "Thanks for {action}",
        "Update on {topic}",
        "Can we schedule a call?",
    ]

    HUMAN_BODIES = [
        """
        Hi,

        Thanks for your email. I've reviewed the {topic} and have a few questions.

        Can we schedule a quick call to discuss? I'm free {time_suggestion}.

        Best regards,
        {name}
        """,
        """
        Hey,

        Just wanted to follow up on our conversation about {topic}.

        Did you get a chance to look at the documents I sent? Let me know if you need anything else.

        Thanks!
        {name}
        """,
        """
        Hi there,

        Quick question: {question}

        Also, are you available for a meeting {day}? We should discuss {topic}.

        Let me know what works for you.

        {name}
        """
    ]

    TOPICS = [
        "project update", "budget review", "client meeting", "proposal",
        "deadline", "collaboration", "feedback", "schedule",
        "presentation", "report", "analysis", "strategy"
    ]

    NAMES = ["John", "Sarah", "Mike", "Emily", "Alex", "Jessica", "David", "Amanda"]

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize generator.

        Args:
            seed: Random seed for reproducibility
        """
        if seed is not None:
            random.seed(seed)

    def generate_bot_email(self) -> Dict:
        """Generate a synthetic bot/marketing email."""
        sender = random.choice(self.BOT_SENDERS)
        subject_template = random.choice(self.BOT_SUBJECTS)
        body_template = random.choice(self.BOT_BODIES)

        # Fill in template variables
        subject = subject_template.format(
            percent=random.choice([10, 20, 30, 40, 50, 60, 70]),
            urgency=random.choice(["LIMITED TIME", "ACT NOW", "ENDING SOON", "TODAY ONLY"]),
            item=random.choice(["order", "cart", "wishlist", "items"]),
            topic=random.choice(["Tech News", "Fashion Updates", "Travel Deals", "Food Recipes"]),
            num=random.randint(1, 99)
        )

        body = body_template.format(
            url="https://bit.ly/sale" + str(random.randint(1000, 9999)),
            percent=random.choice([20, 30, 40, 50]),
            urgency_time=random.choice(["tonight", "tomorrow", "this weekend"]),
            hours=random.choice([12, 24, 48]),
            multiple_urls="\n".join([
                f"Product {i}: https://shop.example.com/product{i}"
                for i in range(3)
            ]),
            topic=random.choice(self.TOPICS),
            topic_detail=random.choice(self.TOPICS)
        )

        # Bot-like headers
        headers = {
            'from': sender,
            'subject': subject,
            'list-unsubscribe': f'<mailto:unsub@{sender.split("@")[1]}>',
            'precedence': 'bulk' if random.random() > 0.3 else 'normal',
            'x-mailer': random.choice(['MailChimp', 'SendGrid', 'Constant Contact', 'Campaign Monitor']),
        }

        if random.random() > 0.5:
            headers['x-campaign-id'] = str(random.randint(10000, 99999))
            headers['x-marketing-type'] = random.choice(['promotional', 'newsletter', 'transactional'])

        # Random time (often outside business hours for bots)
        if random.random() > 0.4:
            hour = random.choice([0, 1, 2, 3, 4, 5, 20, 21, 22, 23])  # Night/evening
        else:
            hour = random.randint(6, 19)

        date_received = datetime.now() - timedelta(
            days=random.randint(0, 365),
            hours=hour,
            minutes=random.randint(0, 59)
        )

        return {
            'message_id': f'bot_{random.randint(100000, 999999)}',
            'sender': sender,
            'recipients': ['user@example.com'],
            'subject': subject,
            'body_text': body,
            'body_html': f'<html><body><table>{body}</table></body></html>',
            'headers': headers,
            'date_received': date_received,
            'labels': ['INBOX'],
            'thread_id': None,
            'true_label': 'bot',  # Ground truth
            'priority': random.choice(['low', 'archive'])
        }

    def generate_human_email(self) -> Dict:
        """Generate a synthetic human/personal email."""
        sender = random.choice(self.HUMAN_SENDERS)
        subject_template = random.choice(self.HUMAN_SUBJECTS)
        body_template = random.choice(self.HUMAN_BODIES)

        # Fill in template variables
        topic = random.choice(self.TOPICS)
        subject = subject_template.format(
            topic=topic,
            day=random.choice(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]),
            action=random.choice(["the update", "your help", "the meeting", "the info"])
        )

        name = random.choice(self.NAMES)
        body = body_template.format(
            topic=topic,
            time_suggestion=random.choice([
                "tomorrow afternoon",
                "next Tuesday",
                "after 2pm",
                "Wednesday morning"
            ]),
            name=name,
            question=random.choice([
                "Do you have the latest numbers?",
                "When can we schedule this?",
                "Did you receive my last email?",
                "What's the status on this?"
            ]),
            day=random.choice(["next week", "this Friday", "tomorrow"])
        )

        # Human-like headers
        headers = {
            'from': sender,
            'subject': subject,
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        # Sometimes it's a reply
        if random.random() > 0.5:
            headers['in-reply-to'] = f'<msg_{random.randint(1000, 9999)}@example.com>'
            headers['references'] = headers['in-reply-to']

        # Business hours for humans
        hour = random.randint(9, 17)
        weekday = random.randint(0, 4)  # Monday-Friday

        date_received = datetime.now() - timedelta(
            days=random.randint(0, 90),
            hours=hour - datetime.now().hour,
            minutes=random.randint(0, 59)
        )
        # Adjust to weekday
        while date_received.weekday() > 4:
            date_received -= timedelta(days=1)

        return {
            'message_id': f'human_{random.randint(100000, 999999)}',
            'sender': sender,
            'recipients': ['user@example.com'],
            'subject': subject,
            'body_text': body,
            'body_html': None,
            'headers': headers,
            'date_received': date_received,
            'labels': ['INBOX', 'IMPORTANT'] if random.random() > 0.7 else ['INBOX'],
            'thread_id': f'thread_{random.randint(1000, 9999)}',
            'true_label': 'human',  # Ground truth
            'priority': random.choice(['critical', 'important', 'normal'])
        }

    def generate_dataset(
        self,
        num_emails: int = 1000,
        bot_ratio: float = 0.7
    ) -> Tuple[List[Dict], List[str]]:
        """
        Generate a synthetic email dataset.

        Args:
            num_emails: Total number of emails to generate
            bot_ratio: Proportion of bot emails (0.0 to 1.0)

        Returns:
            Tuple of (emails list, labels list)
        """
        num_bots = int(num_emails * bot_ratio)
        num_humans = num_emails - num_bots

        logger.info(f"Generating {num_emails} synthetic emails ({num_bots} bots, {num_humans} humans)")

        emails = []
        labels = []

        # Generate bot emails
        for _ in range(num_bots):
            email = self.generate_bot_email()
            emails.append(email)
            labels.append('bot')

        # Generate human emails
        for _ in range(num_humans):
            email = self.generate_human_email()
            emails.append(email)
            labels.append('human')

        # Shuffle
        combined = list(zip(emails, labels))
        random.shuffle(combined)
        emails, labels = zip(*combined)

        return list(emails), list(labels)

    def generate_priority_dataset(
        self,
        num_emails: int = 1000
    ) -> Tuple[List[Dict], List[str]]:
        """
        Generate dataset with priority labels instead of bot/human.

        Returns:
            Tuple of (emails list, priority labels list)
        """
        emails, binary_labels = self.generate_dataset(num_emails)

        priority_labels = []
        for email in emails:
            priority_labels.append(email['priority'])

        return emails, priority_labels


# Convenience function
def generate_synthetic_training_data(
    num_samples: int = 1000,
    bot_ratio: float = 0.7,
    seed: Optional[int] = 42
) -> Tuple[List[Dict], List[str]]:
    """
    Generate synthetic email data for training.

    Args:
        num_samples: Number of emails to generate
        bot_ratio: Proportion of bot emails
        seed: Random seed for reproducibility

    Returns:
        Tuple of (emails, labels)
    """
    generator = SyntheticEmailGenerator(seed=seed)
    return generator.generate_dataset(num_samples, bot_ratio)


if __name__ == "__main__":
    # Demo
    print("Generating synthetic email data...")

    generator = SyntheticEmailGenerator(seed=42)

    print("\n" + "="*70)
    print("BOT EMAIL EXAMPLE")
    print("="*70)
    bot_email = generator.generate_bot_email()
    print(f"From: {bot_email['sender']}")
    print(f"Subject: {bot_email['subject']}")
    print(f"Body:\n{bot_email['body_text'][:200]}...")

    print("\n" + "="*70)
    print("HUMAN EMAIL EXAMPLE")
    print("="*70)
    human_email = generator.generate_human_email()
    print(f"From: {human_email['sender']}")
    print(f"Subject: {human_email['subject']}")
    print(f"Body:\n{human_email['body_text'][:200]}...")

    print("\n" + "="*70)
    print("GENERATING DATASET")
    print("="*70)
    emails, labels = generator.generate_dataset(num_emails=100, bot_ratio=0.7)
    print(f"Generated {len(emails)} emails")
    print(f"Bot emails: {labels.count('bot')}")
    print(f"Human emails: {labels.count('human')}")
    print("\n✅ Synthetic data generation working!")
