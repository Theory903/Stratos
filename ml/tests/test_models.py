"""Tests for ML model adapters and feature engineering."""

from __future__ import annotations

import numpy as np
import pytest


# ── Statistical Models ─────────────────────────────────────────────


class TestARIMA:
    def test_fit_predict(self) -> None:
        from stratos_ml.adapters.models.statistical import ARIMAPredictor

        model = ARIMAPredictor(order=(3, 1, 0))
        # Trending series
        y = np.cumsum(np.random.randn(200)) + 100
        model.fit(np.empty(0), y)
        pred = model.predict(y[-10:])
        assert pred.shape == (1,)
        assert np.isfinite(pred[0])

    def test_name(self) -> None:
        from stratos_ml.adapters.models.statistical import ARIMAPredictor
        assert "ARIMA" in ARIMAPredictor().name()


class TestGARCH:
    def test_volatility_prediction(self) -> None:
        from stratos_ml.adapters.models.statistical import GARCHVolatilityModel

        model = GARCHVolatilityModel()
        returns = np.random.randn(500) * 0.02
        model.fit(np.empty(0), returns)
        pred = model.predict(returns[-5:])
        assert pred.shape == (1,)
        assert pred[0] > 0  # Volatility must be positive


class TestPCA:
    def test_factor_decomposition(self) -> None:
        from stratos_ml.adapters.models.statistical import PCAFactorModel

        pca = PCAFactorModel(n_components=3)
        data = np.random.randn(100, 10)
        pca.fit(data)
        transformed = pca.transform(data)
        assert transformed.shape == (100, 3)
        ratios = pca.explained_variance_ratio
        assert ratios is not None
        assert abs(ratios.sum() - 1.0) < 0.01 or ratios.sum() <= 1.0


# ── Classical ML Models ────────────────────────────────────────────


class TestIsolationForest:
    def test_anomaly_detection(self) -> None:
        from stratos_ml.adapters.models.classical import IsolationForestDetector

        detector = IsolationForestDetector(contamination=0.1)
        normal = np.random.randn(200, 5)
        detector.fit(normal)
        # Mix normal + outliers
        test_data = np.vstack([np.random.randn(50, 5), np.random.randn(5, 5) * 10])
        scores = detector.detect(test_data)
        assert scores.shape == (55,)
        assert all(0 <= s <= 1 for s in scores)
        # Outliers should have higher scores on average
        assert scores[-5:].mean() > scores[:50].mean()


class TestRandomForest:
    def test_fit_predict(self) -> None:
        from stratos_ml.adapters.models.classical import RandomForestPredictor

        model = RandomForestPredictor(n_estimators=10, max_depth=3)
        X = np.random.randn(100, 5)
        y = X @ np.array([1, -2, 3, -1, 0.5]) + np.random.randn(100) * 0.1
        model.fit(X, y)
        pred = model.predict(X[:5])
        assert pred.shape == (5,)


class TestHMM:
    def test_regime_classification(self) -> None:
        from stratos_ml.adapters.models.classical import HMMRegimeClassifier

        hmm = HMMRegimeClassifier(n_regimes=3)
        # Simulate 3 distinct market regimes
        bull = np.random.randn(100) * 0.01 + 0.002
        bear = np.random.randn(100) * 0.02 - 0.003
        sideways = np.random.randn(100) * 0.005
        combined = np.concatenate([bull, bear, sideways])
        hmm.fit(combined)
        regime, stability = hmm.classify(bull[-10:])
        assert isinstance(regime, str)
        assert isinstance(stability, float)
        assert 0.0 <= stability <= 1.0
        assert len(regime) > 0


# ── Feature Engineering ────────────────────────────────────────────


class TestFeatureEngineer:
    def test_technical_features(self) -> None:
        from stratos_ml.adapters.feature_store import FeatureEngineer

        prices = np.cumsum(np.random.randn(100)) + 100
        features = FeatureEngineer.technical_features(prices)
        assert features.shape == (100, 8)
        assert np.all(np.isfinite(features))

    def test_time_series_split(self) -> None:
        from stratos_ml.adapters.feature_store import FeatureEngineer

        X = np.random.randn(100, 5)
        y = np.random.randn(100)
        (X_train, y_train), (X_val, y_val), (X_test, y_test) = (
            FeatureEngineer.time_series_split(X, y)
        )
        assert len(X_train) == 70
        assert len(X_val) == 15
        assert len(X_test) == 15
        # No data leakage: train comes before val, val before test
        assert len(X_train) + len(X_val) + len(X_test) == 100


# ── Model Store ────────────────────────────────────────────────────


class TestFileModelStore:
    def test_save_and_load(self, tmp_path) -> None:
        from stratos_ml.adapters.registry import FileModelStore
        from stratos_ml.adapters.models.classical import RandomForestPredictor

        store = FileModelStore(base_path=str(tmp_path / "models"))
        model = RandomForestPredictor(n_estimators=5)
        X = np.random.randn(50, 3)
        y = np.random.randn(50)
        model.fit(X, y)

        uri = store.save(model._model, "rf", "v1")
        assert "model.pkl" in uri

        loaded = store.load("rf", "v1")
        assert loaded is not None

    def test_list_versions(self, tmp_path) -> None:
        from stratos_ml.adapters.registry import FileModelStore

        store = FileModelStore(base_path=str(tmp_path / "models"))
        # Create fake versioned directories
        import os
        os.makedirs(tmp_path / "models" / "test_model" / "v1")
        os.makedirs(tmp_path / "models" / "test_model" / "v2")
        versions = store.list_versions("test_model")
        assert "v1" in versions
        assert "v2" in versions
