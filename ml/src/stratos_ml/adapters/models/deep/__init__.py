"""Deep learning model adapters — LSTM, Autoencoder.

These implement Predictor and AnomalyDetector protocols.
Models are lazily imported so the service starts even without GPU.
"""

from __future__ import annotations

from typing import Any

import numpy as np


class LSTMPredictor:
    """Long Short-Term Memory network for sequential forecasting.

    Implements `Predictor` protocol.
    Builds a 2-layer LSTM with a linear projection head.
    """

    def __init__(
        self,
        input_dim: int = 1,
        hidden_dim: int = 64,
        num_layers: int = 2,
        dropout: float = 0.2,
        seq_length: int = 30,
        epochs: int = 50,
        lr: float = 0.001,
    ) -> None:
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.dropout = dropout
        self.seq_length = seq_length
        self.epochs = epochs
        self.lr = lr
        self._model: Any = None
        self._scaler_mean: float = 0.0
        self._scaler_std: float = 1.0

    def name(self) -> str:
        return f"LSTM(h={self.hidden_dim},L={self.num_layers})"

    def _build_model(self) -> Any:
        """Lazily build PyTorch model."""
        import torch
        import torch.nn as nn

        class LSTMNet(nn.Module):
            def __init__(self, input_dim: int, hidden_dim: int, num_layers: int, dropout: float):
                super().__init__()
                self.lstm = nn.LSTM(
                    input_dim, hidden_dim, num_layers,
                    batch_first=True, dropout=dropout if num_layers > 1 else 0.0,
                )
                self.fc = nn.Linear(hidden_dim, 1)

            def forward(self, x: torch.Tensor) -> torch.Tensor:
                lstm_out, _ = self.lstm(x)
                return self.fc(lstm_out[:, -1, :]).squeeze(-1)

        return LSTMNet(self.input_dim, self.hidden_dim, self.num_layers, self.dropout)

    def _create_sequences(self, data: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Create sliding window sequences for LSTM training."""
        X, y = [], []
        for i in range(len(data) - self.seq_length):
            X.append(data[i : i + self.seq_length])
            y.append(data[i + self.seq_length])
        return np.array(X), np.array(y)

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train LSTM on sequential data."""
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, TensorDataset

        # Normalize
        self._scaler_mean = float(y.mean())
        self._scaler_std = float(y.std()) or 1.0
        normalized = (y - self._scaler_mean) / self._scaler_std

        # Create sequences
        seq_X, seq_y = self._create_sequences(normalized)
        if len(seq_X) == 0:
            return

        # Reshape for LSTM: (batch, seq_len, input_dim)
        if seq_X.ndim == 2:
            seq_X = seq_X.reshape(seq_X.shape[0], seq_X.shape[1], 1)

        dataset = TensorDataset(
            torch.FloatTensor(seq_X),
            torch.FloatTensor(seq_y),
        )
        loader = DataLoader(dataset, batch_size=32, shuffle=True)

        self._model = self._build_model()
        optimizer = torch.optim.Adam(self._model.parameters(), lr=self.lr)
        criterion = nn.MSELoss()

        self._model.train()
        for epoch in range(self.epochs):
            for batch_X, batch_y in loader:
                optimizer.zero_grad()
                pred = self._model(batch_X)
                loss = criterion(pred, batch_y)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self._model.parameters(), 1.0)
                optimizer.step()

    def predict(self, features: np.ndarray) -> np.ndarray:
        """Predict next value given recent history."""
        if self._model is None:
            return np.zeros(1)

        import torch

        self._model.eval()
        normalized = (features - self._scaler_mean) / self._scaler_std

        # Take last seq_length values
        seq = normalized[-self.seq_length:]
        if len(seq) < self.seq_length:
            seq = np.pad(seq, (self.seq_length - len(seq), 0))

        x = torch.FloatTensor(seq).reshape(1, self.seq_length, 1)
        with torch.no_grad():
            pred = self._model(x).item()

        # Denormalize
        return np.array([pred * self._scaler_std + self._scaler_mean])


