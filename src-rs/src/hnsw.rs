//! HNSW (Hierarchical Navigable Small World) vector index.
//!
//! Sub-millisecond approximate nearest neighbor search.
//! Optimized for molecular property vectors (8-64 dimensions).

use rand::seq::SliceRandom;
use rand::Rng;
use rustc_hash::FxHashMap;
use std::cmp::Ordering;

/// A single node in the HNSW graph.
#[derive(Clone, Debug)]
struct HnswNode {
    id: u64,
    vector: Vec<f32>,
    /// layer -> { neighbor_id }
    neighbors: FxHashMap<usize, Vec<u64>>,
    layer: usize,
}

/// HNSW index for approximate nearest neighbor search.
pub struct HnswIndex {
    nodes: FxHashMap<u64, HnswNode>,
    entry_point: Option<u64>,
    max_layer: usize,
    ef_construction: usize,
    m_max: usize,
    m_max0: usize,
    dim: usize,
    next_id: u64,
    ml_factor: f32,
}

impl HnswIndex {
    /// Create a new HNSW index.
    ///
    /// - `dim`: vector dimensionality
    /// - `m_max`: max connections per layer (upper layers)
    /// - `ef_construction`: search width during insertion
    pub fn new(dim: usize, m_max: usize, ef_construction: usize) -> Self {
        Self {
            nodes: FxHashMap::default(),
            entry_point: None,
            max_layer: 0,
            ef_construction,
            m_max,
            m_max0: m_max * 2,
            dim,
            next_id: 0,
            ml_factor: 1.0 / (m_max as f32).ln(),
        }
    }

    /// Default config for battery property vectors (dim=16).
    pub fn for_battery_properties() -> Self {
        Self::new(16, 16, 200)
    }

    /// Default config for molecular fingerprints (dim=128).
    pub fn for_molecular_fingerprints() -> Self {
        Self::new(128, 24, 300)
    }

    /// Insert a vector, returns its assigned ID.
    pub fn insert(&mut self, vector: Vec<f32>) -> u64 {
        assert_eq!(vector.len(), self.dim, "Vector dimension mismatch");

        let id = self.next_id;
        self.next_id += 1;

        let layer = self.random_layer();
        let mut node = HnswNode {
            id,
            vector,
            neighbors: FxHashMap::default(),
            layer,
        };

        for l in 0..=layer {
            node.neighbors.insert(l, Vec::new());
        }

        match self.entry_point {
            None => {
                self.nodes.insert(id, node);
                self.entry_point = Some(id);
                self.max_layer = layer;
                return id;
            }
            Some(ep_id) => {
                let ep_layer = self.nodes[&ep_id].layer;

                // Navigate from top to the node's layer
                let mut cur = ep_id;
                for l in (layer + 1..=ep_layer).rev() {
                    cur = self.greedy_closest(cur, &node.vector, l);
                }

                // Insert connections from layer min(cur_layer, node_layer) down to 0
                for l in (0..=layer.min(ep_layer)).rev() {
                    let candidates = self.search_layer(cur, &node.vector, self.ef_construction, l);

                    let m = if l == 0 { self.m_max0 } else { self.m_max };
                    let neighbors = self.select_neighbors(&candidates, m);

                    node.neighbors.insert(l, neighbors.clone());

                    for &neighbor_id in &neighbors {
                        if let Some(neighbor) = self.nodes.get_mut(&neighbor_id) {
                            if let Some(nbrs) = neighbor.neighbors.get_mut(&l) {
                                nbrs.push(id);
                                let m_limit = if l == 0 { self.m_max0 } else { self.m_max };
                                if nbrs.len() > m_limit {
                                    self.prune_connections(neighbor_id, l, m_limit);
                                }
                            }
                        }
                    }

                    if !candidates.is_empty() {
                        cur = candidates[0].1;
                    }
                }

                self.nodes.insert(id, node);

                if layer > self.max_layer {
                    self.max_layer = layer;
                    self.entry_point = Some(id);
                }
            }
        }

        id
    }

    /// Search for k nearest neighbors.
    pub fn search(&self, query: &[f32], k: usize, ef: usize) -> Vec<(f32, u64)> {
        if self.entry_point.is_none() || self.nodes.is_empty() {
            return Vec::new();
        }

        let ep = self.entry_point.unwrap();
        let mut cur = ep;

        // Greedy descent from top layer to layer 1
        for l in (1..=self.max_layer).rev() {
            cur = self.greedy_closest(cur, query, l);
        }

        // Search at layer 0
        let candidates = self.search_layer(cur, query, ef.max(k), 0);

        candidates.into_iter().take(k).collect()
    }

    /// Get vector by ID.
    pub fn get(&self, id: u64) -> Option<&[f32]> {
        self.nodes.get(&id).map(|n| n.vector.as_slice())
    }

    /// Number of indexed vectors.
    pub fn len(&self) -> usize {
        self.nodes.len()
    }

    pub fn is_empty(&self) -> bool {
        self.nodes.is_empty()
    }

    // -- Internal methods --

    fn random_layer(&self) -> usize {
        let mut rng = rand::thread_rng();
        let r: f32 = rng.gen();
        (-r.log(std::f32::consts::E) * self.ml_factor) as usize
    }

