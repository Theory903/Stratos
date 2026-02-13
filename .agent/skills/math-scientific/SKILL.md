---
name: math-scientific
description: Math and scientific computing standards — NumPy, SciPy, Polars, Pandas, numerical stability, precision, and financial computing
---

# Math & Scientific Computing

## NumPy — Vectorization Rules

1. **Never loop over arrays** — use vectorized operations or `np.vectorize`.
2. **Broadcasting** over explicit tiling.
3. **Pre-allocate** output arrays for large operations.
4. **Use `float64`** for financial calculations (not `float32`).

```python
import numpy as np

# Portfolio variance: w^T * Σ * w
def portfolio_variance(weights: np.ndarray, cov_matrix: np.ndarray) -> float:
    return float(weights @ cov_matrix @ weights)

# Vectorized returns calculation
def log_returns(prices: np.ndarray) -> np.ndarray:
    return np.diff(np.log(prices))
```

---

## Polars (Preferred for DataFrames)

```python
import polars as pl

df = pl.scan_parquet("data/prices.parquet")
result = (
    df.filter(pl.col("date") >= "2024-01-01")
    .group_by("ticker")
    .agg([
        pl.col("close").pct_change().std().alias("volatility"),
        pl.col("volume").mean().alias("avg_volume"),
    ])
    .sort("volatility", descending=True)
    .collect()
)
```

**Why Polars over Pandas**: Lazy evaluation, multi-threaded, no GIL bottleneck, consistent API, better memory efficiency.

---

## Financial Precision

### Rules
- **Use `Decimal`** for monetary values. Never `float` for money.
- **Specify rounding mode** explicitly (ROUND_HALF_UP for finance).
- **Store cents/basis points** as integers when possible.

```python
from decimal import Decimal, ROUND_HALF_UP

price = Decimal("19.99")
tax = price * Decimal("0.08")
total = (price + tax).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
```

### Numerical Stability
- Avoid subtracting nearly-equal numbers.
- Use log-space for products of probabilities.
- Use Kahan summation for large sums.
- Check condition numbers for matrix operations.

---

## SciPy — Optimization

```python
from scipy.optimize import minimize

# Portfolio optimization (minimize variance subject to target return)
result = minimize(
    fun=lambda w: w @ cov_matrix @ w,
    x0=np.ones(n) / n,
    method="SLSQP",
    bounds=[(0, 1)] * n,
    constraints=[
        {"type": "eq", "fun": lambda w: np.sum(w) - 1},
        {"type": "eq", "fun": lambda w: w @ returns - target_return},
    ],
)
```

---

## Rust — nalgebra / ndarray

```rust
use nalgebra::{DMatrix, DVector};

fn portfolio_risk(weights: &DVector<f64>, cov: &DMatrix<f64>) -> f64 {
    (weights.transpose() * cov * weights)[(0, 0)].sqrt()
}
```

---

## Key Libraries

| Language | Library | Purpose |
|---|---|---|
| Python | numpy | Array operations |
| Python | scipy | Optimization, statistics |
| Python | polars | DataFrames (preferred) |
| Python | pandas | DataFrames (legacy) |
| Python | sympy | Symbolic math |
| Python | statsmodels | Statistical modeling |
| Rust | nalgebra | Linear algebra |
| Rust | ndarray | N-dimensional arrays |
| Java | Apache Commons Math | Numerical methods |
| TS | mathjs | Math operations |
