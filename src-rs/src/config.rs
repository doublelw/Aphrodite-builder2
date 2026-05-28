//! AI provider configuration and API interaction.

use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderConfig {
    pub provider: String,       // claude / glm / deepseek
    pub model: String,
    pub api_key: String,
    pub base_url: String,
    pub max_tokens: u32,
    pub temperature: f32,
}

impl Default for ProviderConfig {
    fn default() -> Self {
        Self {
            provider: "deepseek".into(),
            model: "deepseek-chat".into(),
            api_key: String::new(),
            base_url: "https://api.deepseek.com".into(),
            max_tokens: 4096,
            temperature: 0.3,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    pub provider: ProviderConfig,
    pub default_project: Option<String>,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            provider: ProviderConfig::default(),
            default_project: None,
        }
    }
}

pub struct ConfigManager {
    config_dir: PathBuf,
}

impl ConfigManager {
    pub fn new() -> Self {
        let config_dir = dirs::home_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join(".batteryfold");
        fs::create_dir_all(&config_dir).ok();
        Self { config_dir }
    }

    pub fn config_path(&self) -> PathBuf {
        self.config_dir.join("config.json")
    }

    pub fn load(&self) -> Option<AppConfig> {
        let path = self.config_path();
        if !path.exists() {
            return None;
        }
        fs::read_to_string(&path)
            .ok()
            .and_then(|s| serde_json::from_str(&s).ok())
    }

    pub fn save(&self, config: &AppConfig) {
        let path = self.config_path();
        if let Ok(json) = serde_json::to_string_pretty(config) {
            fs::write(path, json).ok();
        }
    }

    pub fn interactive_setup(&self) -> AppConfig {
        use colored::Colorize;

        println!("\n{}", "╔══════════════════════════════════════════════╗".cyan());
        println!("{}", "║     BatteryFold AI Configuration Setup       ║".cyan());
        println!("{}", "╚══════════════════════════════════════════════╝".cyan());
        println!();

        // Provider selection
        println!("{}", "Select AI Provider:".bold());
        println!("  1. {} — Anthropic Claude", "Claude".bright_blue());
        println!("     Models: claude-sonnet-4-6, claude-opus-4-7, claude-haiku-4-5");
        println!("  2. {} — Zhipu GLM", "GLM".bright_green());
        println!("     Models: glm-4-plus, glm-4-flash, glm-4-long");
        println!("  3. {} — DeepSeek", "DeepSeek".bright_magenta());
        println!("     Models: deepseek-chat, deepseek-reasoner");
        println!();

        let provider = self::read_input("Provider (1-3, default 3): ");
        let (provider_name, default_model, default_url) = match provider.trim() {
            "1" => ("claude",
                    "claude-sonnet-4-6",
                    "https://api.anthropic.com"),
            "2" => ("glm",
                    "glm-4-plus",
                    "https://open.bigmodel.cn/api/paas/v4"),
            _ => ("deepseek",
                  "deepseek-chat",
                  "https://api.deepseek.com"),
        };

        let api_key = read_input(&format!("API Key: "));
        if api_key.trim().is_empty() {
            println!("{}", "ERROR: API key cannot be empty.".red());
            std::process::exit(1);
        }

        println!("\n{}", "Base URL:".bold());
        println!("  Default: {}", default_url);
        let custom_url = read_input("Custom URL (Enter for default): ");
        let base_url = if custom_url.trim().is_empty() {
            default_url.to_string()
        } else {
            custom_url.trim().to_string()
        };

        let model = read_input(&format!("Model (Enter for {}): ", default_model));
        let model = if model.trim().is_empty() {
            default_model.to_string()
        } else {
            model.trim().to_string()
        };

        let config = AppConfig {
            provider: ProviderConfig {
                provider: provider_name.to_string(),
                model,
                api_key: api_key.trim().to_string(),
                base_url,
                max_tokens: 4096,
                temperature: 0.3,
            },
            default_project: None,
        };

        self.save(&config);
        println!("\n{} Configuration saved to {}",
                 "✓".green(),
                 self.config_path().display());

        config
    }

    pub fn call_ai(&self, config: &ProviderConfig, system: &str, user: &str) -> Result<String, String> {
        match config.provider.as_str() {
            "claude" => self::call_claude(config, system, user),
            _ => self::call_openai_compatible(config, system, user),
        }
    }
}

fn call_claude(config: &ProviderConfig, system: &str, user: &str) -> Result<String, String> {
    let url = format!("{}/v1/messages", config.base_url);

    let body = serde_json::json!({
        "model": config.model,
        "max_tokens": config.max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    });

    let response = ureq::post(&url)
        .set("x-api-key", &config.api_key)
        .set("anthropic-version", "2023-06-01")
        .set("Content-Type", "application/json")
        .send_json(&body)
        .map_err(|e| format!("API error: {}", e))?;

    let json: serde_json::Value = response.into_json()
        .map_err(|e| format!("Parse error: {}", e))?;

    json.get("content")
        .and_then(|c| c.get(0))
        .and_then(|c| c.get("text"))
        .and_then(|t| t.as_str())
        .map(|s| s.to_string())
        .ok_or_else(|| "No response content".into())
}

fn call_openai_compatible(config: &ProviderConfig, system: &str, user: &str) -> Result<String, String> {
    let url = format!("{}/chat/completions", config.base_url);

    let body = serde_json::json!({
        "model": config.model,
        "max_tokens": config.max_tokens,
        "temperature": config.temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    });

    let response = ureq::post(&url)
        .set("Authorization", &format!("Bearer {}", config.api_key))
        .set("Content-Type", "application/json")
        .send_json(&body)
        .map_err(|e| format!("API error: {}", e))?;

    let json: serde_json::Value = response.into_json()
        .map_err(|e| format!("Parse error: {}", e))?;

    json.get("choices")
        .and_then(|c| c.get(0))
        .and_then(|c| c.get("message"))
        .and_then(|m| m.get("content"))
        .and_then(|t| t.as_str())
        .map(|s| s.to_string())
        .ok_or_else(|| "No response content".into())
}

pub fn read_input(prompt: &str) -> String {
    use std::io::{self, Write};
    print!("{}", prompt);
    io::stdout().flush().ok();
    let mut input = String::new();
    io::stdin().read_line(&mut input).ok();
    input.trim().to_string()
}
