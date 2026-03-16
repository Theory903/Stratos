//! Risk measurement engine — VaR, CVaR, stress testing, tail risk.
//!
//! Implements the `RiskMeasure` trait (ISP: each metric is a narrow interface).

pub mod measure;

use stratos_core::math;
use stratos_core::traits::{Engine, RiskMeasure};

/// Historical Value-at-Risk (VaR).
///
/// Estimates the maximum expected loss at a given confidence level
/// using the historical simulation method (non-parametric).
pub struct HistoricalVaR;

impl Engine for HistoricalVaR {
    fn name(&self) -> &str {
        "HistoricalVaR"
    }
}

impl RiskMeasure for HistoricalVaR {
    fn compute(&self, returns: &[f64], confidence_level: f64) -> f64 {
        if returns.is_empty() {
            return 0.0;
        }
        let mut sorted = returns.to_vec();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));

        let index = ((1.0 - confidence_level) * sorted.len() as f64).floor() as usize;
        let index = index.min(sorted.len() - 1);
        -sorted[index] // VaR is positive (loss amount)
    }
}

/// Parametric VaR assuming normal distribution.
pub struct ParametricVaR;

impl Engine for ParametricVaR {
    fn name(&self) -> &str {
        "ParametricVaR"
    }
}

impl RiskMeasure for ParametricVaR {
    fn compute(&self, returns: &[f64], confidence_level: f64) -> f64 {
        if returns.is_empty() {
            return 0.0;
        }
        let mu = math::mean(returns);
        let sigma = math::std_dev(returns);

        // Z-score for given confidence level (approximation)
        let z = inv_normal_cdf(1.0 - confidence_level);
        -(mu + z * sigma)
    }
}

/// Conditional Value-at-Risk (CVaR / Expected Shortfall).
///
/// Average loss beyond VaR — captures tail risk better than VaR.
pub struct ConditionalVaR;

impl Engine for ConditionalVaR {
    fn name(&self) -> &str {
        "CVaR"
    }
}

impl RiskMeasure for ConditionalVaR {
    fn compute(&self, returns: &[f64], confidence_level: f64) -> f64 {
        if returns.is_empty() {
            return 0.0;
        }
        let mut sorted = returns.to_vec();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));

        let cutoff_index = ((1.0 - confidence_level) * sorted.len() as f64).ceil() as usize;
        let cutoff_index = cutoff_index.max(1).min(sorted.len());

        let tail_mean: f64 = sorted[..cutoff_index].iter().sum::<f64>() / cutoff_index as f64;
        -tail_mean
    }
}

/// Maximum Drawdown risk measure.
pub struct MaxDrawdownMeasure;

impl Engine for MaxDrawdownMeasure {
    fn name(&self) -> &str {
        "MaxDrawdown"
    }
}

impl RiskMeasure for MaxDrawdownMeasure {
    fn compute(&self, returns: &[f64], _confidence_level: f64) -> f64 {
        math::max_drawdown(returns)
    }
}

/// Volatility (annualized standard deviation).
pub struct VolatilityMeasure {
    pub trading_days: f64,
}

impl Default for VolatilityMeasure {
    fn default() -> Self {
        Self { trading_days: 252.0 }
    }
}

impl Engine for VolatilityMeasure {
    fn name(&self) -> &str {
        "Volatility"
    }
}

impl RiskMeasure for VolatilityMeasure {
    fn compute(&self, returns: &[f64], _confidence_level: f64) -> f64 {
        math::annualized_volatility(returns, self.trading_days)
    }
}

/// Approximate inverse normal CDF (Abramowitz & Stegun approximation).
fn inv_normal_cdf(p: f64) -> f64 {
    if p <= 0.0 {
        return f64::NEG_INFINITY;
    }
    if p >= 1.0 {
        return f64::INFINITY;
    }

    // Rational approximation
    let t = if p < 0.5 {
        (-2.0 * p.ln()).sqrt()
    } else {
        (-2.0 * (1.0 - p).ln()).sqrt()
    };

    let c0 = 2.515517;
    let c1 = 0.802853;
    let c2 = 0.010328;
    let d1 = 1.432788;
    let d2 = 0.189269;
    let d3 = 0.001308;

    let result = t - (c0 + c1 * t + c2 * t * t) / (1.0 + d1 * t + d2 * t * t + d3 * t * t * t);

    if p < 0.5 {
        -result
    } else {
        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_returns() -> Vec<f64> {
        vec![
            0.02, -0.01, 0.03, -0.04, 0.01, -0.02, 0.05, -0.03, 0.02, -0.06,
            0.04, -0.01, 0.03, -0.05, 0.02, -0.02, 0.01, -0.03, 0.04, -0.07,
        ]
    }

    #[test]
    fn test_historical_var() {
        let returns = sample_returns();
        let var = HistoricalVaR;
        let val = var.compute(&returns, 0.95);
        assert!(val > 0.0, "VaR should be positive");
        assert!(val < 0.1, "VaR should be reasonable");
    }

    #[test]
    fn test_parametric_var() {
        let returns = sample_returns();
        let var = ParametricVaR;
        let val = var.compute(&returns, 0.95);
        assert!(val > 0.0, "Parametric VaR should be positive");
    }

    #[test]
    fn test_cvar_greater_than_var() {
        let returns = sample_returns();
        let var_val = HistoricalVaR.compute(&returns, 0.95);
        let cvar_val = ConditionalVaR.compute(&returns, 0.95);
        // CVaR should be >= VaR (expected shortfall includes the tail)
        assert!(cvar_val >= var_val * 0.9, "CVaR should be >= VaR (approximately)");
    }

    #[test]
    fn test_max_drawdown() {
        let returns = sample_returns();
        let dd = MaxDrawdownMeasure.compute(&returns, 0.95);
        assert!(dd > 0.0 && dd < 1.0);
    }

    #[test]
    fn test_volatility() {
        let returns = sample_returns();
        let vol = VolatilityMeasure::default().compute(&returns, 0.95);
        assert!(vol > 0.0);
        assert!(vol < 1.0, "Annualized vol should be < 100%");
    }

    #[test]
    fn test_inv_normal_cdf() {
        let z = inv_normal_cdf(0.05);
        assert!((z - (-1.645)).abs() < 0.01);
    }
}
