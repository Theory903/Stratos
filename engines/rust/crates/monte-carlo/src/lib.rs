//! Monte Carlo simulation engine.
//!
//! Provides a configurable simulator that uses pluggable `PathSampler`
//! implementations (OCP: add new stochastic processes without modifying this engine).

pub mod sampler;

use stratos_core::error::EngineError;
use stratos_core::math;
use stratos_core::traits::{Engine, PathSampler};

/// Result of a Monte Carlo simulation.
#[derive(Debug, Clone)]
pub struct SimulationResult {
    /// All simulated paths: paths[path_index][time_step]
    pub paths: Vec<Vec<f64>>,
    /// Mean terminal value
    pub mean_terminal: f64,
    /// Percentile-based terminal values
    pub percentiles: Percentiles,
    /// Probability of loss (terminal < initial)
    pub prob_loss: f64,
}

#[derive(Debug, Clone)]
pub struct Percentiles {
    pub p5: f64,
    pub p25: f64,
    pub p50: f64,
    pub p75: f64,
    pub p95: f64,
}

/// Monte Carlo engine — runs N-path simulations using a pluggable PathSampler.
pub struct MonteCarloEngine<S: PathSampler> {
    sampler: S,
}

impl<S: PathSampler> MonteCarloEngine<S> {
    pub fn new(sampler: S) -> Self {
        Self { sampler }
    }

    /// Run simulation and compute statistics.
    pub fn run(
        &self,
        initial_value: f64,
        num_paths: usize,
        horizon: usize,
    ) -> Result<SimulationResult, EngineError> {
        if num_paths == 0 || horizon == 0 {
            return Err(EngineError::InvalidInput(
                "num_paths and horizon must be > 0".into(),
            ));
        }

        let paths: Vec<Vec<f64>> = (0..num_paths)
            .map(|_| self.sampler.sample_path(initial_value, horizon))
            .collect();

        // Terminal values
        let terminals: Vec<f64> = paths.iter().map(|p| *p.last().unwrap_or(&0.0)).collect();

        let mean_terminal = math::mean(&terminals);
        let prob_loss = terminals.iter().filter(|&&v| v < initial_value).count() as f64
            / num_paths as f64;

        let mut sorted_terminals = terminals.clone();
        sorted_terminals.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));

        let percentile = |p: f64| -> f64 {
            let idx = (p * sorted_terminals.len() as f64).floor() as usize;
            sorted_terminals[idx.min(sorted_terminals.len() - 1)]
        };

        Ok(SimulationResult {
            paths,
            mean_terminal,
            percentiles: Percentiles {
                p5: percentile(0.05),
                p25: percentile(0.25),
                p50: percentile(0.50),
                p75: percentile(0.75),
                p95: percentile(0.95),
            },
            prob_loss,
        })
    }
}

impl<S: PathSampler + Send + Sync> Engine for MonteCarloEngine<S> {
    fn name(&self) -> &str {
        "MonteCarlo"
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::sampler::{GbmSampler, MeanRevertingSampler};

    #[test]
    fn test_gbm_simulation() {
        let sampler = GbmSampler::new(0.08, 0.2, 1.0 / 252.0);
        let engine = MonteCarloEngine::new(sampler);
        let result = engine.run(100.0, 1000, 252).unwrap();

        assert_eq!(result.paths.len(), 1000);
        assert!(result.mean_terminal > 0.0);
        assert!(result.percentiles.p50 > 0.0);
        assert!(result.prob_loss < 0.5); // Most paths should end positive
    }

    #[test]
    fn test_mean_reverting_simulation() {
        let sampler = MeanRevertingSampler::new(100.0, 0.5, 0.15);
        let engine = MonteCarloEngine::new(sampler);
        let result = engine.run(90.0, 500, 252).unwrap();

        // Should revert toward 100
        assert!(result.mean_terminal > 90.0);
    }

    #[test]
    fn test_percentile_ordering() {
        let sampler = GbmSampler::new(0.05, 0.15, 1.0 / 252.0);
        let engine = MonteCarloEngine::new(sampler);
        let result = engine.run(100.0, 5000, 100).unwrap();

        assert!(result.percentiles.p5 <= result.percentiles.p25);
        assert!(result.percentiles.p25 <= result.percentiles.p50);
        assert!(result.percentiles.p50 <= result.percentiles.p75);
        assert!(result.percentiles.p75 <= result.percentiles.p95);
    }

    #[test]
    fn test_zero_paths_error() {
        let sampler = GbmSampler::new(0.05, 0.15, 1.0 / 252.0);
        let engine = MonteCarloEngine::new(sampler);
        assert!(engine.run(100.0, 0, 252).is_err());
    }
}
