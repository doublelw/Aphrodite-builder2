//! Persistent memory store for cross-session knowledge.
//!
//! Stores molecular design patterns, calculation results,
//! screening outcomes, and workflow trajectories.
//! Backed by JSON files for portability.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

/// Type of memory entry.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum MemoryType {
    /// Molecular candidate with predicted properties
    Molecule,
    /// Successful calculation path (input→output)
    CalculationPath,
    /// Screening result and ranking
    ScreeningResult,
    /// Workflow execution trace
    WorkflowTrace,
    /// User preference or project context
    Context,
    /// SONA-captured successful pattern
    Pattern,
}

/// A single memory entry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryEntry {
    pub id: u64,
    pub entry_type: MemoryType,
    pub key: String,
    pub vector: Vec<f32>,
    pub data: serde_json::Value,
    pub tags: Vec<String>,
    pub created_at: u64,
    pub access_count: u32,
    pub last_accessed: u64,
    pub confidence: f32,
}

/// Persistent memory store with vector index.
pub struct MemoryStore {
    entries: HashMap<u64, MemoryEntry>,
    index: crate::hnsw::HnswIndex,
    path: PathBuf,
    next_id: u64,
}

impl MemoryStore {
    /// Open or create a memory store at the given directory.
    pub fn open(path: &str) -> Self {
        let dir = PathBuf::from(path);
        fs::create_dir_all(&dir).ok();

        let mut store = Self {
            entries: HashMap::new(),
            index: crate::hnsw::HnswIndex::for_battery_properties(),
            path: dir,
            next_id: 0,
        };

        store.load_from_disk();
        store
    }

    /// Store a new memory entry.
    pub fn store(
        &mut self,
        entry_type: MemoryType,
        key: &str,
        vector: Vec<f32>,
        data: serde_json::Value,
        tags: Vec<String>,
    ) -> u64 {
        let id = self.next_id;
        self.next_id += 1;

        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs())
            .unwrap_or(0);

        let entry = MemoryEntry {
            id,
            entry_type,
            key: key.to_string(),
            vector: vector.clone(),
            data,
            tags,
            created_at: now,
            access_count: 0,
            last_accessed: now,
            confidence: 1.0,
        };

        self.index.insert(vector);
        self.entries.insert(id, entry);
        self.flush();

        id
    }

    /// Recall memories similar to the given vector.
    pub fn recall(&mut self, query: &[f32], k: usize) -> Vec<(f32, u64)> {
        let results = self.index.search(query, k, 100);

        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs())
            .unwrap_or(0);

        for (dist, id) in &results {
            if let Some(entry) = self.entries.get_mut(id) {
                entry.access_count += 1;
                entry.last_accessed = now;
            }
        }

        results
    }

    /// Recall memories by key prefix.
    pub fn recall_by_key(&self, prefix: &str) -> Vec<&MemoryEntry> {
        self.entries
            .values()
            .filter(|e| e.key.starts_with(prefix))
            .collect()
    }

    /// Recall memories by tag.
    pub fn recall_by_tag(&self, tag: &str) -> Vec<&MemoryEntry> {
        self.entries
            .values()
            .filter(|e| e.tags.contains(&tag.to_string()))
            .collect()
    }

    /// Recall memories by type.
    pub fn recall_by_type(&self, entry_type: &MemoryType) -> Vec<&MemoryEntry> {
        self.entries
            .values()
            .filter(|e| &e.entry_type == entry_type)
            .collect()
    }

    /// Get entry by ID.
    pub fn get(&self, id: u64) -> Option<&MemoryEntry> {
        self.entries.get(&id)
    }

    /// Update an entry's confidence score (used by SONA).
    pub fn update_confidence(&mut self, id: u64, confidence: f32) {
        if let Some(entry) = self.entries.get_mut(&id) {
            entry.confidence = confidence;
        }
    }

    /// Number of stored memories.
    pub fn len(&self) -> usize {
        self.entries.len()
    }

    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    /// Flush all entries to disk.
    pub fn flush(&self) {
        let data_path = self.path.join("memory_store.json");
        let entries: Vec<&MemoryEntry> = self.entries.values().collect();
        if let Ok(json) = serde_json::to_string_pretty(&entries) {
            fs::write(data_path, json).ok();
        }

        let meta_path = self.path.join("meta.json");
        let meta = serde_json::json!({
            "next_id": self.next_id,
            "count": self.entries.len(),
        });
        if let Ok(json) = serde_json::to_string_pretty(&meta) {
            fs::write(meta_path, json).ok();
        }
    }

    fn load_from_disk(&mut self) {
        let data_path = self.path.join("memory_store.json");
        if data_path.exists() {
            if let Ok(content) = fs::read_to_string(&data_path) {
                if let Ok(entries) = serde_json::from_str::<Vec<MemoryEntry>>(&content) {
                    for entry in entries {
                        self.index.insert(entry.vector.clone());
                        self.entries.insert(entry.id, entry);
                    }
                }
            }
        }

        let meta_path = self.path.join("meta.json");
        if meta_path.exists() {
            if let Ok(content) = fs::read_to_string(&meta_path) {
                if let Ok(meta) = serde_json::from_str::<serde_json::Value>(&content) {
                    self.next_id = meta["next_id"].as_u64().unwrap_or(0);
                }
            }
        }

        // Ensure next_id doesn't collide
        if let Some(max_id) = self.entries.keys().max() {
            self.next_id = self.next_id.max(*max_id + 1);
        }
    }
}

impl Drop for MemoryStore {
    fn drop(&mut self) {
        self.flush();
    }
}
