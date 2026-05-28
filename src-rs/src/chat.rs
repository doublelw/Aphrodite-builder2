//! Interactive chat loop with AI and command routing.

use crate::config::{ConfigManager, ProviderConfig, read_input};
use crate::project::ProjectManager;
use crate::router::CommandRouter;
use crate::sona::SonaEngine;
use crate::memory::MemoryType;
use colored::Colorize;

pub struct ChatSession {
    project_name: String,
    config_manager: ConfigManager,
    provider: ProviderConfig,
    sona: SonaEngine,
    conversation_history: Vec<(String, String)>, // (role, content)
}

impl ChatSession {
    pub fn new(project_name: String, config_manager: ConfigManager, provider: ProviderConfig) -> Self {
        Self {
            project_name,
            config_manager,
            provider,
            sona: SonaEngine::new(),
            conversation_history: Vec::new(),
        }
    }

    pub fn run(&mut self) {
        self.print_welcome();

        let system_prompt = CommandRouter::system_prompt(&self.project_name);

        loop {
            println!();
            let prompt = format!("{} ", format!("[{}]", self.project_name).green());
            let input = match read_line(&prompt) {
                Some(s) => s,
                None => continue,
            };

            if input.trim().is_empty() {
                continue;
            }

            // Check built-in commands
            if let Some(response) = CommandRouter::handle_builtin(&input, &self.project_name) {
                if response == "__QUIT__" {
                    println!("\n{} Saving project state...", "→".cyan());
                    break;
                }
                println!("{}", response);
                continue;
            }

            // Handle memory commands
            if input.trim().starts_with("/save") {
                let text = input.trim().strip_prefix("/save ").unwrap_or("").trim();
                if !text.is_empty() {
                    self.save_to_memory(text);
                } else {
                    println!("{} Usage: /save <text to remember>", "→".yellow());
                }
                continue;
            }

            if input.trim().starts_with("/memory") {
                self.show_memory();
                continue;
            }

            // Route to AI
            self.conversation_history.push(("user".into(), input.clone()));

            let context = self.build_context();
            let full_user_message = format!("{}\n\n{}", context, input);

            print!("{} ", "Thinking...".dimmed());
            std::io::Write::flush(&mut std::io::stdout()).ok();

            match self.config_manager.call_ai(&self.provider, &system_prompt, &full_user_message) {
                Ok(response) => {
                    // Clear "Thinking..." line
                    print!("\r{}\r", " ".repeat(30));
                    println!("{}", response);
                    self.conversation_history.push(("assistant".into(), response));
                }
                Err(e) => {
                    print!("\r{}\r", " ".repeat(30));
                    println!("{} API Error: {}", "✗".red(), e);
                    println!("{} Check your API key and network connection.", "→".yellow());
                }
            }
        }
    }

    fn print_welcome(&self) {
        println!();
        println!("{}", "╔═══════════════════════════════════════════════════╗".cyan());
        println!("{}", "║         BatteryFold — Organic Battery AI         ║".cyan());
        println!("{}", "╚═══════════════════════════════════════════════════╝".cyan());
        println!();
        println!("  {}  Project: {}", "●".green(), self.project_name.bold());
        println!("  {}  AI: {} ({})", "●".blue(), self.provider.provider, self.provider.model);
        println!("  {}  Type /help for commands, /quit to exit", "●".yellow());
        println!();
        println!("{}", "─".repeat(52));
    }

    fn build_context(&self) -> String {
        if self.conversation_history.is_empty() {
            return String::new();
        }

        // Keep last 10 messages for context
        let recent: Vec<_> = self.conversation_history.iter().rev().take(10).collect();
        let mut ctx = String::from("[Recent conversation context]\n");
        for (role, content) in recent.into_iter().rev() {
            let preview = if content.len() > 200 {
                format!("{}...", &content[..200])
            } else {
                content.clone()
            };
            ctx.push_str(&format!("{}: {}\n", role, preview));
        }
        ctx
    }

    fn save_to_memory(&mut self, text: &str) {
        // Create a simple vector from text keywords for HNSW
        let vector = self.text_to_vector(text);
        let project_manager = ProjectManager::new();
        if let Some((_info, mut store)) = project_manager.open_project(&self.project_name) {
            let id = store.store(
                MemoryType::Context,
                &format!("note_{}", chrono::Local::now().format("%H%M%S")),
                vector,
                serde_json::json!({"text": text, "saved_by": "user"}),
                vec!["user_note".into()],
            );
            println!("{} Saved to project memory (entry #{})", "✓".green(), id);
        }
    }

    fn show_memory(&self) {
        let project_manager = ProjectManager::new();
        if let Some((_info, store)) = project_manager.open_project(&self.project_name) {
            let molecules = store.recall_by_type(&MemoryType::Molecule);
            let calcs = store.recall_by_type(&MemoryType::CalculationPath);
            let patterns = store.recall_by_type(&MemoryType::Pattern);
            let contexts = store.recall_by_type(&MemoryType::Context);

            println!("\n{} Project Memory: {}", "●".cyan(), self.project_name);
            println!("{}", "─".repeat(40));
            println!("  Molecules:        {}", molecules.len());
            println!("  Calculation paths: {}", calcs.len());
            println!("  SONA patterns:    {}", patterns.len());
            println!("  Notes/Context:    {}", contexts.len());
            println!("  Total entries:    {}", store.len());

            if !contexts.is_empty() {
                println!("\n  {} Recent Notes:", "→".yellow());
                for entry in contexts.iter().take(5) {
                    if let Some(text) = entry.data.get("text").and_then(|t| t.as_str()) {
                        let preview = if text.len() > 60 { &text[..60] } else { text };
                        println!("    • {}", preview.dimmed());
                    }
                }
            }
        }
    }

    fn text_to_vector(&self, text: &str) -> Vec<f32> {
        // Simple hash-based embedding for text
        // In production, this would use a proper embedding model
        let mut vector = vec![0.0f32; 16];
        for (i, byte) in text.as_bytes().iter().enumerate() {
            let idx = i % 16;
            vector[idx] += (*byte as f32 - 64.0) / 64.0;
        }
        // Normalize
        let norm: f32 = vector.iter().map(|x| x * x).sum::<f32>().sqrt().max(0.001);
        for x in vector.iter_mut() {
            *x /= norm;
        }
        vector
    }
}

fn read_line(prompt: &str) -> Option<String> {
    use std::io::{self, Write};
    print!("{}", prompt);
    io::stdout().flush().ok();
    let mut input = String::new();
    match io::stdin().read_line(&mut input) {
        Ok(0) => None, // EOF
        Ok(_) => Some(input.trim().to_string()),
        Err(_) => None,
    }
}