class AutoencoderDetector:
    """Autoencoder for anomaly detection.

    Implements `AnomalyDetector` protocol.
    Trains on normal data and flags high-reconstruction-error samples as anomalies.
    """

    def __init__(
        self,
        input_dim: int = 10,
        latent_dim: int = 3,
        epochs: int = 100,
        lr: float = 0.001,
    ) -> None:
        self.input_dim = input_dim
        self.latent_dim = latent_dim
        self.epochs = epochs
        self.lr = lr
        self._model: Any = None
        self._threshold: float = 0.0
        self._scaler_mean: np.ndarray | None = None
        self._scaler_std: np.ndarray | None = None

    def name(self) -> str:
        return f"Autoencoder(d={self.input_dim}→{self.latent_dim})"

    def _build_model(self) -> Any:
        """Build encoder-decoder architecture."""
        import torch
        import torch.nn as nn

        class AE(nn.Module):
            def __init__(self, input_dim: int, latent_dim: int):
                super().__init__()
                mid = (input_dim + latent_dim) // 2
                self.encoder = nn.Sequential(
                    nn.Linear(input_dim, mid), nn.ReLU(), nn.BatchNorm1d(mid),
                    nn.Linear(mid, latent_dim), nn.ReLU(),
                )
                self.decoder = nn.Sequential(
                    nn.Linear(latent_dim, mid), nn.ReLU(), nn.BatchNorm1d(mid),
                    nn.Linear(mid, input_dim),
                )

            def forward(self, x: torch.Tensor) -> torch.Tensor:
                return self.decoder(self.encoder(x))

        return AE(input_dim, latent_dim)

    def fit(self, data: np.ndarray) -> None:
        """Fit autoencoder on normal data and set reconstruction threshold."""
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, TensorDataset

        if data.ndim == 1:
            data = data.reshape(-1, 1)
        self.input_dim = data.shape[1]

        # Normalize
        self._scaler_mean = data.mean(axis=0)
        self._scaler_std = data.std(axis=0)
        self._scaler_std[self._scaler_std < 1e-8] = 1.0
        normalized = (data - self._scaler_mean) / self._scaler_std

        dataset = TensorDataset(torch.FloatTensor(normalized))
        loader = DataLoader(dataset, batch_size=64, shuffle=True)

        self._model = self._build_model()
        optimizer = torch.optim.Adam(self._model.parameters(), lr=self.lr)
        criterion = nn.MSELoss(reduction="none")

        self._model.train()
        for epoch in range(self.epochs):
            for (batch,) in loader:
                optimizer.zero_grad()
                recon = self._model(batch)
                loss = criterion(recon, batch).mean()
                loss.backward()
                optimizer.step()

        # Set threshold as 95th percentile of training reconstruction error
        self._model.eval()
        with torch.no_grad():
            recon = self._model(torch.FloatTensor(normalized))
            errors = ((recon - torch.FloatTensor(normalized)) ** 2).mean(dim=1).numpy()
            self._threshold = float(np.percentile(errors, 95))

    def detect(self, data: np.ndarray) -> np.ndarray:
        """Return anomaly scores in [0, 1]."""
        if self._model is None or self._scaler_mean is None:
            return np.zeros(data.shape[0] if data.ndim > 1 else 1)

        import torch

        if data.ndim == 1:
            data = data.reshape(-1, 1)

        normalized = (data - self._scaler_mean) / self._scaler_std
        self._model.eval()
        with torch.no_grad():
            recon = self._model(torch.FloatTensor(normalized))
            errors = ((recon - torch.FloatTensor(normalized)) ** 2).mean(dim=1).numpy()

        # Normalize scores relative to threshold
        if self._threshold > 0:
            scores = errors / (2 * self._threshold)
        else:
            scores = errors
        return np.clip(scores, 0.0, 1.0)
