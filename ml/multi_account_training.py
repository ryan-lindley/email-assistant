"""
Multi-Account ML Training Pipeline

Trains a unified email classifier across multiple Gmail accounts.

Features:
- Unified feature extraction across all accounts
- Cross-account training data preparation
- Account-specific pattern learning
- Ensemble model training (Random Forest + Gradient Boosting)
- Model versioning and tracking
- Incremental learning support

Usage:
    from ml.multi_account_training import MultiAccountTrainer

    trainer = MultiAccountTrainer(config_path='accounts.json')

    # Train from all accounts
    model, metrics = trainer.train_unified_model(max_per_account=1000)

    # Save model
    trainer.save_model('models/unified_classifier.pkl')

    # Train incrementally when new account added
    trainer.train_incremental(new_account_emails)
"""

import json
import logging
import pickle
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from collections import Counter

import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix

from core.gmail.multi_account import MultiAccountManager
from ml.features import EmailFeatureExtractor
from ml.classifier import EmailClassifier

logger = logging.getLogger(__name__)


class MultiAccountTrainer:
    """Train unified ML model across multiple Gmail accounts."""

    def __init__(self, config_path: str = 'accounts.json', use_transformer: bool = False):
        """
        Initialize multi-account trainer.

        Args:
            config_path: Path to accounts configuration
            use_transformer: Whether to use transformer embeddings
        """
        self.config_path = config_path
        self.manager = MultiAccountManager(config_path)
        self.feature_extractor = EmailFeatureExtractor()
        self.classifier = EmailClassifier(use_transformer=use_transformer)

        self.training_metadata: Dict[str, Any] = {
            'accounts_trained': [],
            'training_date': None,
            'total_samples': 0,
            'samples_per_account': {},
            'class_distribution': {},
            'feature_count': 67
        }

    def fetch_training_data(
        self,
        max_per_account: Optional[int] = 1000,
        include_labels: bool = True
    ) -> Tuple[List[Dict], List[str]]:
        """
        Fetch emails from all accounts for training.

        Args:
            max_per_account: Maximum emails per account
            include_labels: Whether to include Gmail labels in features

        Returns:
            Tuple of (email_list, labels_list)
        """
        logger.info("=" * 70)
        logger.info("FETCHING TRAINING DATA FROM ALL ACCOUNTS")
        logger.info("=" * 70)

        # Authenticate and fetch
        success, failed = self.manager.authenticate_all()

        if success == 0:
            raise RuntimeError("No accounts authenticated successfully")

        logger.info(f"✅ {success} account(s) authenticated")

        # Fetch emails
        results = self.manager.fetch_all_emails(max_per_account=max_per_account)

        # Combine and deduplicate
        all_emails = []
        for account_name, emails in results.items():
            self.training_metadata['samples_per_account'][account_name] = len(emails)
            self.training_metadata['accounts_trained'].append(account_name)
            all_emails.extend(emails)

        unique_emails = self.manager.deduplicate_emails(all_emails)

        logger.info(f"\n📊 Training data summary:")
        logger.info(f"  • Total emails (before dedup): {len(all_emails)}")
        logger.info(f"  • Unique emails (after dedup): {len(unique_emails)}")

        # For initial training, we'll use heuristic labels
        # In production, these would come from user feedback
        labels = self._generate_heuristic_labels(unique_emails)

        self.training_metadata['total_samples'] = len(unique_emails)
        self.training_metadata['class_distribution'] = dict(Counter(labels))

        return unique_emails, labels

    def _generate_heuristic_labels(self, emails: List[Dict]) -> List[str]:
        """
        Generate initial labels using heuristics.

        In production, these would be replaced by user feedback.

        Args:
            emails: List of email dictionaries

        Returns:
            List of labels ('bot' or 'human')
        """
        labels = []

        for msg in emails:
            headers = {h['name'].lower(): h['value']
                      for h in msg.get('payload', {}).get('headers', [])}

            # Bot indicators (same as analyzer)
            bot_score = 0

            # List-Unsubscribe (strong indicator)
            if any(h['name'].lower() == 'list-unsubscribe' for h in msg.get('payload', {}).get('headers', [])):
                bot_score += 2

            # Auto-submitted
            if any(h['name'].lower() == 'auto-submitted' for h in msg.get('payload', {}).get('headers', [])):
                bot_score += 2

            # No-reply sender
            sender = headers.get('from', '').lower()
            if 'no-reply' in sender or 'noreply' in sender:
                bot_score += 1

            # Marketing keywords
            subject = headers.get('subject', '').lower()
            marketing_words = ['unsubscribe', 'newsletter', 'offer', 'deal', 'discount']
            if any(word in subject for word in marketing_words):
                bot_score += 1

            # Label as bot if score >= 2
            labels.append('bot' if bot_score >= 2 else 'human')

        return labels

    def extract_features_batch(self, emails: List[Dict]) -> np.ndarray:
        """
        Extract features from batch of emails.

        Args:
            emails: List of email dictionaries

        Returns:
            Feature matrix (n_samples, n_features)
        """
        logger.info("🔧 Extracting features from all emails...")

        features_list = []

        for i, msg in enumerate(emails):
            if i % 100 == 0 and i > 0:
                logger.info(f"  Progress: {i}/{len(emails)} ({i*100//len(emails)}%)")

            try:
                # Extract headers
                headers = {h['name'].lower(): h['value']
                          for h in msg.get('payload', {}).get('headers', [])}

                message_id = msg.get('id', f'msg_{i}')
                sender = headers.get('from', '')
                recipients = headers.get('to', '')
                subject = headers.get('subject', '')
                date_received = headers.get('date', '')

                # Get body (simplified extraction)
                body_text = self._extract_body_text(msg)
                body_html = self._extract_body_html(msg)

                # Get labels
                label_names = [label['name'] for label in msg.get('labelIds', [])] if 'labelIds' in msg else []

                # Extract features
                email_features = self.feature_extractor.extract_features(
                    message_id=message_id,
                    sender=sender,
                    recipients=recipients,
                    subject=subject,
                    body_text=body_text,
                    body_html=body_html,
                    headers=headers,
                    date_received=date_received,
                    labels=label_names,
                    thread_id=msg.get('threadId')
                )

                features_list.append(email_features.to_array())

            except Exception as e:
                logger.warning(f"Failed to extract features for email {i}: {e}")
                # Add zero features as fallback
                features_list.append(np.zeros(67))

        logger.info(f"✅ Extracted features for {len(features_list)} emails")

        return np.array(features_list)

    def _extract_body_text(self, msg: Dict) -> str:
        """Extract plain text body from message."""
        payload = msg.get('payload', {})

        # Try parts first
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':
                    data = part.get('body', {}).get('data', '')
                    if data:
                        import base64
                        return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

        # Try direct body
        if 'body' in payload and 'data' in payload['body']:
            import base64
            data = payload['body']['data']
            return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

        return ''

    def _extract_body_html(self, msg: Dict) -> str:
        """Extract HTML body from message."""
        payload = msg.get('payload', {})

        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/html':
                    data = part.get('body', {}).get('data', '')
                    if data:
                        import base64
                        return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

        return ''

    def train_unified_model(
        self,
        max_per_account: Optional[int] = 1000,
        test_size: float = 0.2,
        random_state: int = 42
    ) -> Tuple[EmailClassifier, Dict[str, Any]]:
        """
        Train unified model across all accounts.

        Args:
            max_per_account: Max emails per account
            test_size: Test set proportion
            random_state: Random seed

        Returns:
            Tuple of (trained_classifier, metrics_dict)
        """
        logger.info("\n" + "=" * 70)
        logger.info("TRAINING UNIFIED MULTI-ACCOUNT MODEL")
        logger.info("=" * 70)

        # Fetch training data
        emails, labels = self.fetch_training_data(max_per_account=max_per_account)

        # Extract features
        X = self.extract_features_batch(emails)
        y = np.array(labels)

        # Split train/test
        logger.info(f"\n📊 Splitting data: {int((1-test_size)*100)}% train, {int(test_size*100)}% test")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )

        logger.info(f"  • Training samples: {len(X_train)}")
        logger.info(f"  • Test samples: {len(X_test)}")
        logger.info(f"  • Class distribution: {dict(Counter(y))}")

        # Train model
        logger.info("\n🤖 Training ensemble classifier...")
        self.classifier.train(X_train, y_train)

        # Evaluate
        logger.info("\n📈 Evaluating model performance...")
        y_pred = self.classifier.predict(X_test)

        # Calculate metrics
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, average='weighted', zero_division=0),
            'recall': recall_score(y_test, y_pred, average='weighted', zero_division=0),
            'f1_score': f1_score(y_test, y_pred, average='weighted', zero_division=0),
            'train_samples': len(X_train),
            'test_samples': len(X_test),
            'class_distribution': dict(Counter(y))
        }

        # Print results
        logger.info("\n" + "=" * 70)
        logger.info("MODEL PERFORMANCE")
        logger.info("=" * 70)
        logger.info(f"Accuracy:  {metrics['accuracy']:.3f}")
        logger.info(f"Precision: {metrics['precision']:.3f}")
        logger.info(f"Recall:    {metrics['recall']:.3f}")
        logger.info(f"F1 Score:  {metrics['f1_score']:.3f}")
        logger.info("\nClassification Report:")
        print(classification_report(y_test, y_pred))

        # Update metadata
        self.training_metadata['training_date'] = datetime.now().isoformat()
        self.training_metadata['metrics'] = metrics

        return self.classifier, metrics

    def save_model(self, model_path: str = 'models/unified_classifier.pkl'):
        """
        Save trained model with metadata.

        Args:
            model_path: Path to save model
        """
        model_path = Path(model_path)
        model_path.parent.mkdir(parents=True, exist_ok=True)

        # Save model
        with open(model_path, 'wb') as f:
            pickle.dump(self.classifier, f)

        # Save metadata
        metadata_path = model_path.with_suffix('.json')
        with open(metadata_path, 'w') as f:
            json.dump(self.training_metadata, f, indent=2)

        logger.info(f"\n💾 Model saved to: {model_path}")
        logger.info(f"📝 Metadata saved to: {metadata_path}")

    def load_model(self, model_path: str = 'models/unified_classifier.pkl'):
        """
        Load trained model with metadata.

        Args:
            model_path: Path to load model from
        """
        model_path = Path(model_path)

        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        # Load model
        with open(model_path, 'rb') as f:
            self.classifier = pickle.load(f)

        # Load metadata
        metadata_path = model_path.with_suffix('.json')
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                self.training_metadata = json.load(f)

        logger.info(f"✅ Model loaded from: {model_path}")
        logger.info(f"📊 Trained on {self.training_metadata.get('total_samples', 0)} samples")
        logger.info(f"📅 Training date: {self.training_metadata.get('training_date', 'unknown')}")

    def train_incremental(
        self,
        new_emails: List[Dict],
        new_labels: List[str]
    ) -> Dict[str, Any]:
        """
        Train incrementally on new account data.

        Note: Currently retrains entire model. For true incremental
        learning, would need online learning algorithms.

        Args:
            new_emails: New email samples
            new_labels: Labels for new samples

        Returns:
            Updated metrics
        """
        logger.info(f"🔄 Incremental training with {len(new_emails)} new samples...")

        # Extract features from new emails
        X_new = self.extract_features_batch(new_emails)
        y_new = np.array(new_labels)

        # For now, would need to retrain entire model
        # True incremental learning would use SGD-based models
        logger.warning("⚠️  Incremental learning not yet implemented")
        logger.warning("    Currently requires full retraining")

        return {}


def main():
    """Example usage."""
    import argparse

    parser = argparse.ArgumentParser(description='Train unified multi-account classifier')
    parser.add_argument('--config', default='accounts.json', help='Accounts config path')
    parser.add_argument('--max-per-account', type=int, default=1000, help='Max emails per account')
    parser.add_argument('--output', default='models/unified_classifier.pkl', help='Output model path')
    parser.add_argument('--test-size', type=float, default=0.2, help='Test set proportion')

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    try:
        # Initialize trainer
        trainer = MultiAccountTrainer(config_path=args.config)

        # Train model
        classifier, metrics = trainer.train_unified_model(
            max_per_account=args.max_per_account,
            test_size=args.test_size
        )

        # Save model
        trainer.save_model(args.output)

        logger.info("\n✅ Training complete!")
        logger.info(f"📊 Final accuracy: {metrics['accuracy']:.3f}")

    except Exception as e:
        logger.error(f"❌ Training failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
