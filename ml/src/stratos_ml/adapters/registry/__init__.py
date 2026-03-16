"""Model registry adapter — filesystem-based model persistence.

Implements `ModelStore` protocol.
Uses joblib for sklearn/xgboost and torch.save for PyTorch models.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


class FileModelStore:
    """Persist models to local filesystem with versioning.

    Implements `ModelStore` protocol.
    Layout: {base_path}/{model_name}/{version}/model.pkl + metadata.json
    """

    def __init__(self, base_path: str = "./model_artifacts") -> None:
        self._base = Path(base_path)
        self._base.mkdir(parents=True, exist_ok=True)

    def save(self, model: Any, name: str, version: str) -> str:
        """Persist model artifact and return URI."""
        model_dir = self._base / name / version
        model_dir.mkdir(parents=True, exist_ok=True)

        model_path = model_dir / "model.pkl"

        # Try torch first, fall back to joblib
        if hasattr(model, "state_dict"):
            import torch
            torch.save(model.state_dict(), model_path)
        else:
            import joblib
            joblib.dump(model, model_path)

        # Save metadata
        metadata = {
            "model_name": name,
            "version": version,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "model_type": type(model).__name__,
        }
        with open(model_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        return str(model_path)

    def load(self, name: str, version: str) -> Any:
        """Load a persisted model artifact."""
        model_path = self._base / name / version / "model.pkl"
        if not model_path.exists():
            raise FileNotFoundError(f"Model {name}/{version} not found at {model_path}")

        # Try joblib first (most common)
        try:
            import joblib
            return joblib.load(model_path)
        except Exception:
            import torch
            return torch.load(model_path, weights_only=True)

    def list_versions(self, name: str) -> list[str]:
        """List all saved versions of a model."""
        model_dir = self._base / name
        if not model_dir.exists():
            return []
        return sorted(
            [d.name for d in model_dir.iterdir() if d.is_dir()],
            reverse=True,
        )