    fn distance(a: &[f32], b: &[f32]) -> f32 {
        a.iter()
            .zip(b.iter())
            .map(|(x, y)| (x - y).powi(2))
            .sum::<f32>()
            .sqrt()
    }

    fn greedy_closest(&self, start: u64, query: &[f32], layer: usize) -> u64 {
        let mut best = start;
        let mut best_dist = Self::distance(query, &self.nodes[&start].vector);

        loop {
            let mut changed = false;
            if let Some(node) = self.nodes.get(&best) {
                if let Some(neighbors) = node.neighbors.get(&layer) {
                    for &n_id in neighbors {
                        if let Some(n) = self.nodes.get(&n_id) {
                            let d = Self::distance(query, &n.vector);
                            if d < best_dist {
                                best_dist = d;
                                best = n_id;
                                changed = true;
                            }
                        }
                    }
                }
            }
            if !changed {
                break;
            }
        }

        best
    }

    fn search_layer(
        &self,
        entry: u64,
        query: &[f32],
        ef: usize,
        layer: usize,
    ) -> Vec<(f32, u64)> {
        let entry_dist = Self::distance(query, &self.nodes[&entry].vector);

        let mut candidates: Vec<(f32, u64)> = vec![(entry_dist, entry)];
        let mut visited: std::collections::HashSet<u64> = std::collections::HashSet::new();
        visited.insert(entry);

        let mut results: Vec<(f32, u64)> = vec![(entry_dist, entry)];

        while !candidates.is_empty() {
            candidates.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(Ordering::Equal));
            let (_, closest) = candidates.remove(0);

            let farthest = results.last().map(|(d, _)| *d).unwrap_or(f32::MAX);

            if let Some(node) = self.nodes.get(&closest) {
                if let Some(neighbors) = node.neighbors.get(&layer) {
                    for &n_id in neighbors {
                        if visited.insert(n_id) {
                            if let Some(n) = self.nodes.get(&n_id) {
                                let d = Self::distance(query, &n.vector);
                                let farthest_d = results.last().map(|(d, _)| *d).unwrap_or(f32::MAX);

                                if d < farthest_d || results.len() < ef {
                                    candidates.push((d, n_id));
                                    results.push((d, n_id));
                                    results.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(Ordering::Equal));
                                    if results.len() > ef {
                                        results.pop();
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        results
    }

    fn select_neighbors(&self, candidates: &[(f32, u64)], m: usize) -> Vec<u64> {
        let mut sorted = candidates.to_vec();
        sorted.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(Ordering::Equal));
        sorted.iter().take(m).map(|(_, id)| *id).collect()
    }

    fn prune_connections(&mut self, node_id: u64, layer: usize, m: usize) {
        if let Some(node) = self.nodes.get(&node_id) {
            let query = node.vector.clone();
            let neighbor_ids: Vec<u64> = node.neighbors.get(&layer).cloned().unwrap_or_default();

            let mut scored: Vec<(f32, u64)> = neighbor_ids
                .iter()
                .filter_map(|&n_id| {
                    self.nodes.get(&n_id).map(|n| {
                        (Self::distance(&query, &n.vector), n_id)
                    })
                })
                .collect();

            scored.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(Ordering::Equal));
            let pruned: Vec<u64> = scored.into_iter().take(m).map(|(_, id)| id).collect();

            if let Some(node) = self.nodes.get_mut(&node_id) {
                node.neighbors.insert(layer, pruned);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_insert_and_search() {
        let mut index = HnswIndex::new(4, 4, 50);

        // Insert some vectors
        index.insert(vec![1.0, 0.0, 0.0, 0.0]);
        index.insert(vec![0.0, 1.0, 0.0, 0.0]);
        index.insert(vec![0.9, 0.1, 0.0, 0.0]);
        index.insert(vec![0.0, 0.0, 1.0, 0.0]);
        index.insert(vec![0.95, 0.05, 0.0, 0.0]);

        let results = index.search(&[1.0, 0.0, 0.0, 0.0], 2, 50);
        assert!(results.len() >= 2);
        assert!(results[0].0 < 0.01); // first result should be very close
    }

    #[test]
    fn test_battery_property_vectors() {
        let mut index = HnswIndex::for_battery_properties();

        // Simulate battery property vectors:
        // [voltage, energy_density, homo, lumo, gap, lambda, thermal, flame, cycle, ...]
        for i in 0..100 {
            let v = (i as f32) * 0.1;
            index.insert(vec![
                3.0 + v * 0.1,    // voltage
                250.0 + v * 10.0, // energy_density
                -4.5 + v * 0.05,  // homo
                -1.5 + v * 0.02,  // lumo
                3.0 + v * 0.03,   // gap
                0.2 + v * 0.01,   // lambda
                200.0 + v * 5.0,  // thermal
                0.5 + v * 0.005,  // flame
                0.6 + v * 0.004,  // cycle
                v * 0.1,          // pad
                v * 0.1,
                v * 0.1,
                v * 0.1,
                v * 0.1,
                v * 0.1,
                v * 0.1,
            ]);
        }

        let query = vec![3.5, 300.0, -4.3, -1.4, 3.15, 0.25, 225.0, 0.525, 0.62,
                         0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5];
        let results = index.search(&query, 5, 50);
        assert_eq!(results.len(), 5);
    }
}
