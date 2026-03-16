"""ML service dependency injection."""

from __future__ import annotations

from stratos_ml.adapters.models.classical import (
    HMMRegimeClassifier,
    IsolationForestDetector,
    XGBoostPredictor,
)
from stratos_ml.adapters.registry import FileModelStore
from stratos_ml.application import (
    DetectAnomalyUseCase,
    DetectRegimeUseCase,
    PredictUseCase,
    TrainModelUseCase,
)

# ── Singleton instances (created once per process) ─────────────────

_xgboost = XGBoostPredictor()
_hmm = HMMRegimeClassifier()
_isolationforest = IsolationForestDetector()
_model_store = FileModelStore()


# ── FastAPI Depends factories ──────────────────────────────────────

def get_predictor() -> PredictUseCase:
    return PredictUseCase(predictor=_xgboost)


def get_regime_classifier() -> DetectRegimeUseCase:
    return DetectRegimeUseCase(classifier=_hmm)


def get_anomaly_detector() -> DetectAnomalyUseCase:
    return DetectAnomalyUseCase(detector=_isolationforest)


def get_train_use_case() -> TrainModelUseCase:
    return TrainModelUseCase(predictor=_xgboost, store=_model_store)
