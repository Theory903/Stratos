//! Core traits — abstract interfaces for Dependency Inversion.
//!
//! Engine crates implement these traits. Consumers depend on traits, not
//! concrete implementations (D in SOLID). Traits are narrow (I in SOLID).

use crate::types::{ConfidenceBand, WorldState};

/// An engine that can compute/score something (Single Responsibility).
pub trait Engine: Send + Sync {
    /// Human-readable name of this engine.
    fn name(&self) -> &str;
}

/// Strategy for portfolio allocation (Open/Closed: add strategies without modifying existing).
pub trait AllocationStrategy: Engine {
    /// Compute optimal weights given universe and constraints.
    fn allocate(
        &self,
        expected_returns: &[f64],
        covariance: &[Vec<f64>],
        constraints: &AllocationConstraints,
    ) -> Result<Vec<f64>, crate::error::EngineError>;
}

/// Risk measure computation (Interface Segregation: narrow trait).
pub trait RiskMeasure: Engine {
    /// Compute risk metric for given returns.
    fn compute(&self, returns: &[f64], confidence_level: f64) -> f64;
}

/// Simulatable engine — can run simulations with world state.
pub trait Simulatable: Engine {
    type Output;

    /// Run simulation with given parameters.
    fn simulate(
        &self,
        world_state: &WorldState,
        num_paths: usize,
        horizon: usize,
    ) -> Result<Self::Output, crate::error::EngineError>;
}

/// Scorable entity — can produce a scored assessment with confidence.
pub trait Scorable: Engine {
    type Input;

    fn score(&self, input: &Self::Input) -> Result<(f64, ConfidenceBand), crate::error::EngineError>;
}

/// Path sampling for Monte Carlo (Open/Closed: add samplers without modifying MC engine).
pub trait PathSampler: Send + Sync {
    fn sample_path(&self, initial: f64, steps: usize) -> Vec<f64>;
}

/// Allocation constraints value object.
#[derive(Debug, Clone)]
pub struct AllocationConstraints {
    pub min_weight: f64,
    pub max_weight: f64,
    pub target_return: Option<f64>,
    pub max_risk: Option<f64>,
    
    // Institutional Grade: Liquidity & Cost
    /// Existing weights for turnover/cost penalty calculation
    pub current_weights: Option<Vec<f64>>,
    /// Fixed transaction cost (e.g., 0.001 for 10bps)
    pub transaction_cost: f64,
    /// Nonlinear slippage coefficient (impact per unit turnover)
    pub slippage_coeff: f64,
    /// Nonlinear slippage exponent (e.g., 1.5 or 2.0)
    pub slippage_exponent: f64,
    /// Multiplier for all costs based on system regime (Subsystem G)
    pub cost_regime_multiplier: f64,
    /// Max weight per asset based on liquidity (ADV)
    pub liquidity_limit: Option<Vec<f64>>,
}

impl Default for AllocationConstraints {
    fn default() -> Self {
        Self {
            min_weight: 0.0,
            max_weight: 1.0,
            target_return: None,
            max_risk: None,
            current_weights: None,
            transaction_cost: 0.0,
            slippage_coeff: 0.0,
            slippage_exponent: 1.5,
            cost_regime_multiplier: 1.0,
            liquidity_limit: None,
        }
    }
}
