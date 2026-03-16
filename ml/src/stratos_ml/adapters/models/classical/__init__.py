"""Classical ML model adapters — XGBoost, RandomForest, IsolationForest, HMM.

These implement Predictor, AnomalyDetector, and RegimeClassifier protocols.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestRegressor

from stratos_ml.domain.entities import MarketRegime


class XGBoostPredictor:
    """XGBoost gradient boosting regressor.

    Implements `Predictor` protocol.
    Wraps xgboost.XGBRegressor for financial time-series prediction.
    """

    def __init__(
        self,
        n_estimators: int = 200,
        max_depth: int = 6,
        learning_rate: float = 0.05,
        subsample: float = 0.8,
    ) -> None:
        self._model: Any = None
        self._params = {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "learning_rate": learning_rate,
            "subsample": subsample,
        }

    def name(self) -> str:
        return "XGBoost"

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train XGBoost on features and targets."""
        import xgboost as xgb
        self._model = xgb.XGBRegressor(
            **self._params,
            objective="reg:squarederror",
            random_state=42,
            verbosity=0,
        )
        self._model.fit(X, y)

    def predict(self, features: np.ndarray) -> np.ndarray:
        """Predict target values."""
        if self._model is None:
            return np.zeros(features.shape[0] if features.ndim > 1 else 1)
        if features.ndim == 1:
            features = features.reshape(1, -1)
        return self._model.predict(features)


class RandomForestPredictor:
    """Random Forest regressor.

    Implements `Predictor` protocol.
    """

    def __init__(self, n_estimators: int = 100, max_depth: int = 10) -> None:
        self._model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=42,
            n_jobs=-1,
        )

    def name(self) -> str:
        return "RandomForest"

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self._model.fit(X, y)

    def predict(self, features: np.ndarray) -> np.ndarray:
        if features.ndim == 1:
            features = features.reshape(1, -1)
        return self._model.predict(features)


class IsolationForestDetector:
    """Isolation Forest anomaly detector.

    Implements `AnomalyDetector` protocol.
    Particularly effective for detecting market anomalies, fraud,
    and unusual trading patterns.
    """

    def __init__(
        self,
        contamination: float = 0.05,
        n_estimators: int = 200,
        max_features: float = 0.8,
    ) -> None:
        self._model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            max_features=max_features,
            random_state=42,
            n_jobs=-1,
        )

    def name(self) -> str:
        return "IsolationForest"

    def fit(self, data: np.ndarray) -> None:
        """Fit on normal data to learn the decision boundary."""
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        self._model.fit(data)

    def detect(self, data: np.ndarray) -> np.ndarray:
        """Return anomaly scores in [0, 1]. Higher = more anomalous."""
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        # score_samples returns negative scores; more negative = more anomalous
        raw_scores = self._model.score_samples(data)
        # Normalize to [0, 1]: 0 = normal, 1 = highly anomalous
        min_s, max_s = raw_scores.min(), raw_scores.max()
        if max_s - min_s < 1e-10:
            return np.zeros(len(raw_scores))
        normalized = 1.0 - (raw_scores - min_s) / (max_s - min_s)
        return normalized


class HMMRegimeClassifier:
    """Hidden Markov Model for market regime classification.

    Implements `RegimeClassifier` protocol.
    Classifies market states into regimes (bull, bear, sideways, crisis, recovery).
    """

    def __init__(self, n_regimes: int = 4) -> None:
        self.n_regimes = n_regimes
        self._transition_matrix: np.ndarray | None = None
        self._emission_means: np.ndarray | None = None
        self._emission_stds: np.ndarray | None = None
        self._initial_probs: np.ndarray | None = None
        self._regime_labels = [r.value for r in MarketRegime][:n_regimes]

    def name(self) -> str:
        return f"HMM(k={self.n_regimes})"

    def fit(self, data: np.ndarray) -> None:
        """Fit HMM using simple K-means + transition estimation.

        Uses a simplified approach:
        1. K-means to identify regime clusters
        2. Estimate transition probabilities from cluster sequence
        3. Estimate emission parameters per cluster
        """
        from sklearn.cluster import KMeans

        if data.ndim == 1:
            data = data.reshape(-1, 1)

        # Cluster returns into regimes
        kmeans = KMeans(n_clusters=self.n_regimes, random_state=42, n_init=10)
        labels = kmeans.fit_predict(data)

        # Sort clusters by mean (bear=lowest, bull=highest)
        cluster_means = [data[labels == i].mean() for i in range(self.n_regimes)]
        sort_order = np.argsort(cluster_means)
        label_mapping = {old: new for new, old in enumerate(sort_order)}
        sorted_labels = np.array([label_mapping[l] for l in labels])

        # Emission parameters
        self._emission_means = np.array([
            data[sorted_labels == i].mean() for i in range(self.n_regimes)
        ])
        self._emission_stds = np.array([
            max(data[sorted_labels == i].std(), 1e-8) for i in range(self.n_regimes)
        ])

        # Transition matrix
        trans = np.zeros((self.n_regimes, self.n_regimes))
        for t in range(len(sorted_labels) - 1):
            trans[sorted_labels[t], sorted_labels[t + 1]] += 1

        # Normalize rows
        row_sums = trans.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1
        self._transition_matrix = trans / row_sums

        # Initial probabilities
        counts = np.bincount(sorted_labels, minlength=self.n_regimes)
        self._initial_probs = counts / counts.sum()

    def classify(self, features: np.ndarray) -> tuple[str, float]:
        """Classify current regime based on most recent observations."""
        if self._emission_means is None or self._emission_stds is None:
            return MarketRegime.SIDEWAYS.value, 0.0

        # Use last observation for classification
        obs = features[-1] if features.ndim == 1 else features[-1].mean()

        # Compute log-likelihood under each regime's emission
        log_probs = np.zeros(self.n_regimes)
        from scipy.stats import norm
        for i in range(self.n_regimes):
            log_probs[i] = norm.logpdf(obs, self._emission_means[i], self._emission_stds[i])

        # Add prior
        if self._initial_probs is not None:
            log_probs += np.log(self._initial_probs + 1e-10)

        # Softmax for stability (confidence)
        probs = np.exp(log_probs - np.max(log_probs))
        probs /= probs.sum()

        best_regime = int(np.argmax(probs))
        stability = float(probs[best_regime])

        if best_regime < len(self._regime_labels):
            return self._regime_labels[best_regime], stability
        return MarketRegime.SIDEWAYS.value, 0.0
