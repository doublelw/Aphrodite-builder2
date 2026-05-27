//! BatteryFold Memory System
//!
//! High-performance vector memory for molecular design workflows.
//! Inspired by Ruflo's AgentDB + SONA architecture.
//!
//! Components:
//!   - HNSW index for sub-millisecond vector retrieval
//!   - Persistent MemoryStore for cross-session knowledge
//!   - SONA self-optimizing pattern capture

mod hnsw;
mod memory;
mod sona;
mod ffi;

pub use hnsw::HnswIndex;
pub use memory::{MemoryStore, MemoryEntry, MemoryType};
pub use sona::SonaEngine;
