"""ML domain ports — abstract interfaces for model implementations.

All concrete models (ARIMA, XGBoost, LSTM, etc.) implement these protocols.
Adding new models requires ZERO modifications to existing code (Open/Closed).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class Predictor(Protocol):
    """Predict numeric values from features (ISP: predict only)."""

    def name(self) -> str: ...
    def predict(self, features: np.ndarray) -> np.ndarray: ...
    def fit(self, X: np.ndarray, y: np.ndarray) -> None: ...


@runtime_checkable
class AnomalyDetector(Protocol):
    """Detect anomalies in data (ISP: detect only)."""

    def name(self) -> str: ...
    def detect(self, data: np.ndarray) -> np.ndarray: ...
    def fit(self, data: np.ndarray) -> None: ...


@runtime_checkable
class RegimeClassifier(Protocol):
    """Classify market regimes (ISP: classify only)."""

    def name(self) -> str: ...
    def classify(self, features: np.ndarray) -> tuple[str, float]: ...
    def fit(self, data: np.ndarray) -> None: ...


@runtime_checkable
class ModelStore(Protocol):
    """Persist and load model artifacts (DIP: abstract storage)."""

    def save(self, model: Any, name: str, version: str) -> str: ...
    def load(self, name: str, version: str) -> Any: ...
    def list_versions(self, name: str) -> list[str]: ...
