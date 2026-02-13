//! AllocationStrategy — Open/Closed: add strategies without modifying existing.

use stratos_core::error::EngineError;
use stratos_core::traits::AllocationConstraints;

/// Strategy for computing optimal portfolio weights.
pub trait AllocationStrategy: Send + Sync {
    fn name(&self) -> &str;
    fn optimize(
        &self,
        expected_returns: &[f64],
        covariance: &[Vec<f64>],
        constraints: &AllocationConstraints,
    ) -> Result<Vec<f64>, EngineError>;
}
