"""ML adapters — concrete model implementations and infrastructure."""

from stratos_ml.adapters.models.statistical import ARIMAPredictor, GARCHVolatilityModel, PCAFactorModel
from stratos_ml.adapters.models.classical import (
    HMMRegimeClassifier,
    IsolationForestDetector,
    RandomForestPredictor,
    XGBoostPredictor,
)
from stratos_ml.adapters.models.deep import AutoencoderDetector, LSTMPredictor
from stratos_ml.adapters.registry import FileModelStore
from stratos_ml.adapters.feature_store import FeatureEngineer

__all__ = [
    "ARIMAPredictor",
    "GARCHVolatilityModel",
    "PCAFactorModel",
    "XGBoostPredictor",
    "RandomForestPredictor",
    "IsolationForestDetector",
    "HMMRegimeClassifier",
    "LSTMPredictor",
    "AutoencoderDetector",
    "FileModelStore",
    "FeatureEngineer",
]
