//! FFI interface for Python integration.
//!
//! Exposes C-callable functions so the Python CLI can use
//! the Rust memory system via ctypes.

use crate::memory::{MemoryStore, MemoryType};
use crate::sona::SonaEngine;
use std::collections::HashMap;
use std::ffi::{CStr, CString};
use std::os::raw::c_char;
use std::ptr;
use std::sync::Mutex;

/// Global state: memory store + SONA engine.
struct GlobalState {
    store: Option<MemoryStore>,
    sona: Option<SonaEngine>,
}

static STATE: Mutex<GlobalState> = Mutex::new(GlobalState {
    store: None,
    sona: None,
});

/// Initialize memory store at the given path.
/// Returns number of existing entries, or negative on error.
#[no_mangle]
pub extern "C" fn bf_memory_init(path: *const c_char) -> i32 {
    let path_str = unsafe {
        if path.is_null() {
            return -1;
        }
        match CStr::from_ptr(path).to_str() {
            Ok(s) => s.to_string(),
            Err(_) => return -2,
        }
    };

    let mut state = STATE.lock().unwrap();
    state.store = Some(MemoryStore::open(&path_str));
    state.sona = Some(SonaEngine::new());

    state.store.as_ref().map(|s| s.len()).unwrap_or(0) as i32
}

/// Store a memory entry.
///
/// - `key`: null-terminated string key
/// - `vector`: pointer to f32 array
/// - `vector_len`: length of vector array
/// - `data_json`: null-terminated JSON string
/// - `tags_json`: null-terminated JSON array of strings
/// - `entry_type`: 0=molecule, 1=calculation_path, 2=screening_result,
///                 3=workflow_trace, 4=context, 5=pattern
///
/// Returns: entry ID (>= 0) or error code (< 0)
#[no_mangle]
pub extern "C" fn bf_memory_store(
    key: *const c_char,
    vector: *const f32,
    vector_len: usize,
    data_json: *const c_char,
    tags_json: *const c_char,
    entry_type: i32,
) -> i64 {
    let key_str = unsafe {
        if key.is_null() {
            return -1;
        }
        match CStr::from_ptr(key).to_str() {
            Ok(s) => s.to_string(),
            Err(_) => return -2,
        }
    };

    let vec = unsafe {
        if vector.is_null() || vector_len == 0 {
            return -3;
        }
        std::slice::from_raw_parts(vector, vector_len).to_vec()
    };

    let data = unsafe {
        if data_json.is_null() {
            serde_json::Value::Null
        } else {
            match CStr::from_ptr(data_json).to_str() {
                Ok(s) => serde_json::from_str(s).unwrap_or(serde_json::Value::Null),
                Err(_) => serde_json::Value::Null,
            }
        }
    };

    let tags: Vec<String> = unsafe {
        if tags_json.is_null() {
            vec![]
        } else {
            match CStr::from_ptr(tags_json).to_str() {
                Ok(s) => serde_json::from_str(s).unwrap_or_default(),
                Err(_) => vec![],
            }
        }
    };

    let mem_type = match entry_type {
        0 => MemoryType::Molecule,
        1 => MemoryType::CalculationPath,
        2 => MemoryType::ScreeningResult,
        3 => MemoryType::WorkflowTrace,
        4 => MemoryType::Context,
        5 => MemoryType::Pattern,
        _ => MemoryType::Context,
    };

    let mut state = STATE.lock().unwrap();
    if let Some(ref mut store) = state.store {
        store.store(mem_type, &key_str, vec, data, tags) as i64
    } else {
        -10
    }
}

/// Search for similar memories.
/// Returns JSON string of results. Caller must free with bf_free_string().
#[no_mangle]
pub extern "C" fn bf_memory_recall(
    vector: *const f32,
    vector_len: usize,
    k: usize,
) -> *mut c_char {
    let vec = unsafe {
        if vector.is_null() || vector_len == 0 {
            return ptr::null_mut();
        }
        std::slice::from_raw_parts(vector, vector_len).to_vec()
    };

    // Step 1: recall (mut borrow)
    let results: Vec<(f32, u64)> = {
        let mut state = STATE.lock().unwrap();
        if let Some(ref mut store) = state.store {
            store.recall(&vec, k)
        } else {
            vec![]
        }
    };

    // Step 2: read entries (immutable borrow)
    let json_results: Vec<serde_json::Value> = {
        let state = STATE.lock().unwrap();
        results
            .iter()
            .filter_map(|(dist, id)| {
                if let Some(ref store) = state.store {
                    store.get(*id).map(|entry| {
                        serde_json::json!({
                            "id": entry.id,
                            "key": entry.key,
                            "type": format!("{:?}", entry.entry_type),
                            "distance": dist,
                            "data": entry.data,
                            "tags": entry.tags,
                            "confidence": entry.confidence,
                            "access_count": entry.access_count,
                        })
                    })
                } else {
                    None
                }
            })
            .collect()
    };

    let json_str = serde_json::to_string(&json_results).unwrap_or_default();
    CString::new(json_str)
        .map(|s| s.into_raw())
        .unwrap_or(ptr::null_mut())
}

/// Get memory store statistics as JSON.
#[no_mangle]
pub extern "C" fn bf_memory_stats() -> *mut c_char {
    let state = STATE.lock().unwrap();

    let (total, by_type) = if let Some(ref store) = state.store {
        let mut counts: HashMap<String, usize> = HashMap::new();
        for _entry in store.recall_by_type(&MemoryType::Molecule) {
            *counts.entry("molecule".into()).or_default() += 1;
        }
        for _entry in store.recall_by_type(&MemoryType::CalculationPath) {
            *counts.entry("calculation_path".into()).or_default() += 1;
        }
        for _entry in store.recall_by_type(&MemoryType::Pattern) {
            *counts.entry("pattern".into()).or_default() += 1;
        }
        (store.len(), counts)
    } else {
        (0, HashMap::new())
    };

    let sona_count = state.sona.as_ref().map(|s| s.len()).unwrap_or(0);

    let stats = serde_json::json!({
        "total_entries": total,
        "sona_patterns": sona_count,
        "by_type": by_type,
    });

    let json_str = serde_json::to_string(&stats).unwrap_or_default();
    CString::new(json_str)
        .map(|s| s.into_raw())
        .unwrap_or(ptr::null_mut())
}

/// Free a string returned by this library.
#[no_mangle]
pub extern "C" fn bf_free_string(s: *mut c_char) {
    if !s.is_null() {
        unsafe {
            let _ = CString::from_raw(s);
        }
    }
}
