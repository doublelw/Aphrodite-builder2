//! SONA — Self-Optimizing Neural Adaptation layer.
//!
//! Captures successful execution patterns, builds a ReasoningBank,
//! and automatically routes similar tasks to proven patterns.
//!
//! Inspired by Ruflo's SONA: "the more you use it, the smarter it gets."

use crate::memory::{MemoryStore, MemoryType};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// A captured execution pattern.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Pattern {
    pub id: u64,
    pub name: String,
    pub task_signature: Vec<f32>,
    pub steps: Vec<PatternStep>,
    pub success_rate: f32,
    pub execution_count: u32,
    pub last_outcome: bool,
}

/// A single step in a captured pattern.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PatternStep {
    pub action: String,
    pub tool: String,
    pub params: serde_json::Value,
    pub expected_duration_secs: f32,
}

/// Task routing recommendation.
#[derive(Debug)]
pub struct RoutingDecision {
    pub pattern_id: Option<u64>,
    pub pattern_name: String,
    pub confidence: f32,
    pub estimated_steps: Vec<PatternStep>,
}

/// SONA self-optimization engine.
pub struct SonaEngine {
    patterns: HashMap<u64, Pattern>,
    next_pattern_id: u64,
    /// Minimum confidence to auto-apply a pattern
    confidence_threshold: f32,
    /// Decay factor for old patterns
    decay_factor: f32,
}

impl SonaEngine {
    pub fn new() -> Self {
        Self {
            patterns: HashMap::new(),
            next_pattern_id: 0,
            confidence_threshold: 0.7,
            decay_factor: 0.95,
        }
    }

    /// Capture a successful execution as a reusable pattern.
    pub fn capture_pattern(
        &mut self,
        name: &str,
        task_signature: Vec<f32>,
        steps: Vec<PatternStep>,
    ) -> u64 {
        let id = self.next_pattern_id;
        self.next_pattern_id += 1;

        let pattern = Pattern {
            id,
            name: name.to_string(),
            task_signature,
            steps,
            success_rate: 1.0,
            execution_count: 1,
            last_outcome: true,
        };

        self.patterns.insert(id, pattern);
        id
    }

    /// Record the outcome of a pattern execution.
    pub fn record_outcome(&mut self, pattern_id: u64, success: bool) {
        if let Some(pattern) = self.patterns.get_mut(&pattern_id) {
            pattern.execution_count += 1;
            pattern.last_outcome = success;

            // Update success rate with exponential moving average
            let alpha = 0.3;
            if success {
                pattern.success_rate = alpha * 1.0 + (1.0 - alpha) * pattern.success_rate;
            } else {
                pattern.success_rate = alpha * 0.0 + (1.0 - alpha) * pattern.success_rate;
            }
        }
    }

    /// Route a new task to the best matching pattern.
    pub fn route(&self, task_vector: &[f32]) -> RoutingDecision {
        let mut best_pattern: Option<&Pattern> = None;
        let mut best_distance = f32::MAX;

        for pattern in self.patterns.values() {
            let dist = cosine_distance(task_vector, &pattern.task_signature);
            if dist < best_distance {
                best_distance = dist;
                best_pattern = Some(pattern);
            }
        }

        match best_pattern {
            Some(pattern) => {
                let confidence = (1.0 - best_distance) * pattern.success_rate;
                RoutingDecision {
                    pattern_id: Some(pattern.id),
                    pattern_name: pattern.name.clone(),
                    confidence,
                    estimated_steps: pattern.steps.clone(),
                }
            }
            None => RoutingDecision {
                pattern_id: None,
                pattern_name: "no_match".to_string(),
                confidence: 0.0,
                estimated_steps: vec![],
            },
        }
    }

    /// Get the confidence threshold for auto-application.
    pub fn should_auto_apply(&self, decision: &RoutingDecision) -> bool {
        decision.confidence >= self.confidence_threshold
            && decision.pattern_id.is_some()
    }

    /// Decay old pattern confidence (call periodically).
    pub fn decay(&mut self) {
        for pattern in self.patterns.values_mut() {
            pattern.success_rate *= self.decay_factor;
        }
    }

    /// Get all patterns sorted by success rate.
    pub fn top_patterns(&self, n: usize) -> Vec<&Pattern> {
        let mut patterns: Vec<&Pattern> = self.patterns.values().collect();
        patterns.sort_by(|a, b| {
            b.success_rate
                .partial_cmp(&a.success_rate)
                .unwrap_or(std::cmp::Ordering::Equal)
        });
        patterns.into_iter().take(n).collect()
    }

    /// Store patterns into a MemoryStore for persistence.
    pub fn persist(&self, store: &mut MemoryStore) {
        for pattern in self.patterns.values() {
            let data = serde_json::to_value(pattern).unwrap_or(serde_json::Value::Null);
            let key = format!("sona_pattern_{}", pattern.id);
            let tags = vec!["sona".to_string(), "pattern".to_string()];

            // Check if already stored
            let existing = store.recall_by_key(&key);
            if existing.is_empty() {
                store.store(
                    MemoryType::Pattern,
                    &key,
                    pattern.task_signature.clone(),
                    data,
                    tags,
                );
            }
        }
    }

    /// Number of captured patterns.
    pub fn len(&self) -> usize {
        self.patterns.len()
    }

    pub fn is_empty(&self) -> bool {
        self.patterns.is_empty()
    }
}

/// Cosine distance between two vectors.
fn cosine_distance(a: &[f32], b: &[f32]) -> f32 {
    let min_len = a.len().min(b.len());
    let mut dot = 0.0f32;
    let mut norm_a = 0.0f32;
    let mut norm_b = 0.0f32;

    for i in 0..min_len {
        dot += a[i] * b[i];
        norm_a += a[i] * a[i];
        norm_b += b[i] * b[i];
    }

    let denom = norm_a.sqrt() * norm_b.sqrt();
    if denom < 1e-10 {
        return 1.0;
    }

    1.0 - dot / denom
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pattern_capture_and_route() {
        let mut sona = SonaEngine::new();

        sona.capture_pattern(
            "high_voltage_screening",
            vec![1.0, 0.8, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            vec![
                PatternStep {
                    action: "generate_candidates".into(),
                    tool: "rdkit".into(),
                    params: serde_json::json!({"n": 50}),
                    expected_duration_secs: 10.0,
                },
                PatternStep {
                    action: "dft_screening".into(),
                    tool: "orca".into(),
                    params: serde_json::json!({"method": "r2SCAN-3c"}),
                    expected_duration_secs: 3600.0,
                },
            ],
        );

        let decision = sona.route(&[0.9, 0.75, 0.0, 0.4, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]);
        assert!(decision.pattern_id.is_some());
        assert!(decision.confidence > 0.5);
        assert_eq!(decision.estimated_steps.len(), 2);
    }

    #[test]
    fn test_outcome_updates_success_rate() {
        let mut sona = SonaEngine::new();
        let pid = sona.capture_pattern("test", vec![1.0, 0.0], vec![]);

        sona.record_outcome(pid, true);
        assert!(sona.patterns[&pid].success_rate > 0.9);

        sona.record_outcome(pid, false);
        sona.record_outcome(pid, false);
        assert!(sona.patterns[&pid].success_rate < 0.7);
    }
}
