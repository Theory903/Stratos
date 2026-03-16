//! Graph propagation engine — supply chain, trade network, contagion modeling.
//!
//! Implements a weighted directed graph for modeling economic relationships
//! and propagating shocks (sanctions, supply disruptions, contagion).

use std::collections::HashMap;
use serde::{Deserialize, Serialize};
use stratos_core::error::EngineError;
use stratos_core::traits::Engine;

/// A node in the economic graph.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GraphNode {
    pub id: String,
    pub label: String,
    pub node_type: NodeType,
    pub weight: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum NodeType {
    Country,
    Industry,
    Company,
    Commodity,
    Currency,
    AssetClass,
}

/// A weighted directed edge.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GraphEdge {
    pub from: String,
    pub to: String,
    pub weight: f64,
    pub edge_type: EdgeType,
    /// Variance or uncertainty of this relationship (0.0=certain, 1.0=speculative)
    pub uncertainty: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum EdgeType {
    TradeFlow,
    SupplyChain,
    Investment,
    Dependency,
    FxPeg,
    CreditLink,
}

/// Impact Band for a node (Subsystem B).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImpactBand {
    pub base: f64,
    pub min: f64,
    pub max: f64,
}

/// Shock propagation result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PropagationResult {
    pub impacts: HashMap<String, ImpactBand>,
    pub total_affected: usize,
    pub max_depth_reached: usize,
}

/// Graph propagation engine.
pub struct GraphEngine {
    nodes: HashMap<String, GraphNode>,
    adjacency: HashMap<String, Vec<GraphEdge>>,
}

impl Engine for GraphEngine {
    fn name(&self) -> &str {
        "GraphPropagation"
    }
}

impl GraphEngine {
    pub fn new() -> Self {
        Self {
            nodes: HashMap::new(),
            adjacency: HashMap::new(),
        }
    }

    pub fn add_node(&mut self, node: GraphNode) {
        let id = node.id.clone();
        self.nodes.insert(id.clone(), node);
        self.adjacency.entry(id).or_default();
    }

    pub fn add_edge(&mut self, edge: GraphEdge) {
        self.adjacency
            .entry(edge.from.clone())
            .or_default()
            .push(edge);
    }

    /// Propagate a shock from a source node through the graph.
    ///
    /// Uses BFS with decay and uncertainty propagation (Subsystem B.2).
    pub fn propagate_shock(
        &self,
        source: &str,
        initial_impact: f64,
        decay_factor: f64,
        max_depth: usize,
    ) -> Result<PropagationResult, EngineError> {
        if !self.nodes.contains_key(source) {
            return Err(EngineError::InvalidInput(format!(
                "Source node '{}' not found in graph", source
            )));
        }

        let mut impacts: HashMap<String, ImpactBand> = HashMap::new();
        let initial_band = ImpactBand {
            base: initial_impact,
            min: initial_impact,
            max: initial_impact,
        };
        impacts.insert(source.to_string(), initial_band.clone());

        let mut queue = vec![(source.to_string(), initial_band, 0usize)];
        let mut max_depth_reached = 0;

        while let Some((node_id, band, depth)) = queue.pop() {
            if depth >= max_depth {
                continue;
            }
            max_depth_reached = max_depth_reached.max(depth);

            if let Some(edges) = self.adjacency.get(&node_id) {
                for edge in edges {
                    // Propagate base, min, max
                    let base_prop = band.base * edge.weight * decay_factor;
                    
                    // Uncertainty spreads the band
                    // max = larger absolute impact, min = smaller absolute impact
                    let spread = edge.uncertainty.abs();
                    let (min_prop, max_prop) = if base_prop >= 0.0 {
                        (base_prop * (1.0 - spread), base_prop * (1.0 + spread))
                    } else {
                        (base_prop * (1.0 + spread), base_prop * (1.0 - spread))
                    };

                    if base_prop.abs() < 0.0001 {
                        continue; 
                    }

                    let propagated_band = ImpactBand {
                        base: base_prop,
                        min: min_prop,
                        max: max_prop,
                    };

                    let entry = impacts.entry(edge.to.clone()).or_insert(ImpactBand {
                        base: 0.0,
                        min: 0.0,
                        max: 0.0,
                    });
                    
                    entry.base += propagated_band.base;
                    entry.min += propagated_band.min;
                    entry.max += propagated_band.max;
                    
                    queue.push((edge.to.clone(), propagated_band, depth + 1));
                }
            }
        }

        let total_affected = impacts.len();
        Ok(PropagationResult {
            impacts,
            total_affected,
            max_depth_reached,
        })
    }

    /// Compute centrality scores (simplified PageRank-like).
    pub fn centrality_scores(&self, iterations: usize, damping: f64) -> HashMap<String, f64> {
        let n = self.nodes.len();
        if n == 0 {
            return HashMap::new();
        }

        let mut scores: HashMap<String, f64> = self
            .nodes
            .keys()
            .map(|k| (k.clone(), 1.0 / n as f64))
            .collect();

        for _ in 0..iterations {
            let mut new_scores = HashMap::new();
            for node_id in self.nodes.keys() {
                let mut incoming_score = 0.0;
                // Find nodes pointing to this node
                for (from, edges) in &self.adjacency {
                    for edge in edges {
                        if &edge.to == node_id {
                            let out_degree = edges.len() as f64;
                            incoming_score += scores[from] * edge.weight / out_degree;
                        }
                    }
                }
                new_scores.insert(
                    node_id.clone(),
                    (1.0 - damping) / n as f64 + damping * incoming_score,
                );
            }
            scores = new_scores;
        }
        scores
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn build_test_graph() -> GraphEngine {
        let mut g = GraphEngine::new();
        g.add_node(GraphNode {
            id: "US".into(), label: "United States".into(),
            node_type: NodeType::Country, weight: 1.0,
        });
        g.add_node(GraphNode {
            id: "CN".into(), label: "China".into(),
            node_type: NodeType::Country, weight: 1.0,
        });
        g.add_node(GraphNode {
            id: "semi".into(), label: "Semiconductors".into(),
            node_type: NodeType::Industry, weight: 1.0,
        });
        g.add_edge(GraphEdge {
            from: "US".into(), to: "CN".into(),
            weight: 0.6, edge_type: EdgeType::TradeFlow,
            uncertainty: 0.0,
        });
        g.add_edge(GraphEdge {
            from: "CN".into(), to: "semi".into(),
            weight: 0.8, edge_type: EdgeType::SupplyChain,
            uncertainty: 0.0,
        });
        g
    }

    #[test]
    fn test_shock_propagation() {
        let g = build_test_graph();
        let result = g.propagate_shock("US", -10.0, 0.8, 3).unwrap();

        assert!(result.impacts.contains_key("US"));
        assert!(result.impacts.contains_key("CN"));
        assert!(result.impacts.contains_key("semi"));
        // CN impact should be US * 0.6 * 0.8 = -4.8
        assert!((result.impacts["CN"].base - (-4.8)).abs() < 0.01);
    }

    #[test]
    fn test_centrality() {
        let g = build_test_graph();
        let scores = g.centrality_scores(20, 0.85);
        assert!(!scores.is_empty());
    }

    #[test]
    fn test_invalid_source() {
        let g = build_test_graph();
        assert!(g.propagate_shock("XX", -10.0, 0.8, 3).is_err());
    }
}
