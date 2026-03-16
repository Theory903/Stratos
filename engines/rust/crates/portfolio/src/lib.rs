//! Portfolio optimization engine — Mean-Variance, Equal Weight, Risk Parity.
//!
//! Implements the `AllocationStrategy` trait (OCP: add new strategies by
//! implementing the trait, not modifying this code).

pub mod strategy;

use stratos_core::error::EngineError;
use stratos_core::math;
use stratos_core::traits::{AllocationConstraints, AllocationStrategy, Engine};

/// Equal-weight allocator — baseline strategy.
pub struct EqualWeightAllocator;

impl Engine for EqualWeightAllocator {
    fn name(&self) -> &str {
        "EqualWeight"
    }
}

impl AllocationStrategy for EqualWeightAllocator {
    fn allocate(
        &self,
        expected_returns: &[f64],
        _covariance: &[Vec<f64>],
        constraints: &AllocationConstraints,
    ) -> Result<Vec<f64>, EngineError> {
        let n = expected_returns.len();
        if n == 0 {
            return Err(EngineError::InvalidInput(
                "Cannot allocate to zero assets".into(),
            ));
        }
        let w = 1.0 / n as f64;
        let w_clamped = w.clamp(constraints.min_weight, constraints.max_weight);
        Ok(vec![w_clamped; n])
    }
}

/// Mean-Variance Optimizer using gradient descent on Sharpe ratio.
///
/// Iteratively adjusts weights to maximize the Sharpe ratio
/// (return - risk_free) / volatility, subject to constraints.
pub struct MeanVarianceOptimizer {
    pub risk_free_rate: f64,
    pub learning_rate: f64,
    pub max_iterations: usize,
    pub tolerance: f64,
}

impl Default for MeanVarianceOptimizer {
    fn default() -> Self {
        Self {
            risk_free_rate: 0.02,
            learning_rate: 0.001,
            max_iterations: 10000,
            tolerance: 1e-6,
        }
    }
}

impl Engine for MeanVarianceOptimizer {
    fn name(&self) -> &str {
        "MeanVarianceOptimizer"
    }
}

