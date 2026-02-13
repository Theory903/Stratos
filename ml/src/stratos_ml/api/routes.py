"""ML API routes — thin delegation to use cases."""

from fastapi import APIRouter

router = APIRouter(tags=["ML"])


@router.post("/predict/{model_name}")
async def predict(model_name: str) -> dict:
    """Run prediction with a named model."""
    # TODO: wire use case via deps.py
    return {"status": "not_implemented", "model": model_name}


@router.get("/regime/current")
async def current_regime() -> dict:
    """Get current detected market regime."""
    return {"status": "not_implemented"}


@router.post("/anomaly/detect")
async def detect_anomaly() -> dict:
    """Detect anomalies in submitted data."""
    return {"status": "not_implemented"}
