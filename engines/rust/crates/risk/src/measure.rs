//! RiskMeasure trait — Interface Segregation: narrow per-metric interface.

/// Compute a single risk metric from return data.
pub trait RiskMeasure: Send + Sync {
    fn name(&self) -> &str;
    fn compute(&self, returns: &[f64], confidence_level: f64) -> f64;
}
