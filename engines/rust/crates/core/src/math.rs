//! Mathematical utilities for financial computations.

/// Compute mean of a slice of f64.
pub fn mean(data: &[f64]) -> f64 {
    if data.is_empty() { return 0.0; }
    data.iter().sum::<f64>() / data.len() as f64
}

/// Compute standard deviation (population).
pub fn std_dev(data: &[f64]) -> f64 {
    let m = mean(data);
    let variance = data.iter().map(|x| (x - m).powi(2)).sum::<f64>() / data.len() as f64;
    variance.sqrt()
}

/// Compute log returns from price series.
pub fn log_returns(prices: &[f64]) -> Vec<f64> {
    prices.windows(2).map(|w| (w[1] / w[0]).ln()).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mean() {
        assert!((mean(&[1.0, 2.0, 3.0]) - 2.0).abs() < 1e-10);
    }

    #[test]
    fn test_log_returns() {
        let prices = vec![100.0, 110.0, 105.0];
        let returns = log_returns(&prices);
        assert_eq!(returns.len(), 2);
    }
}
