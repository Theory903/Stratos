//! Core domain types used across all engine crates.

use serde::{Deserialize, Serialize};

/// Global macro state snapshot.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorldState {
    pub interest_rate: f64,
    pub inflation: f64,
    pub liquidity_index: f64,
    pub geopolitical_risk: f64,
    pub volatility_index: f64,
    pub commodity_index: f64,
}

/// Portfolio with asset weights and risk metrics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Portfolio {
    pub assets: Vec<Asset>,
    pub weights: Vec<f64>,
    pub expected_return: f64,
    pub expected_drawdown: f64,
    pub risk_score: f64,
}

/// Single asset in a portfolio.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Asset {
    pub ticker: String,
    pub asset_class: AssetClass,
    pub current_price: f64,
}

/// Classification of financial assets.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum AssetClass {
    Equity,
    Bond,
    Crypto,
    Commodity,
    Fx,
}

/// Sovereign nation profile.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SovereignProfile {
    pub country_code: String,
    pub debt_gdp: f64,
    pub fx_reserves: f64,
    pub fiscal_deficit: f64,
    pub political_stability: f64,
    pub currency_volatility: f64,
}

/// Corporate financial profile.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompanyProfile {
    pub ticker: String,
    pub name: String,
    pub earnings_quality: f64,
    pub leverage_ratio: f64,
    pub free_cash_flow_stability: f64,
    pub fraud_score: f64,
    pub moat_score: f64,
}

/// Confidence band for probabilistic outputs.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfidenceBand {
    /// Score in [0.0, 1.0]
    pub score: f64,
    /// Calibration level: high, medium, low
    pub calibration: String,
}

impl ConfidenceBand {
    pub fn new(score: f64) -> Self {
        let calibration = if score >= 0.8 {
            "high"
        } else if score >= 0.5 {
            "medium"
        } else {
            "low"
        };
        Self {
            score,
            calibration: calibration.to_string(),
        }
    }
}
