"""ML service API routes — prediction, regime, anomaly, and training endpoints."""

from __future__ import annotations

from typing import Annotated

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from stratos_ml.api.deps import (
    get_anomaly_detector,
    get_predictor,
    get_regime_classifier,
    get_train_use_case,
)
from stratos_ml.application import (
    DetectAnomalyUseCase,
    DetectRegimeUseCase,
    PredictUseCase,
    TrainModelUseCase,
)

router = APIRouter(prefix="/ml", tags=["ML"])


# ── Request / Response Models ──────────────────────────────────────

class PredictionRequest(BaseModel):
    features: list[float] = Field(..., min_length=1, description="Feature vector for prediction")
    model: str = Field(default="xgboost", description="Model name to use")

class PredictionResponse(BaseModel):
    model_name: str
    value: float
    confidence: float
    horizon_days: int

class RegimeRequest(BaseModel):
    returns: list[float] = Field(..., min_length=10, description="Recent return series")

class RegimeResponse(BaseModel):
    regime: str
    model_name: str

class AnomalyRequest(BaseModel):
    data: list[list[float]] = Field(..., min_length=1, description="Data matrix for anomaly detection")

class AnomalyResponse(BaseModel):
    anomalies: list[dict]
    total_anomalies: int

class TrainRequest(BaseModel):
    model: str = Field(..., description="Model identifier to train")
    version: str = Field(default="v1", description="Version tag")
    features: list[list[float]] = Field(..., description="Training feature matrix")
    targets: list[float] = Field(..., description="Training targets")

class TrainResponse(BaseModel):
    artifact_uri: str
    model_name: str
    version: str

class FeatureRequest(BaseModel):
    prices: list[float] = Field(..., min_length=20, description="Price series")

class FeatureResponse(BaseModel):
    features: list[list[float]]
    feature_names: list[str]


# ── Endpoints ──────────────────────────────────────────────────────

@router.post("/predict", response_model=PredictionResponse)
async def predict(
    request: PredictionRequest,
    use_case: Annotated[PredictUseCase, Depends(get_predictor)],
) -> PredictionResponse:
    """Run prediction using specified model."""
    features = np.array(request.features)
    result = await use_case.execute(features)
    return PredictionResponse(
        model_name=result.model_name,
        value=result.value,
        confidence=result.confidence,
        horizon_days=result.horizon_days,
    )


@router.post("/regime", response_model=RegimeResponse)
async def detect_regime(
    request: RegimeRequest,
    use_case: Annotated[DetectRegimeUseCase, Depends(get_regime_classifier)],
) -> RegimeResponse:
    """Classify current market regime."""
    features = np.array(request.returns)
    regime, stability = await use_case.execute(features)
    return RegimeResponse(regime=regime, stability=stability, model_name="HMM")


@router.post("/anomalies", response_model=AnomalyResponse)
async def detect_anomalies(
    request: AnomalyRequest,
    use_case: Annotated[DetectAnomalyUseCase, Depends(get_anomaly_detector)],
) -> AnomalyResponse:
    """Detect anomalies in financial data."""
    data = np.array(request.data)
    results = await use_case.execute(data)
    anomalies = [
        {"score": r.score, "is_anomaly": r.is_anomaly, "description": r.description}
        for r in results
    ]
    return AnomalyResponse(
        anomalies=anomalies,
        total_anomalies=sum(1 for r in results if r.is_anomaly),
    )


@router.post("/train", response_model=TrainResponse)
async def train_model(
    request: TrainRequest,
    use_case: Annotated[TrainModelUseCase, Depends(get_train_use_case)],
) -> TrainResponse:
    """Train a model and persist the artifact."""
    X = np.array(request.features)
    y = np.array(request.targets)
    uri = await use_case.execute(X, y, request.version)
    return TrainResponse(
        artifact_uri=uri,
        model_name=request.model,
        version=request.version,
    )


@router.post("/features", response_model=FeatureResponse)
async def engineer_features(request: FeatureRequest) -> FeatureResponse:
    """Compute technical features from price series."""
    from stratos_ml.adapters.feature_store import FeatureEngineer

    prices = np.array(request.prices)
    features = FeatureEngineer.technical_features(prices)
    return FeatureResponse(
        features=features.tolist(),
        feature_names=[
            "returns", "log_returns", "volatility_5d", "volatility_20d",
            "ma_ratio_5", "ma_ratio_20", "rsi_14", "momentum_10",
        ],
    )
