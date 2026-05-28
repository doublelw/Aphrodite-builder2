//! BatteryFold Core Library
//!
//! High-performance vector memory for molecular design workflows.
//! Inspired by Ruflo's AgentDB + SONA architecture.

pub mod hnsw;
pub mod memory;
pub mod sona;
pub mod ffi;
pub mod config;
pub mod project;
pub mod chat;
pub mod router;

pub use hnsw::HnswIndex;
pub use memory::{MemoryStore, MemoryEntry, MemoryType};
pub use sona::SonaEngine;
