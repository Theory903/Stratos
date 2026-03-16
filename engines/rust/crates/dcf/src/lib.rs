//! DCF valuation engine — Discounted Cash Flow and WACC computation.

use serde::{Deserialize, Serialize};
use stratos_core::error::EngineError;
use stratos_core::traits::Engine;

/// Inputs for DCF valuation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DcfInputs {
    /// Projected free cash flows for each future period
    pub free_cash_flows: Vec<f64>,
    /// Terminal growth rate (perpetuity)
    pub terminal_growth_rate: f64,
    /// Discount rate (WACC)
    pub discount_rate: f64,
    /// Number of shares outstanding
    pub shares_outstanding: f64,
    /// Net debt (debt - cash)
    pub net_debt: f64,
}

/// Result of DCF valuation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DcfResult {
    pub enterprise_value: f64,
    pub equity_value: f64,
    pub intrinsic_price: f64,
    pub terminal_value: f64,
    pub pv_cash_flows: f64,
    pub pv_terminal: f64,
}

/// WACC computation inputs.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WaccInputs {
    pub equity_market_cap: f64,
    pub total_debt: f64,
    pub cost_of_equity: f64,
    pub cost_of_debt: f64,
    pub tax_rate: f64,
}

/// DCF valuation engine.
pub struct DcfEngine;

impl Engine for DcfEngine {
    fn name(&self) -> &str {
        "DCF"
    }
}

impl DcfEngine {
    /// Compute intrinsic value using multi-stage DCF model.
    pub fn value(&self, inputs: &DcfInputs) -> Result<DcfResult, EngineError> {
        if inputs.discount_rate <= inputs.terminal_growth_rate {
            return Err(EngineError::InvalidInput(
                "Discount rate must exceed terminal growth rate".into(),
            ));
        }
        if inputs.shares_outstanding <= 0.0 {
            return Err(EngineError::InvalidInput(
                "Shares outstanding must be positive".into(),
            ));
        }
        if inputs.free_cash_flows.is_empty() {
            return Err(EngineError::InvalidInput(
                "At least one projected cash flow required".into(),
            ));
        }

        // Present value of projected cash flows
        let mut pv_cf = 0.0;
        for (i, &cf) in inputs.free_cash_flows.iter().enumerate() {
            pv_cf += cf / (1.0 + inputs.discount_rate).powi((i + 1) as i32);
        }

        // Terminal value using Gordon Growth Model
        let last_cf = *inputs.free_cash_flows.last().unwrap();
        let terminal_cf = last_cf * (1.0 + inputs.terminal_growth_rate);
        let terminal_value = terminal_cf / (inputs.discount_rate - inputs.terminal_growth_rate);

        // Present value of terminal value
        let n = inputs.free_cash_flows.len();
        let pv_terminal = terminal_value / (1.0 + inputs.discount_rate).powi(n as i32);

        // Enterprise and equity value
        let enterprise_value = pv_cf + pv_terminal;
        let equity_value = enterprise_value - inputs.net_debt;
        let intrinsic_price = equity_value / inputs.shares_outstanding;

        Ok(DcfResult {
            enterprise_value,
            equity_value,
            intrinsic_price,
            terminal_value,
            pv_cash_flows: pv_cf,
            pv_terminal,
        })
    }

    /// Compute Weighted Average Cost of Capital.
    pub fn wacc(inputs: &WaccInputs) -> f64 {
        let total = inputs.equity_market_cap + inputs.total_debt;
        if total <= 0.0 {
            return 0.0;
        }
        let equity_weight = inputs.equity_market_cap / total;
        let debt_weight = inputs.total_debt / total;

        equity_weight * inputs.cost_of_equity
            + debt_weight * inputs.cost_of_debt * (1.0 - inputs.tax_rate)
    }

    /// Sensitivity analysis — compute intrinsic price across a grid of
    /// discount rates and terminal growth rates.
    pub fn sensitivity_table(
        &self,
        base: &DcfInputs,
        discount_rates: &[f64],
        growth_rates: &[f64],
    ) -> Vec<Vec<Option<f64>>> {
        discount_rates
            .iter()
            .map(|&dr| {
                growth_rates
                    .iter()
                    .map(|&gr| {
                        let modified = DcfInputs {
                            discount_rate: dr,
                            terminal_growth_rate: gr,
                            ..base.clone()
                        };
                        self.value(&modified).ok().map(|r| r.intrinsic_price)
                    })
                    .collect()
            })
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_inputs() -> DcfInputs {
        DcfInputs {
            free_cash_flows: vec![100.0, 110.0, 121.0, 133.1, 146.41],
            terminal_growth_rate: 0.03,
            discount_rate: 0.10,
            shares_outstanding: 100.0,
            net_debt: 200.0,
        }
    }

    #[test]
    fn test_dcf_basic() {
        let engine = DcfEngine;
        let result = engine.value(&sample_inputs()).unwrap();

        assert!(result.enterprise_value > 0.0);
        assert!(result.equity_value > 0.0);
        assert!(result.intrinsic_price > 0.0);
        assert!(result.pv_terminal > result.pv_cash_flows); // Terminal usually dominates
    }

    #[test]
    fn test_dcf_validation() {
        let engine = DcfEngine;

        // Discount rate must exceed growth
        let mut bad = sample_inputs();
        bad.discount_rate = 0.02;
        bad.terminal_growth_rate = 0.03;
        assert!(engine.value(&bad).is_err());
    }

    #[test]
    fn test_wacc() {
        let w = DcfEngine::wacc(&WaccInputs {
            equity_market_cap: 800.0,
            total_debt: 200.0,
            cost_of_equity: 0.10,
            cost_of_debt: 0.05,
            tax_rate: 0.25,
        });
        // WACC = 0.8 * 0.10 + 0.2 * 0.05 * 0.75 = 0.08 + 0.0075 = 0.0875
        assert!((w - 0.0875).abs() < 0.0001);
    }

    #[test]
    fn test_sensitivity_table() {
        let engine = DcfEngine;
        let table = engine.sensitivity_table(
            &sample_inputs(),
            &[0.08, 0.10, 0.12],
            &[0.02, 0.03, 0.04],
        );
        assert_eq!(table.len(), 3);
        assert_eq!(table[0].len(), 3);
        // Lower discount → higher price
        assert!(table[0][1].unwrap() > table[2][1].unwrap());
    }
}