impl AllocationStrategy for MeanVarianceOptimizer {
    fn allocate(
        &self,
        expected_returns: &[f64],
        covariance: &[Vec<f64>],
        constraints: &AllocationConstraints,
    ) -> Result<Vec<f64>, EngineError> {
        let n = expected_returns.len();
        if n == 0 {
            return Err(EngineError::InvalidInput(
                "Cannot allocate to zero assets".into(),
            ));
        }
        if covariance.len() != n || covariance.iter().any(|row| row.len() != n) {
            return Err(EngineError::DimensionMismatch {
                expected: n,
                actual: covariance.len(),
            });
        }

        // Initialize with equal weights or current weights
        let mut weights = constraints
            .current_weights
            .clone()
            .unwrap_or_else(|| vec![1.0 / n as f64; n]);
        let mut prev_sharpe = f64::NEG_INFINITY;

        for iter in 0..self.max_iterations {
            let port_ret = math::portfolio_return(&weights, expected_returns);
            let port_var = math::portfolio_variance(&weights, covariance);
            let port_vol = port_var.sqrt();

            // Calculate Transaction Costs & Slippage (Subsystem C.Nonlinear)
            let mut trans_cost = 0.0;
            if let Some(ref initial_w) = constraints.current_weights {
                let mut total_cost = 0.0;
                for (w, w0) in weights.iter().zip(initial_w.iter()) {
                    let turnover = (w - w0).abs();
                    // Linear TC
                    let linear = turnover * constraints.transaction_cost;
                    // Nonlinear Slippage: k * |turnover|^alpha
                    let slippage = constraints.slippage_coeff * turnover.powf(constraints.slippage_exponent);
                    total_cost += linear + slippage;
                }
                trans_cost = total_cost * constraints.cost_regime_multiplier;
            }

            let net_ret = port_ret - trans_cost;

            if port_vol <= 0.0 {
                break;
            }

            let sharpe = math::sharpe_ratio(net_ret, self.risk_free_rate, port_vol);

            // Check convergence
            if (sharpe - prev_sharpe).abs() < self.tolerance {
                break;
            }
            if iter == self.max_iterations - 1 {
                return Err(EngineError::ConvergenceFailed {
                    iterations: self.max_iterations,
                });
            }
            prev_sharpe = sharpe;

            // Gradient of Sharpe w.r.t. weights (analytical)
            let mut grad = vec![0.0; n];
            for i in 0..n {
                let d_ret = expected_returns[i];
                let d_var: f64 = (0..n).map(|j| weights[j] * covariance[i][j]).sum::<f64>() * 2.0;
                let d_vol = d_var / (2.0 * port_vol);

                // Add Transaction Cost & Slippage Gradient
                let mut d_cost = 0.0;
                if let Some(ref initial_w) = constraints.current_weights {
                    let diff = weights[i] - initial_w[i];
                    let sgn = if diff > 0.0 { 1.0 } else if diff < 0.0 { -1.0 } else { 0.0 };
                    
                    // d(Linear)/dw = sgn * cost
                    let d_linear = sgn * constraints.transaction_cost;
                    // d(Slippage)/dw = k * alpha * |diff|^(alpha-1) * sgn
                    let d_slippage = constraints.slippage_coeff 
                        * constraints.slippage_exponent 
                        * diff.abs().powf(constraints.slippage_exponent - 1.0)
                        * sgn;
                    
                    d_cost = (d_linear + d_slippage) * constraints.cost_regime_multiplier;
                }

                // d(Sharpe)/dw_i = ((d_ret - d_cost) * vol - (net_ret - rf) * d_vol) / vol^2
                grad[i] = ((d_ret - d_cost) * port_vol - (net_ret - self.risk_free_rate) * d_vol)
                    / (port_vol * port_vol);
            }

            // Update weights via gradient ascent
            for i in 0..n {
                weights[i] += self.learning_rate * grad[i];
            }

            // Apply constraints, liquidity limits and re-normalize
            for i in 0..n {
                let mut upper = constraints.max_weight;
                if let Some(ref liq) = constraints.liquidity_limit {
                    if i < liq.len() {
                        upper = upper.min(liq[i]);
                    }
                }
                weights[i] = weights[i].clamp(constraints.min_weight, upper);
            }
            let sum: f64 = weights.iter().sum();
            if sum > 0.0 {
                for w in &mut weights {
                    *w /= sum;
                }
            }
        }

        Ok(weights)
    }
}

/// Risk Parity allocator — weights inversely proportional to volatility.
pub struct RiskParityAllocator;

impl Engine for RiskParityAllocator {
    fn name(&self) -> &str {
        "RiskParity"
    }
}

