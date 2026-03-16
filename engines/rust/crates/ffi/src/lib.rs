//! PyO3 FFI bindings — expose Rust engines to Python.
//!
//! This crate is compiled as a Python extension module (.so/.dylib/.pyd)
//! that the orchestrator service can import directly via `import stratos_engines`.

use pyo3::prelude::*;
use pyo3::types::PyDict;

use stratos_core::math;
use stratos_core::traits::{AllocationConstraints, AllocationStrategy, RiskMeasure};
use stratos_portfolio::{EqualWeightAllocator, MeanVarianceOptimizer, RiskParityAllocator};
use stratos_risk::{ConditionalVaR, HistoricalVaR, ParametricVaR, VolatilityMeasure};
use stratos_dcf::{DcfEngine, DcfInputs, WaccInputs};
use stratos_monte_carlo::MonteCarloEngine;
use stratos_monte_carlo::sampler::{GbmSampler, MeanRevertingSampler};
use stratos_fiscal::FiscalEngine;
use stratos_graph::{GraphEngine, GraphNode, GraphEdge, NodeType, EdgeType};
use stratos_core::types::SovereignProfile;

/// Portfolio allocation using specified strategy.
#[pyfunction]
#[pyo3(signature = (expected_returns, covariance, strategy, min_weight=0.0, max_weight=1.0, current_weights=None, transaction_cost=0.0, slippage_coeff=0.0, slippage_exponent=1.5, cost_regime_multiplier=1.0, liquidity_limit=None))]
fn allocate_portfolio(
    expected_returns: Vec<f64>,
    covariance: Vec<Vec<f64>>,
    strategy: &str,
    min_weight: f64,
    max_weight: f64,
    current_weights: Option<Vec<f64>>,
    transaction_cost: f64,
    slippage_coeff: f64,
    slippage_exponent: f64,
    cost_regime_multiplier: f64,
    liquidity_limit: Option<Vec<f64>>,
) -> PyResult<Vec<f64>> {
    let constraints = AllocationConstraints {
        min_weight,
        max_weight,
        target_return: None,
        max_risk: None,
        current_weights,
        transaction_cost,
        slippage_coeff,
        slippage_exponent,
        cost_regime_multiplier,
        liquidity_limit,
    };

    let result = match strategy {
        "equal_weight" => EqualWeightAllocator
            .allocate(&expected_returns, &covariance, &constraints),
        "mean_variance" => MeanVarianceOptimizer::default()
            .allocate(&expected_returns, &covariance, &constraints),
        "risk_parity" => RiskParityAllocator
            .allocate(&expected_returns, &covariance, &constraints),
        _ => return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Unknown strategy: {}", strategy),
        )),
    };

    result.map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
}

/// Compute VaR at given confidence level.
#[pyfunction]
fn compute_var(returns: Vec<f64>, confidence_level: f64, method: &str) -> PyResult<f64> {
    let result = match method {
        "historical" => HistoricalVaR.compute(&returns, confidence_level),
        "parametric" => ParametricVaR.compute(&returns, confidence_level),
        "cvar" => ConditionalVaR.compute(&returns, confidence_level),
        _ => return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Unknown method: {}", method),
        )),
    };
    Ok(result)
}

/// Compute annualized volatility.
#[pyfunction]
fn compute_volatility(returns: Vec<f64>, trading_days: f64) -> f64 {
    VolatilityMeasure { trading_days }.compute(&returns, 0.95)
}

/// Run Monte Carlo simulation.
#[pyfunction]
fn run_monte_carlo(
    initial_value: f64,
    drift: f64,
    volatility: f64,
    num_paths: usize,
    horizon: usize,
    model: &str,
) -> PyResult<(f64, f64, Vec<f64>)> {
    match model {
        "gbm" => {
            let sampler = GbmSampler::new(drift, volatility, 1.0 / 252.0);
            let engine = MonteCarloEngine::new(sampler);
            let result = engine
                .run(initial_value, num_paths, horizon)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
            Ok((
                result.mean_terminal,
                result.prob_loss,
                vec![
                    result.percentiles.p5,
                    result.percentiles.p25,
                    result.percentiles.p50,
                    result.percentiles.p75,
                    result.percentiles.p95,
                ],
            ))
        }
        "mean_reverting" => {
            let sampler = MeanRevertingSampler::new(initial_value, drift, volatility);
            let engine = MonteCarloEngine::new(sampler);
            let result = engine
                .run(initial_value, num_paths, horizon)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
            Ok((
                result.mean_terminal,
                result.prob_loss,
                vec![
                    result.percentiles.p5,
                    result.percentiles.p25,
                    result.percentiles.p50,
                    result.percentiles.p75,
                    result.percentiles.p95,
                ],
            ))
        }
        _ => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Unknown model: {}", model),
        )),
    }
}

/// DCF valuation.
#[pyfunction]
fn compute_dcf(
    free_cash_flows: Vec<f64>,
    terminal_growth_rate: f64,
    discount_rate: f64,
    shares_outstanding: f64,
    net_debt: f64,
) -> PyResult<(f64, f64, f64)> {
    let engine = DcfEngine;
    let inputs = DcfInputs {
        free_cash_flows,
        terminal_growth_rate,
        discount_rate,
        shares_outstanding,
        net_debt,
    };
    let result = engine
        .value(&inputs)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
    Ok((result.intrinsic_price, result.enterprise_value, result.equity_value))
}

