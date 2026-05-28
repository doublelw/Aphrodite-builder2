//! Project management — each project has its own knowledge base.

use crate::memory::MemoryStore;
use crate::config::ConfigManager;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectInfo {
    pub name: String,
    pub created_at: String,
    pub description: String,
    pub molecule_count: u64,
    pub last_accessed: String,
}

pub struct ProjectManager {
    projects_dir: PathBuf,
}

impl ProjectManager {
    pub fn new() -> Self {
        let dir = dirs::home_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join(".batteryfold")
            .join("projects");
        fs::create_dir_all(&dir).ok();
        Self { projects_dir: dir }
    }

    pub fn list_projects(&self) -> Vec<ProjectInfo> {
        let mut projects = Vec::new();
        if let Ok(entries) = fs::read_dir(&self.projects_dir) {
            for entry in entries.flatten() {
                let meta_path = entry.path().join("project.json");
                if meta_path.exists() {
                    if let Ok(content) = fs::read_to_string(&meta_path) {
                        if let Ok(info) = serde_json::from_str::<ProjectInfo>(&content) {
                            projects.push(info);
                        }
                    }
                }
            }
        }
        projects.sort_by(|a, b| b.last_accessed.cmp(&a.last_accessed));
        projects
    }

    pub fn create_project(&self, name: &str, description: &str) -> ProjectInfo {
        let project_dir = self.projects_dir.join(name);
        fs::create_dir_all(&project_dir).ok();
        fs::create_dir_all(project_dir.join("memory")).ok();

        let now = chrono::Local::now().format("%Y-%m-%d %H:%M").to_string();
        let info = ProjectInfo {
            name: name.to_string(),
            created_at: now.clone(),
            description: description.to_string(),
            molecule_count: 0,
            last_accessed: now,
        };

        let meta_path = project_dir.join("project.json");
        fs::write(meta_path, serde_json::to_string_pretty(&info).unwrap()).ok();

        info
    }

    pub fn open_project(&self, name: &str) -> Option<(ProjectInfo, MemoryStore)> {
        let project_dir = self.projects_dir.join(name);
        if !project_dir.exists() {
            return None;
        }

        let meta_path = project_dir.join("project.json");
        let info: ProjectInfo = if meta_path.exists() {
            let content = fs::read_to_string(&meta_path).ok()?;
            serde_json::from_str(&content).ok()?
        } else {
            ProjectInfo {
                name: name.to_string(),
                created_at: String::new(),
                description: String::new(),
                molecule_count: 0,
                last_accessed: String::new(),
            }
        };

        // Update last accessed
        let mut updated = info.clone();
        updated.last_accessed = chrono::Local::now().format("%Y-%m-%d %H:%M").to_string();
        fs::write(meta_path, serde_json::to_string_pretty(&updated).unwrap()).ok();

        let memory = MemoryStore::open(project_dir.join("memory").to_str().unwrap());

        Some((updated, memory))
    }

    pub fn project_dir(&self, name: &str) -> PathBuf {
        self.projects_dir.join(name)
    }

    pub fn interactive_select(&self) -> Option<String> {
        use colored::Colorize;

        let projects = self.list_projects();

        if projects.is_empty() {
            println!("{}", "\nNo existing projects. Let's create one.".yellow());
            let name = crate::config::read_input("Project name: ");
            if name.is_empty() {
                return None;
            }
            let desc = crate::config::read_input("Description (optional): ");
            self.create_project(&name, &desc);
            println!("{} Project '{}' created.", "✓".green(), name);
            return Some(name);
        }

        println!("\n{}", "Existing Projects:".bold());
        println!("{}", "─".repeat(50));
        for (i, p) in projects.iter().enumerate() {
            println!("  {}. {} — {}", (i + 1).to_string().cyan(), p.name.bold(), p.description);
            println!("     Created: {} | Last: {} | Molecules: {}",
                     p.created_at.dimmed(), p.last_accessed.dimmed(), p.molecule_count);
        }
        println!("  {}. {} — Start a new project", "n".green(), "<new project>".yellow());
        println!();

        let choice = crate::config::read_input("Select project (number or 'n'): ");

        if choice.trim().to_lowercase() == "n" {
            let name = crate::config::read_input("Project name: ");
            if name.is_empty() {
                return None;
            }
            let desc = crate::config::read_input("Description (optional): ");
            self.create_project(&name, &desc);
            println!("{} Project '{}' created.", "✓".green(), name);
            return Some(name);
        }

        if let Ok(idx) = choice.trim().parse::<usize>() {
            if idx > 0 && idx <= projects.len() {
                return Some(projects[idx - 1].name.clone());
            }
        }

        None
    }
}