impl AllocationStrategy for RiskParityAllocator {
    fn allocate(
        &self,
        _expected_returns: &[f64],
        covariance: &[Vec<f64>],
        constraints: &AllocationConstraints,
    ) -> Result<Vec<f64>, EngineError> {
        let n = covariance.len();
        if n == 0 {
            return Err(EngineError::InvalidInput(
                "Cannot allocate to zero assets".into(),
            ));
        }

        // Weight inversely proportional to individual asset volatility
        let inv_vols: Vec<f64> = (0..n)
            .map(|i| {
                let vol = covariance[i][i].sqrt();
                if vol > 0.0 {
                    1.0 / vol
                } else {
                    1.0
                }
            })
            .collect();

        let sum: f64 = inv_vols.iter().sum();
        let mut weights: Vec<f64> = inv_vols.iter().map(|v| v / sum).collect();

        // Apply constraints
        for w in &mut weights {
            *w = w.clamp(constraints.min_weight, constraints.max_weight);
        }

        // Re-normalize
        let sum: f64 = weights.iter().sum();
        if sum > 0.0 {
            for w in &mut weights {
                *w /= sum;
            }
        }

        Ok(weights)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_data() -> (Vec<f64>, Vec<Vec<f64>>) {
        let returns = vec![0.12, 0.10, 0.08];
        let cov = vec![
            vec![0.04, 0.006, 0.002],
            vec![0.006, 0.09, 0.004],
            vec![0.002, 0.004, 0.01],
        ];
        (returns, cov)
    }

    #[test]
    fn test_equal_weight() {
        let (ret, cov) = sample_data();
        let alloc = EqualWeightAllocator;
        let w = alloc
            .allocate(&ret, &cov, &AllocationConstraints::default())
            .unwrap();
        assert_eq!(w.len(), 3);
        assert!((w.iter().sum::<f64>() - 1.0).abs() < 1e-10);
    }

    #[test]
    fn test_mean_variance() {
        let (ret, cov) = sample_data();
        let optimizer = MeanVarianceOptimizer::default();
        let w = optimizer
            .allocate(&ret, &cov, &AllocationConstraints::default())
            .unwrap();
        assert_eq!(w.len(), 3);
        assert!((w.iter().sum::<f64>() - 1.0).abs() < 0.01);
        // Should overweight the high-return, low-vol asset (index 2: bonds)
        // or balance based on risk-adjusted returns
    }

    #[test]
    fn test_transaction_costs() {
        let (ret, cov) = sample_data();
        let optimizer = MeanVarianceOptimizer::default();
        
        // Scenario 1: No Transaction Cost
        let constraints_no_tc = AllocationConstraints::default();
        let w_no_tc = optimizer.allocate(&ret, &cov, &constraints_no_tc).unwrap();
        
        // Scenario 2: Moderate Transaction Cost, Initial Weights = Equal
        let mut constraints_high_tc = AllocationConstraints::default();
        constraints_high_tc.current_weights = Some(vec![0.33, 0.33, 0.34]);
        constraints_high_tc.transaction_cost = 0.1; // 10% cost
        
        let w_high_tc = optimizer.allocate(&ret, &cov, &constraints_high_tc).unwrap();
        
        // It should stay relatively close (within 10%)
        for i in 0..3 {
            assert!((w_high_tc[i] - 0.33).abs() < 0.1);
        }
        
        // Scenario 3: Liquidity Constraints
        let mut constraints_liq = AllocationConstraints::default();
        constraints_liq.liquidity_limit = Some(vec![0.1, 0.1, 1.0]); // Limit equities to 10% each
        let w_liq = optimizer.allocate(&ret, &cov, &constraints_liq).unwrap();
        
        assert!(w_liq[0] <= 0.101);
        assert!(w_liq[1] <= 0.101);
    }

    #[test]
    fn test_risk_parity() {
        let (ret, cov) = sample_data();
        let alloc = RiskParityAllocator;
        let w = alloc
            .allocate(&ret, &cov, &AllocationConstraints::default())
            .unwrap();
        assert_eq!(w.len(), 3);
        assert!((w.iter().sum::<f64>() - 1.0).abs() < 0.01);
        // Bonds (low vol) should have highest weight
        assert!(w[2] > w[0]); // bonds > equities
    }

    #[test]
    fn test_nonlinear_slippage() {
        let (ret, cov) = sample_data();
        let optimizer = MeanVarianceOptimizer::default();
        
        let initial_weights = vec![0.33, 0.33, 0.34];
        let mut constraints = AllocationConstraints::default();
        constraints.current_weights = Some(initial_weights.clone());
        constraints.slippage_coeff = 2.0;    // Significant slippage
        constraints.slippage_exponent = 2.0; // Quadratic cost
        
        // Scenario 1: Normal Regime (mult = 1.0)
        constraints.cost_regime_multiplier = 1.0;
        let w_normal = optimizer.allocate(&ret, &cov, &constraints).unwrap();
        
        // Scenario 2: Crisis Regime (mult = 10.0) -> Should be "stickier"
        constraints.cost_regime_multiplier = 10.0;
        let w_crisis = optimizer.allocate(&ret, &cov, &constraints).unwrap();
        
        for i in 0..3 {
            let dist_normal = (w_normal[i] - initial_weights[i]).abs();
            let dist_crisis = (w_crisis[i] - initial_weights[i]).abs();
            
            // Crisis weights MUST be closer or equal to initial weights than normal weights
            assert!(dist_crisis <= dist_normal + 1e-6, 
                "Asset {}: Crisis distance {} > Normal distance {}", i, dist_crisis, dist_normal);
        }
    }

    #[test]
    fn test_empty_portfolio() {
        let alloc = EqualWeightAllocator;
        let result = alloc.allocate(&[], &[], &AllocationConstraints::default());
        assert!(result.is_err());
    }
}