/// WACC computation.
#[pyfunction]
fn compute_wacc(
    equity_market_cap: f64,
    total_debt: f64,
    cost_of_equity: f64,
    cost_of_debt: f64,
    tax_rate: f64,
) -> f64 {
    DcfEngine::wacc(&WaccInputs {
        equity_market_cap,
        total_debt,
        cost_of_equity,
        cost_of_debt,
        tax_rate,
    })
}

/// Fiscal sustainability analysis.
#[pyfunction]
fn analyze_fiscal(
    country_code: &str,
    debt_gdp: f64,
    fx_reserves: f64,
    fiscal_deficit: f64,
    political_stability: f64,
    currency_volatility: f64,
) -> PyResult<(f64, String)> {
    let engine = FiscalEngine;
    let profile = SovereignProfile {
        country_code: country_code.to_string(),
        debt_gdp,
        fx_reserves,
        fiscal_deficit,
        political_stability,
        currency_volatility,
    };
    let result = engine
        .analyze(&profile)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
    Ok((result.total_score, format!("{:?}", result.risk_tier)))
}

/// Math utilities.
#[pyfunction]
fn compute_covariance_matrix(return_series: Vec<Vec<f64>>) -> Vec<Vec<f64>> {
    math::covariance_matrix(&return_series)
}

/// Simulate a shock propagating through the economic graph (Subsystem B).
#[pyfunction]
#[pyo3(signature = (nodes, edges, source_id, initial_impact, decay_factor=0.8, max_depth=3))]
fn simulate_shock(
    nodes: Vec<PyObject>, // List of dicts: id, label, type, weight
    edges: Vec<PyObject>, // List of dicts: from, to, weight, type, uncertainty
    source_id: &str,
    initial_impact: f64,
    decay_factor: f64,
    max_depth: usize,
    py: Python<'_>,
) -> PyResult<PyObject> {
    let mut engine = GraphEngine::new();

    // 1. Add Nodes
    for node_obj in nodes {
        let dict = node_obj.downcast_bound::<PyDict>(py)?;
        let id: String = dict.get_item("id")?.unwrap().extract()?;
        let label: String = dict.get_item("label")?.unwrap().extract()?;
        let n_type_str: String = dict.get_item("type")?.unwrap().extract()?;
        let weight: f64 = dict.get_item("weight")?.unwrap().extract()?;

        let node_type = match n_type_str.to_lowercase().as_str() {
            "country" => NodeType::Country,
            "industry" => NodeType::Industry,
            "company" => NodeType::Company,
            "commodity" => NodeType::Commodity,
            "currency" => NodeType::Currency,
            "asset_class" => NodeType::AssetClass,
            _ => NodeType::Country,
        };

        engine.add_node(GraphNode { id, label, node_type, weight });
    }

    // 2. Add Edges
    for edge_obj in edges {
        let dict = edge_obj.downcast_bound::<PyDict>(py)?;
        let from: String = dict.get_item("from")?.unwrap().extract()?;
        let to: String = dict.get_item("to")?.unwrap().extract()?;
        let weight: f64 = dict.get_item("weight")?.unwrap().extract()?;
        let e_type_str: String = dict.get_item("type")?.unwrap().extract()?;
        let uncertainty: f64 = dict.get_item("uncertainty")?.unwrap().extract()?;

        let edge_type = match e_type_str.to_lowercase().as_str() {
            "tradeflow" => EdgeType::TradeFlow,
            "supplychain" => EdgeType::SupplyChain,
            "fxpeg" => EdgeType::FxPeg,
            "creditlink" => EdgeType::CreditLink,
            _ => EdgeType::Dependency,
        };

        engine.add_edge(GraphEdge { from, to, weight, edge_type, uncertainty });
    }

    // 3. Propagate
    let result = engine.propagate_shock(source_id, initial_impact, decay_factor, max_depth)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

    // 4. Convert Result to PyDict
    let py_result = PyDict::new(py);
    let impacts_dict = PyDict::new(py);
    
    for (node, band) in result.impacts {
        let band_dict = PyDict::new(py);
        band_dict.set_item("base", band.base)?;
        band_dict.set_item("min", band.min)?;
        band_dict.set_item("max", band.max)?;
        impacts_dict.set_item(node, band_dict)?;
    }
    
    py_result.set_item("impacts", impacts_dict)?;
    py_result.set_item("total_affected", result.total_affected)?;
    py_result.set_item("max_depth", result.max_depth_reached)?;

    Ok(py_result.to_object(py))
}

/// Python module definition.
#[pymodule]
fn stratos_engines(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(allocate_portfolio, m)?)?;
    m.add_function(wrap_pyfunction!(compute_var, m)?)?;
    m.add_function(wrap_pyfunction!(compute_volatility, m)?)?;
    m.add_function(wrap_pyfunction!(run_monte_carlo, m)?)?;
    m.add_function(wrap_pyfunction!(compute_dcf, m)?)?;
    m.add_function(wrap_pyfunction!(compute_wacc, m)?)?;
    m.add_function(wrap_pyfunction!(analyze_fiscal, m)?)?;
    m.add_function(wrap_pyfunction!(compute_covariance_matrix, m)?)?;
    m.add_function(wrap_pyfunction!(simulate_shock, m)?)?;
    Ok(())
}
