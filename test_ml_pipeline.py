"""
End-to-End ML Pipeline Test

Demonstrates the complete ML workflow:
1. Generate synthetic email data
2. Extract features from emails
3. Train ensemble classifier
4. Make predictions
5. Evaluate performance
"""

import sys
import numpy as np
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from ml.synthetic_data import SyntheticEmailGenerator
from ml.features import EmailFeatureExtractor
from ml.classifier import EmailClassifier


def test_complete_pipeline():
    """Test the complete ML pipeline end-to-end."""

    print("\n" + "="*70)
    print("END-TO-END ML PIPELINE TEST")
    print("="*70)

    # Step 1: Generate synthetic data
    print("\n📧 STEP 1: Generating synthetic email data...")
    generator = SyntheticEmailGenerator(seed=42)
    emails, labels = generator.generate_dataset(
        num_emails=500,  # Use 500 for faster testing
        bot_ratio=0.7
    )
    print(f"✅ Generated {len(emails)} emails")
    print(f"   - Bot emails: {labels.count('bot')}")
    print(f"   - Human emails: {labels.count('human')}")

    # Step 2: Extract features
    print("\n🔍 STEP 2: Extracting features from emails...")
    extractor = EmailFeatureExtractor()

    X_list = []
    y_list = []

    for email, label in zip(emails, labels):
        features = extractor.extract_features(
            message_id=email['message_id'],
            sender=email['sender'],
            recipients=email['recipients'],
            subject=email['subject'],
            body_text=email['body_text'],
            body_html=email['body_html'],
            headers=email['headers'],
            date_received=email['date_received'],
            labels=email.get('labels'),
            thread_id=email.get('thread_id')
        )

        # Convert to numeric vector
        feature_vector = []
        for fname in extractor.get_feature_names():
            value = features.features.get(fname, 0)
            if isinstance(value, bool):
                feature_vector.append(1.0 if value else 0.0)
            elif isinstance(value, (int, float)):
                feature_vector.append(float(value))
            else:
                feature_vector.append(0.0)

        X_list.append(feature_vector)
        y_list.append(email['priority'])  # Use priority instead of bot/human

    X = np.array(X_list)
    y = np.array(y_list)

    print(f"✅ Extracted features from {len(X)} emails")
    print(f"   - Feature dimensions: {X.shape}")
    print(f"   - Priority distribution: {dict(zip(*np.unique(y, return_counts=True)))}")

    # Step 3: Train classifier
    print("\n🤖 STEP 3: Training ensemble classifier...")
    classifier = EmailClassifier(use_transformer=False, random_state=42)

    metrics = classifier.fit(
        X=X,
        y=y,
        feature_names=extractor.get_feature_names(),
        validation_split=0.2
    )

    print(f"✅ Training complete!")
    print(f"   - Ensemble accuracy: {metrics['accuracy']:.3f}")
    print(f"   - Random Forest accuracy: {metrics['rf_accuracy']:.3f}")
    print(f"   - Gradient Boosting accuracy: {metrics['gb_accuracy']:.3f}")

    # Step 4: Test predictions
    print("\n🎯 STEP 4: Testing predictions on new emails...")

    # Generate a few test emails
    test_generator = SyntheticEmailGenerator(seed=99)
    test_bot_email = test_generator.generate_bot_email()
    test_human_email = test_generator.generate_human_email()

    # Extract features and predict
    for test_email, email_type in [(test_bot_email, "BOT"), (test_human_email, "HUMAN")]:
        print(f"\n{'-'*70}")
        print(f"Test Email ({email_type}):")
        print(f"  From: {test_email['sender']}")
        print(f"  Subject: {test_email['subject'][:60]}...")

        # Extract features
        test_features = extractor.extract_features(
            message_id=test_email['message_id'],
            sender=test_email['sender'],
            recipients=test_email['recipients'],
            subject=test_email['subject'],
            body_text=test_email['body_text'],
            body_html=test_email['body_html'],
            headers=test_email['headers'],
            date_received=test_email['date_received']
        )

        # Predict
        prediction = classifier.predict_single(
            features=test_features.features,
            explain=True
        )

        print(f"\n  📊 ML Prediction:")
        print(f"    Priority: {prediction.priority}")
        print(f"    Confidence: {prediction.confidence:.2%}")
        print(f"    Uncertain: {'Yes' if prediction.is_uncertain else 'No'}")

        if prediction.top_features:
            print(f"\n  💡 Top Contributing Features:")
            for feat_name, importance in prediction.top_features[:5]:
                print(f"    - {feat_name}: {importance:.4f}")

    # Step 5: Show feature importance
    print("\n" + "="*70)
    print("📈 STEP 5: Feature Importance Analysis")
    print("="*70)

    top_features = classifier.get_feature_importance(top_n=15)
    print("\nTop 15 Most Important Features:")
    for i, (feat_name, importance) in enumerate(top_features, 1):
        bar = "█" * int(importance * 50)
        print(f"  {i:2d}. {feat_name:35s} {importance:.4f} {bar}")

    # Step 6: Model persistence
    print("\n" + "="*70)
    print("💾 STEP 6: Model Persistence")
    print("="*70)

    model_path = "test_model.pkl"
    classifier.save(model_path)
    print(f"✅ Model saved to {model_path}")

    # Load and verify
    loaded_classifier = EmailClassifier.load(model_path)
    print(f"✅ Model loaded successfully")

    # Verify loaded model works
    test_pred_original = classifier.predict_single(test_features.features, explain=False)
    test_pred_loaded = loaded_classifier.predict_single(test_features.features, explain=False)

    if test_pred_original.priority == test_pred_loaded.priority:
        print(f"✅ Loaded model predictions match original")
    else:
        print(f"⚠️  Warning: Loaded model predictions differ")

    # Step 7: Print detailed metrics
    print("\n" + "="*70)
    print("📊 STEP 7: Detailed Model Metrics")
    print("="*70)
    classifier.print_metrics()

    # Summary
    print("\n" + "="*70)
    print("✅ END-TO-END PIPELINE TEST COMPLETE")
    print("="*70)

    print("\n🎉 Summary:")
    print(f"  ✅ Data generation: {len(emails)} synthetic emails")
    print(f"  ✅ Feature extraction: {X.shape[1]} features per email")
    print(f"  ✅ Model training: {metrics['accuracy']:.1%} accuracy")
    print(f"  ✅ Predictions: Working with confidence scores")
    print(f"  ✅ Model persistence: Save/load functional")

    print("\n📋 Next Steps:")
    print("  1. Run analyze_mailbox.py on your real Gmail")
    print("  2. Train on your actual email patterns")
    print("  3. Integrate with database for persistence")
    print("  4. Build interactive feedback CLI")
    print("  5. Add calendar integration for deadlines")

    # Cleanup
    Path(model_path).unlink()
    print(f"\n🧹 Cleaned up test model file")


if __name__ == "__main__":
    test_complete_pipeline()
