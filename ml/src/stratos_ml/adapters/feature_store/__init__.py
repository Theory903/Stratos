"""Feature engineering — transform raw market data into ML features.

Time-series aware feature engineering for financial data.
"""

from __future__ import annotations

import numpy as np


class FeatureEngineer:
    """Generate features from raw price/volume data.

    Produces a feature matrix for downstream ML models.
    """

    @staticmethod
    def technical_features(prices: np.ndarray, volumes: np.ndarray | None = None) -> np.ndarray:
        """Compute standard technical indicators as feature columns.

        Returns: (n_samples, n_features) array with columns:
            [returns, log_returns, volatility_5, volatility_20,
             ma_ratio_5, ma_ratio_20, rsi_14, momentum_10]
        """
        n = len(prices)
        features = []

        # 1. Simple returns
        returns = np.zeros(n)
        returns[1:] = np.diff(prices) / prices[:-1]
        features.append(returns)

        # 2. Log returns
        log_returns = np.zeros(n)
        log_returns[1:] = np.diff(np.log(prices + 1e-10))
        features.append(log_returns)

        # 3. Rolling volatility (5-day)
        vol_5 = _rolling_std(returns, 5)
        features.append(vol_5)

        # 4. Rolling volatility (20-day)
        vol_20 = _rolling_std(returns, 20)
        features.append(vol_20)

        # 5. MA crossover ratio (price / MA5)
        ma_5 = _rolling_mean(prices, 5)
        ma_ratio_5 = np.where(ma_5 > 0, prices / ma_5, 1.0)
        features.append(ma_ratio_5)

        # 6. MA crossover ratio (price / MA20)
        ma_20 = _rolling_mean(prices, 20)
        ma_ratio_20 = np.where(ma_20 > 0, prices / ma_20, 1.0)
        features.append(ma_ratio_20)

        # 7. RSI (14-day)
        rsi = _compute_rsi(prices, 14)
        features.append(rsi)

        # 8. Momentum (10-day)
        momentum = np.zeros(n)
        momentum[10:] = prices[10:] / prices[:-10] - 1.0
        features.append(momentum)

        return np.column_stack(features)

    @staticmethod
    def time_series_split(
        X: np.ndarray,
        y: np.ndarray,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
    ) -> tuple[
        tuple[np.ndarray, np.ndarray],
        tuple[np.ndarray, np.ndarray],
        tuple[np.ndarray, np.ndarray],
    ]:
        """Walk-forward split — never leaks future data into training."""
        n = len(X)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))

        return (
            (X[:train_end], y[:train_end]),
            (X[train_end:val_end], y[train_end:val_end]),
            (X[val_end:], y[val_end:]),
        )


def _rolling_mean(data: np.ndarray, window: int) -> np.ndarray:
    """Compute rolling mean with leading NaN fill."""
    result = np.zeros_like(data, dtype=float)
    for i in range(len(data)):
        start = max(0, i - window + 1)
        result[i] = data[start : i + 1].mean()
    return result


def _rolling_std(data: np.ndarray, window: int) -> np.ndarray:
    """Compute rolling standard deviation."""
    result = np.zeros_like(data, dtype=float)
    for i in range(len(data)):
        start = max(0, i - window + 1)
        result[i] = data[start : i + 1].std() if i >= 1 else 0.0
    return result


def _compute_rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
    """Relative Strength Index."""
    n = len(prices)
    rsi = np.full(n, 50.0)

    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    if len(gains) < period:
        return rsi

    avg_gain = gains[:period].mean()
    avg_loss = losses[:period].mean()

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss < 1e-10:
            rsi[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i + 1] = 100.0 - 100.0 / (1.0 + rs)

    return rsi
