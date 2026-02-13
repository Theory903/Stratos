"""ML application layer — use cases for model training, prediction, and detection."""

from __future__ import annotations

from typing import Any

import numpy as np

from stratos_ml.domain.entities import AnomalyResult, Prediction
from stratos_ml.domain.ports import AnomalyDetector, ModelStore, Predictor, RegimeClassifier


class PredictUseCase:
    """Run prediction using a named model."""

    def __init__(self, predictor: Predictor) -> None:
        self._predictor = predictor

    async def execute(self, features: np.ndarray) -> Prediction:
        values = self._predictor.predict(features)
        return Prediction(
            model_name=self._predictor.name(),
            value=float(values[0]),
            confidence=0.0,  # TODO: calibration
            horizon_days=1,
        )


class DetectRegimeUseCase:
    """Classify current market regime."""

    def __init__(self, classifier: RegimeClassifier) -> None:
        self._classifier = classifier

    async def execute(self, features: np.ndarray) -> str:
        return self._classifier.classify(features)


class DetectAnomalyUseCase:
    """Detect anomalies in financial data."""

    def __init__(self, detector: AnomalyDetector) -> None:
        self._detector = detector

    async def execute(self, data: np.ndarray) -> list[AnomalyResult]:
        scores = self._detector.detect(data)
        return [
            AnomalyResult(
                score=float(s),
                is_anomaly=float(s) > 0.5,
                description=f"Anomaly score: {s:.3f}",
            )
            for s in scores
        ]


class TrainModelUseCase:
    """Train a model and persist to model store."""

    def __init__(self, predictor: Predictor, store: ModelStore) -> None:
        self._predictor = predictor
        self._store = store

    async def execute(self, X: np.ndarray, y: np.ndarray, version: str) -> str:
        self._predictor.fit(X, y)
        artifact_uri = self._store.save(self._predictor, self._predictor.name(), version)
        return artifact_uri
