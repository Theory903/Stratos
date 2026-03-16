//! Fiscal sustainability engine — sovereign debt, currency, and policy scoring.

use serde::{Deserialize, Serialize};
use stratos_core::error::EngineError;
use stratos_core::traits::{Engine, Scorable};
use stratos_core::types::{ConfidenceBand, SovereignProfile};

/// Fiscal sustainability score and components.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FiscalScore {
    /// Overall sustainability score [0, 100]
    pub total_score: f64,
    pub debt_score: f64,
    pub reserves_score: f64,
    pub deficit_score: f64,
    pub stability_score: f64,
    pub fx_score: f64,
    pub risk_tier: RiskTier,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RiskTier {
    Low,
    Moderate,
    Elevated,
    High,
    Critical,
}

/// Fiscal sustainability engine.
pub struct FiscalEngine;

impl Engine for FiscalEngine {
    fn name(&self) -> &str {
        "FiscalSustainability"
    }
}

impl Scorable for FiscalEngine {
    type Input = SovereignProfile;

    fn score(
        &self,
        input: &SovereignProfile,
    ) -> Result<(f64, ConfidenceBand), EngineError> {
        let result = self.analyze(input)?;
        let normalized = result.total_score / 100.0;
        Ok((normalized, ConfidenceBand::new(0.75)))
    }
}

impl FiscalEngine {
    /// Comprehensive fiscal analysis of a sovereign profile.
    pub fn analyze(&self, profile: &SovereignProfile) -> Result<FiscalScore, EngineError> {
        // Debt/GDP scoring (lower is better)
        let debt_score = Self::score_metric(profile.debt_gdp, &[
            (30.0, 100.0),
            (60.0, 80.0),
            (90.0, 60.0),
            (120.0, 40.0),
            (150.0, 20.0),
        ]);

        // FX reserves scoring (higher is better)
        let reserves_score = Self::score_metric(profile.fx_reserves, &[
            (5.0, 20.0),
            (20.0, 40.0),
            (50.0, 60.0),
            (100.0, 80.0),
            (200.0, 100.0),
        ]);

        // Fiscal deficit scoring (closer to 0 or surplus is better)
        let deficit_abs = profile.fiscal_deficit.abs();
        let deficit_score = Self::score_metric(deficit_abs, &[
            (1.0, 100.0),
            (3.0, 80.0),
            (5.0, 60.0),
            (8.0, 40.0),
            (12.0, 20.0),
        ]);

        // Political stability scoring (higher is better, 0-1 scale)
        let stability_score = profile.political_stability * 100.0;

        // Currency volatility scoring (lower is better)
        let fx_score = Self::score_metric(profile.currency_volatility, &[
            (0.02, 100.0),
            (0.05, 80.0),
            (0.10, 60.0),
            (0.20, 40.0),
            (0.40, 20.0),
        ]);

        // Weighted total
        let total_score = debt_score * 0.30
            + reserves_score * 0.15
            + deficit_score * 0.25
            + stability_score * 0.15
            + fx_score * 0.15;

        let risk_tier = match total_score as u32 {
            80..=100 => RiskTier::Low,
            60..=79 => RiskTier::Moderate,
            40..=59 => RiskTier::Elevated,
            20..=39 => RiskTier::High,
            _ => RiskTier::Critical,
        };

        Ok(FiscalScore {
            total_score,
            debt_score,
            reserves_score,
            deficit_score,
            stability_score,
            fx_score,
            risk_tier,
        })
    }

    /// Linear interpolation scoring with breakpoints.
    fn score_metric(value: f64, breakpoints: &[(f64, f64)]) -> f64 {
        if breakpoints.is_empty() {
            return 50.0;
        }
        if value <= breakpoints[0].0 {
            return breakpoints[0].1;
        }
        if value >= breakpoints[breakpoints.len() - 1].0 {
            return breakpoints[breakpoints.len() - 1].1;
        }
        for i in 0..breakpoints.len() - 1 {
            let (v0, s0) = breakpoints[i];
            let (v1, s1) = breakpoints[i + 1];
            if value >= v0 && value <= v1 {
                let t = (value - v0) / (v1 - v0);
                return s0 + t * (s1 - s0);
            }
        }
        50.0
    }
}

/// Debt sustainability stress tester.
pub struct DebtStressTester;

impl DebtStressTester {
    /// Project debt/GDP trajectory under stress scenarios.
    pub fn project_debt_trajectory(
        initial_debt_gdp: f64,
        growth_rate: f64,
        interest_rate: f64,
        primary_deficit_gdp: f64,
        years: usize,
    ) -> Vec<f64> {
        let mut trajectory = Vec::with_capacity(years + 1);
        let mut debt_gdp = initial_debt_gdp;
        trajectory.push(debt_gdp);

        for _ in 0..years {
            // Debt dynamics: d(t+1) = d(t) * (1+r)/(1+g) + pd
            debt_gdp = debt_gdp * (1.0 + interest_rate) / (1.0 + growth_rate)
                + primary_deficit_gdp;
            trajectory.push(debt_gdp);
        }
        trajectory
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_strong_sovereign() {
        let engine = FiscalEngine;
        let profile = SovereignProfile {
            country_code: "CH".to_string(),
            debt_gdp: 40.0,
            fx_reserves: 100.0,
            fiscal_deficit: -1.0,
            political_stability: 0.9,
            currency_volatility: 0.03,
        };
        let result = engine.analyze(&profile).unwrap();
        assert!(result.total_score > 70.0);
        matches!(result.risk_tier, RiskTier::Low | RiskTier::Moderate);
    }

    #[test]
    fn test_weak_sovereign() {
        let engine = FiscalEngine;
        let profile = SovereignProfile {
            country_code: "XX".to_string(),
            debt_gdp: 140.0,
            fx_reserves: 10.0,
            fiscal_deficit: -10.0,
            political_stability: 0.2,
            currency_volatility: 0.35,
        };
        let result = engine.analyze(&profile).unwrap();
        assert!(result.total_score < 40.0);
    }

    #[test]
    fn test_debt_trajectory() {
        let trajectory = DebtStressTester::project_debt_trajectory(
            80.0, 0.03, 0.05, 2.0, 10,
        );
        assert_eq!(trajectory.len(), 11);
        // Debt should increase when r > g and deficits persist
        assert!(trajectory.last().unwrap() > &80.0);
    }
}
