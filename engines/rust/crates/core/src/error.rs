//! Engine error types.

use thiserror::Error;

#[derive(Error, Debug)]
pub enum EngineError {
    #[error("Invalid input: {0}")]
    InvalidInput(String),

    #[error("Computation failed: {0}")]
    ComputationFailed(String),

    #[error("Convergence failure after {iterations} iterations")]
    ConvergenceFailed { iterations: usize },

    #[error("Dimension mismatch: expected {expected}, got {actual}")]
    DimensionMismatch { expected: usize, actual: usize },
}
