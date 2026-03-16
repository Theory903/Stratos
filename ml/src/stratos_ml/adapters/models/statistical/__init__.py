"""Statistical model adapters — ARIMA, GARCH, PCA.

These implement the Predictor protocol from domain/ports.
Pure statistical methods — no ML training loops.
"""

from __future__ import annotations

import numpy as np
from scipy import stats


class ARIMAPredictor:
    """Auto-regressive Integrated Moving Average model.

    Implements `Predictor` protocol.
    Uses a simplified AR(p) implementation suitable for real-time inference.
    """

    def __init__(self, order: tuple[int, int, int] = (5, 1, 1)) -> None:
        self.p, self.d, self.q = order
        self._coeffs: np.ndarray | None = None
        self._intercept: float = 0.0
        self._name = f"ARIMA({self.p},{self.d},{self.q})"

    def name(self) -> str:
        return self._name

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Fit AR(p) model using OLS on differenced series."""
        # Difference the series d times
        series = y.copy()
        for _ in range(self.d):
            series = np.diff(series)

        # Build AR design matrix
        n = len(series)
        if n <= self.p:
            self._coeffs = np.zeros(self.p)
            return

        design = np.zeros((n - self.p, self.p))
        for i in range(self.p):
            design[:, i] = series[self.p - i - 1 : n - i - 1]

        target = series[self.p:]

        # OLS: β = (X'X)^(-1) X'y
        try:
            xt_x = design.T @ design
            xt_y = design.T @ target
            self._coeffs = np.linalg.solve(xt_x + 1e-8 * np.eye(self.p), xt_y)
            self._intercept = np.mean(target) - design.mean(axis=0) @ self._coeffs
        except np.linalg.LinAlgError:
            self._coeffs = np.zeros(self.p)

    def predict(self, features: np.ndarray) -> np.ndarray:
        """Predict next value(s) given recent history."""
        if self._coeffs is None:
            return np.zeros(1)

        # features should be last p values of the (differenced) series
        recent = features[-self.p:] if len(features) >= self.p else features
        pred = self._intercept + np.dot(
            self._coeffs[: len(recent)], recent[::-1]
        )
        return np.array([pred])


class GARCHVolatilityModel:
    """Generalized Autoregressive Conditional Heteroscedasticity model.

    Implements `Predictor` protocol.
    GARCH(1,1): σ²(t) = ω + α·ε²(t-1) + β·σ²(t-1)
    """

    def __init__(self, omega: float = 0.0001, alpha: float = 0.1, beta: float = 0.85) -> None:
        self.omega = omega
        self.alpha = alpha
        self.beta = beta
        self._fitted_variance: float = 0.0

    def name(self) -> str:
        return "GARCH(1,1)"

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Fit GARCH(1,1) by computing conditional variances on the return series."""
        returns = y if y.ndim == 1 else y.ravel()
        n = len(returns)
        variances = np.zeros(n)
        variances[0] = np.var(returns)

        for t in range(1, n):
            variances[t] = (
                self.omega
                + self.alpha * returns[t - 1] ** 2
                + self.beta * variances[t - 1]
            )

        self._fitted_variance = variances[-1]

    def predict(self, features: np.ndarray) -> np.ndarray:
        """Predict next-period volatility (σ)."""
        if features.size == 0:
            return np.array([np.sqrt(self._fitted_variance)])

        last_return = features[-1]
        next_var = (
            self.omega
            + self.alpha * last_return**2
            + self.beta * self._fitted_variance
        )
        self._fitted_variance = next_var
        return np.array([np.sqrt(next_var)])


class PCAFactorModel:
    """Principal Component Analysis for factor decomposition.

    Decomposes asset returns into orthogonal risk factors.
    NOT a Predictor but used as a feature engineering step.
    """

    def __init__(self, n_components: int = 5) -> None:
        self.n_components = n_components
        self._components: np.ndarray | None = None
        self._explained_variance: np.ndarray | None = None
        self._mean: np.ndarray | None = None

    def name(self) -> str:
        return f"PCA(k={self.n_components})"

    def fit(self, data: np.ndarray) -> None:
        """Fit PCA on return matrix (n_samples × n_assets)."""
        self._mean = data.mean(axis=0)
        centered = data - self._mean

        # SVD decomposition
        U, S, Vt = np.linalg.svd(centered, full_matrices=False)
        self._components = Vt[: self.n_components]
        self._explained_variance = (S[: self.n_components] ** 2) / (data.shape[0] - 1)

    def transform(self, data: np.ndarray) -> np.ndarray:
        """Project data onto principal components (factor loadings)."""
        if self._components is None or self._mean is None:
            return data
        centered = data - self._mean
        return centered @ self._components.T

    @property
    def explained_variance_ratio(self) -> np.ndarray | None:
        """Ratio of variance explained by each component."""
        if self._explained_variance is None:
            return None
        total = self._explained_variance.sum()
        return self._explained_variance / total if total > 0 else self._explained_variance
