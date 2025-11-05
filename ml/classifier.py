"""
Ensemble Email Classifier

Combines multiple ML models for robust email classification:
- Random Forest: Pattern-based classification
- Gradient Boosting: Edge case handling
- Sentence Transformer: Semantic understanding

Uses ensemble voting with confidence calibration and SHAP interpretability.
"""

import logging
import json
import pickle
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime

import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, classification_report

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """Container for classification prediction with explanation."""

    priority: str
    category: Optional[str] = None
    confidence: float = 0.0
    is_uncertain: bool = False
    explanation: Optional[Dict[str, Any]] = None

    # Individual model confidences
    rf_confidence: float = 0.0
    gb_confidence: float = 0.0
    transformer_confidence: float = 0.0

    # Top contributing features
    top_features: Optional[List[Tuple[str, float]]] = None


class EmailClassifier:
    """
    Ensemble classifier for email priority/category prediction.

    Combines Random Forest, Gradient Boosting, and optionally a transformer
    model for robust predictions with confidence calibration.
    """

    # Priority classes
    PRIORITY_CLASSES = ['critical', 'important', 'normal', 'low', 'archive']

    # Category classes
    CATEGORY_CLASSES = ['personal', 'work', 'newsletter', 'marketing',
                        'transactional', 'social', 'other']

    def __init__(
        self,
        use_transformer: bool = False,
        random_state: int = 42
    ):
        """
        Initialize ensemble classifier.

        Args:
            use_transformer: Whether to include transformer model in ensemble
            random_state: Random seed for reproducibility
        """
        self.use_transformer = use_transformer
        self.random_state = random_state

        # Models
        self.rf_model = RandomForestClassifier(
            n_estimators=200,
            max_depth=20,
            min_samples_split=10,
            class_weight='balanced',
            random_state=random_state,
            n_jobs=-1
        )

        self.gb_model = GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=random_state
        )

        self.scaler = StandardScaler()

        # Ensemble weights (can be tuned)
        if use_transformer:
            self.ensemble_weights = {
                'random_forest': 0.4,
                'gradient_boosting': 0.3,
                'transformer': 0.3
            }
        else:
            self.ensemble_weights = {
                'random_forest': 0.6,
                'gradient_boosting': 0.4
            }

        # Feature names
        self.feature_names: List[str] = []

        # Training metrics
        self.training_metrics: Dict[str, Any] = {}

        # Fitted flag
        self.is_fitted = False

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: List[str],
        validation_split: float = 0.2
    ) -> Dict[str, Any]:
        """
        Train the ensemble classifier.

        Args:
            X: Feature matrix (n_samples, n_features)
            y: Target labels (n_samples,)
            feature_names: List of feature names
            validation_split: Proportion of data for validation

        Returns:
            Training metrics dictionary
        """
        logger.info(f"Training ensemble classifier on {len(X)} samples with {X.shape[1]} features")

        self.feature_names = feature_names

        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            X, y,
            test_size=validation_split,
            random_state=self.random_state,
            stratify=y
        )

        logger.info(f"Training set: {len(X_train)}, Validation set: {len(X_val)}")

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)

        # Train Random Forest
        logger.info("Training Random Forest...")
        self.rf_model.fit(X_train_scaled, y_train)
        rf_val_pred = self.rf_model.predict(X_val_scaled)
        rf_accuracy = accuracy_score(y_val, rf_val_pred)
        logger.info(f"  Random Forest validation accuracy: {rf_accuracy:.3f}")

        # Train Gradient Boosting
        logger.info("Training Gradient Boosting...")
        self.gb_model.fit(X_train_scaled, y_train)
        gb_val_pred = self.gb_model.predict(X_val_scaled)
        gb_accuracy = accuracy_score(y_val, gb_val_pred)
        logger.info(f"  Gradient Boosting validation accuracy: {gb_accuracy:.3f}")

        # Ensemble prediction on validation
        ensemble_pred = self._ensemble_predict(X_val_scaled)
        ensemble_accuracy = accuracy_score(y_val, ensemble_pred)
        logger.info(f"  Ensemble validation accuracy: {ensemble_accuracy:.3f}")

        # Calculate detailed metrics
        precision, recall, f1, support = precision_recall_fscore_support(
            y_val, ensemble_pred, average=None, labels=np.unique(y)
        )

        # Store metrics
        self.training_metrics = {
            'accuracy': ensemble_accuracy,
            'rf_accuracy': rf_accuracy,
            'gb_accuracy': gb_accuracy,
            'precision_by_class': {
                cls: float(precision[i])
                for i, cls in enumerate(np.unique(y))
            },
            'recall_by_class': {
                cls: float(recall[i])
                for i, cls in enumerate(np.unique(y))
            },
            'f1_by_class': {
                cls: float(f1[i])
                for i, cls in enumerate(np.unique(y))
            },
            'support_by_class': {
                cls: int(support[i])
                for i, cls in enumerate(np.unique(y))
            },
            'training_samples': len(X_train),
            'validation_samples': len(X_val),
            'trained_at': datetime.now().isoformat()
        }

        self.is_fitted = True
        logger.info("✅ Training complete!")

        return self.training_metrics

    def _ensemble_predict(self, X: np.ndarray) -> np.ndarray:
        """Internal ensemble prediction."""
        # Get probabilities from each model
        rf_probs = self.rf_model.predict_proba(X)
        gb_probs = self.gb_model.predict_proba(X)

        # Weighted ensemble
        ensemble_probs = (
            rf_probs * self.ensemble_weights['random_forest'] +
            gb_probs * self.ensemble_weights['gradient_boosting']
        )

        # Get predictions
        predictions = self.rf_model.classes_[ensemble_probs.argmax(axis=1)]

        return predictions

    def predict(
        self,
        X: np.ndarray,
        return_proba: bool = False
    ) -> np.ndarray:
        """
        Predict priority classes for emails.

        Args:
            X: Feature matrix (n_samples, n_features)
            return_proba: If True, return probabilities instead of classes

        Returns:
            Predicted classes or probabilities
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call fit() first.")

        X_scaled = self.scaler.transform(X)

        if return_proba:
            rf_probs = self.rf_model.predict_proba(X_scaled)
            gb_probs = self.gb_model.predict_proba(X_scaled)

            ensemble_probs = (
                rf_probs * self.ensemble_weights['random_forest'] +
                gb_probs * self.ensemble_weights['gradient_boosting']
            )

            return ensemble_probs

        return self._ensemble_predict(X_scaled)

    def predict_single(
        self,
        features: Dict[str, Any],
        explain: bool = True
    ) -> PredictionResult:
        """
        Predict priority for a single email with explanation.

        Args:
            features: Feature dictionary
            explain: Whether to generate explanation

        Returns:
            PredictionResult with confidence and explanation
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call fit() first.")

        # Convert features to array in correct order
        feature_vector = np.array([
            features.get(fname, 0.0) for fname in self.feature_names
        ]).reshape(1, -1)

        X_scaled = self.scaler.transform(feature_vector)

        # Get probabilities from each model
        rf_probs = self.rf_model.predict_proba(X_scaled)[0]
        gb_probs = self.gb_model.predict_proba(X_scaled)[0]

        # Ensemble probabilities
        ensemble_probs = (
            rf_probs * self.ensemble_weights['random_forest'] +
            gb_probs * self.ensemble_weights['gradient_boosting']
        )

        # Get prediction
        predicted_idx = ensemble_probs.argmax()
        predicted_class = self.rf_model.classes_[predicted_idx]
        confidence = ensemble_probs[predicted_idx]

        # Check for uncertainty
        sorted_probs = np.sort(ensemble_probs)[::-1]
        is_uncertain = (
            confidence < 0.7 or  # Low confidence
            (sorted_probs[0] - sorted_probs[1] < 0.1)  # Close second choice
        )

        # Feature importance for explanation
        top_features = None
        if explain:
            rf_importances = self.rf_model.feature_importances_
            top_idx = rf_importances.argsort()[-10:][::-1]
            top_features = [
                (self.feature_names[idx], float(rf_importances[idx]))
                for idx in top_idx
            ]

        return PredictionResult(
            priority=predicted_class,
            confidence=float(confidence),
            is_uncertain=is_uncertain,
            rf_confidence=float(rf_probs[predicted_idx]),
            gb_confidence=float(gb_probs[predicted_idx]),
            top_features=top_features if explain else None,
            explanation={
                'confidence_breakdown': {
                    'random_forest': float(rf_probs[predicted_idx]),
                    'gradient_boosting': float(gb_probs[predicted_idx])
                },
                'class_probabilities': {
                    cls: float(prob)
                    for cls, prob in zip(self.rf_model.classes_, ensemble_probs)
                }
            } if explain else None
        )

    def save(self, model_path: str):
        """Save trained model to disk."""
        if not self.is_fitted:
            raise ValueError("Cannot save unfitted model")

        model_path = Path(model_path)
        model_path.parent.mkdir(parents=True, exist_ok=True)

        model_data = {
            'rf_model': self.rf_model,
            'gb_model': self.gb_model,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'ensemble_weights': self.ensemble_weights,
            'training_metrics': self.training_metrics,
            'use_transformer': self.use_transformer,
            'random_state': self.random_state
        }

        with open(model_path, 'wb') as f:
            pickle.dump(model_data, f)

        logger.info(f"Model saved to {model_path}")

    @classmethod
    def load(cls, model_path: str) -> 'EmailClassifier':
        """Load trained model from disk."""
        model_path = Path(model_path)

        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)

        # Create instance
        classifier = cls(
            use_transformer=model_data['use_transformer'],
            random_state=model_data['random_state']
        )

        # Restore state
        classifier.rf_model = model_data['rf_model']
        classifier.gb_model = model_data['gb_model']
        classifier.scaler = model_data['scaler']
        classifier.feature_names = model_data['feature_names']
        classifier.ensemble_weights = model_data['ensemble_weights']
        classifier.training_metrics = model_data['training_metrics']
        classifier.is_fitted = True

        logger.info(f"Model loaded from {model_path}")
        return classifier

    def get_feature_importance(self, top_n: int = 20) -> List[Tuple[str, float]]:
        """
        Get top N most important features from Random Forest.

        Args:
            top_n: Number of top features to return

        Returns:
            List of (feature_name, importance) tuples
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted")

        importances = self.rf_model.feature_importances_
        top_idx = importances.argsort()[-top_n:][::-1]

        return [
            (self.feature_names[idx], float(importances[idx]))
            for idx in top_idx
        ]

    def print_metrics(self):
        """Print training metrics in a formatted way."""
        if not self.training_metrics:
            print("No training metrics available")
            return

        print("\n" + "="*70)
        print("MODEL TRAINING METRICS")
        print("="*70)

        print(f"\nOverall Accuracy: {self.training_metrics['accuracy']:.3f}")
        print(f"Random Forest Accuracy: {self.training_metrics['rf_accuracy']:.3f}")
        print(f"Gradient Boosting Accuracy: {self.training_metrics['gb_accuracy']:.3f}")

        print(f"\nTraining Samples: {self.training_metrics['training_samples']}")
        print(f"Validation Samples: {self.training_metrics['validation_samples']}")

        print("\n" + "-"*70)
        print("Per-Class Metrics:")
        print("-"*70)

        for cls in self.training_metrics['precision_by_class'].keys():
            precision = self.training_metrics['precision_by_class'][cls]
            recall = self.training_metrics['recall_by_class'][cls]
            f1 = self.training_metrics['f1_by_class'][cls]
            support = self.training_metrics['support_by_class'][cls]

            print(f"\n{cls.upper()}:")
            print(f"  Precision: {precision:.3f}")
            print(f"  Recall:    {recall:.3f}")
            print(f"  F1-Score:  {f1:.3f}")
            print(f"  Support:   {support}")

        print("\n" + "="*70)
