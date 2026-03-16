//! Mathematical utilities for financial computations.
//!
//! Pure functions — no state, no side effects. Used across all engine crates.

/// Compute mean of a slice.
pub fn mean(data: &[f64]) -> f64 {
    if data.is_empty() {
        return 0.0;
    }
    data.iter().sum::<f64>() / data.len() as f64
}

/// Compute sample standard deviation.
pub fn std_dev(data: &[f64]) -> f64 {
    if data.len() < 2 {
        return 0.0;
    }
    let m = mean(data);
    let variance = data.iter().map(|x| (x - m).powi(2)).sum::<f64>() / (data.len() - 1) as f64;
    variance.sqrt()
}

/// Compute log returns from price series.
pub fn log_returns(prices: &[f64]) -> Vec<f64> {
    prices
        .windows(2)
        .map(|w| (w[1] / w[0]).ln())
        .collect()
}

/// Compute simple returns from price series.
pub fn simple_returns(prices: &[f64]) -> Vec<f64> {
    prices
        .windows(2)
        .map(|w| (w[1] - w[0]) / w[0])
        .collect()
}

/// Compute covariance matrix from a matrix of return series.
/// Each inner Vec is a time series of returns for one asset.
pub fn covariance_matrix(return_series: &[Vec<f64>]) -> Vec<Vec<f64>> {
    let n = return_series.len();
    let mut cov = vec![vec![0.0; n]; n];

    for i in 0..n {
        let mean_i = mean(&return_series[i]);
        for j in i..n {
            let mean_j = mean(&return_series[j]);
            let len = return_series[i].len().min(return_series[j].len());
            if len < 2 {
                continue;
            }
            let cov_ij: f64 = (0..len)
                .map(|k| (return_series[i][k] - mean_i) * (return_series[j][k] - mean_j))
                .sum::<f64>()
                / (len - 1) as f64;
            cov[i][j] = cov_ij;
            cov[j][i] = cov_ij;
        }
    }
    cov
}

/// Compute portfolio variance given weights and covariance matrix.
pub fn portfolio_variance(weights: &[f64], cov: &[Vec<f64>]) -> f64 {
    let n = weights.len();
    let mut var = 0.0;
    for i in 0..n {
        for j in 0..n {
            var += weights[i] * weights[j] * cov[i][j];
        }
    }
    var
}

/// Compute portfolio expected return given weights and expected returns.
pub fn portfolio_return(weights: &[f64], returns: &[f64]) -> f64 {
    weights.iter().zip(returns).map(|(w, r)| w * r).sum()
}

/// Sharpe ratio: (return - risk_free) / volatility
pub fn sharpe_ratio(port_return: f64, risk_free: f64, volatility: f64) -> f64 {
    if volatility <= 0.0 {
        return 0.0;
    }
    (port_return - risk_free) / volatility
}

/// Maximum drawdown from a return series.
pub fn max_drawdown(returns: &[f64]) -> f64 {
    let mut peak = 1.0;
    let mut max_dd = 0.0;
    let mut value = 1.0;

    for &r in returns {
        value *= 1.0 + r;
        if value > peak {
            peak = value;
        }
        let dd = (peak - value) / peak;
        if dd > max_dd {
            max_dd = dd;
        }
    }
    max_dd
}

/// Annualized return from daily returns.
pub fn annualized_return(daily_returns: &[f64], trading_days: f64) -> f64 {
    let total: f64 = daily_returns.iter().map(|r| (1.0 + r).ln()).sum();
    (total / daily_returns.len() as f64 * trading_days).exp() - 1.0
}

/// Annualized volatility from daily returns.
pub fn annualized_volatility(daily_returns: &[f64], trading_days: f64) -> f64 {
    std_dev(daily_returns) * trading_days.sqrt()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mean() {
        assert!((mean(&[1.0, 2.0, 3.0]) - 2.0).abs() < 1e-10);
    }

    #[test]
    fn test_mean_empty() {
        assert_eq!(mean(&[]), 0.0);
    }

    #[test]
    fn test_std_dev() {
        let data = vec![2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0];
        let sd = std_dev(&data);
        assert!((sd - 2.138).abs() < 0.01);
    }

    #[test]
    fn test_log_returns() {
        let prices = vec![100.0, 110.0, 105.0];
        let returns = log_returns(&prices);
        assert_eq!(returns.len(), 2);
        assert!((returns[0] - 0.09531).abs() < 0.001);
    }

    #[test]
    fn test_simple_returns() {
        let prices = vec![100.0, 110.0, 105.0];
        let returns = simple_returns(&prices);
        assert!((returns[0] - 0.1).abs() < 1e-10);
    }

    #[test]
    fn test_covariance_matrix() {
        let a = vec![0.1, 0.2, 0.15];
        let b = vec![0.05, 0.1, 0.08];
        let cov = covariance_matrix(&[a, b]);
        assert_eq!(cov.len(), 2);
        assert!(cov[0][0] > 0.0); // variance must be positive
        assert!((cov[0][1] - cov[1][0]).abs() < 1e-15); // symmetric
    }

    #[test]
    fn test_portfolio_variance() {
        let w = vec![0.5, 0.5];
        let cov = vec![vec![0.04, 0.006], vec![0.006, 0.09]];
        let var = portfolio_variance(&w, &cov);
        assert!((var - 0.0355).abs() < 0.001);
    }

    #[test]
    fn test_sharpe_ratio() {
        assert!((sharpe_ratio(0.12, 0.02, 0.15) - 0.6667).abs() < 0.01);
    }

    #[test]
    fn test_max_drawdown() {
        let returns = vec![0.1, -0.05, -0.1, 0.15, -0.2];
        let dd = max_drawdown(&returns);
        assert!(dd > 0.0 && dd < 1.0);
    }
}
