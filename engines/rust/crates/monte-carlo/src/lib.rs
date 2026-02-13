//! Monte Carlo simulation engine.
pub mod sampler;

/// PathSampler — Open/Closed: add new stochastic processes without modifying MC engine.
pub trait PathSampler: Send + Sync {
    fn name(&self) -> &str;
    fn sample_path(&self, initial: f64, steps: usize) -> Vec<f64>;
}
