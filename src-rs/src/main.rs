//! BatteryFold — AI-powered organic battery design platform.
//!
//! Usage:
//!   batteryfold              # Start interactive session
//!   batteryfold setup        # Configure AI provider
//!   batteryfold projects     # List projects
//!   batteryfold --version    # Show version

use batteryfold_core::config::ConfigManager;
use batteryfold_core::project::ProjectManager;
use batteryfold_core::chat::ChatSession;
use colored::Colorize;
use std::env;

const VERSION: &str = "1.0.0";

fn main() {
    let args: Vec<String> = env::args().collect();

    // Handle CLI arguments
    if args.len() > 1 {
        match args[1].as_str() {
            "--version" | "-v" => {
                println!("BatteryFold v{}", VERSION);
                println!("https://github.com/doublelw/Aphrodite-builder2");
                return;
            }
            "setup" => {
                let cm = ConfigManager::new();
                cm.interactive_setup();
                return;
            }
            "projects" => {
                let pm = ProjectManager::new();
                let projects = pm.list_projects();
                if projects.is_empty() {
                    println!("No projects yet. Run {} to start.", "batteryfold".green());
                } else {
                    println!("{}", "BatteryFold Projects:".bold());
                    println!("{}", "─".repeat(40));
                    for p in &projects {
                        println!("  {} — {} (last: {})",
                                 p.name.cyan(), p.description, p.last_accessed);
                    }
                }
                return;
            }
            "help" | "--help" | "-h" => {
                print_help();
                return;
            }
            _ => {}
        }
    }

    // Print banner
    print_banner();

    // Step 1: Load or configure AI provider
    let config_manager = ConfigManager::new();
    let app_config = match config_manager.load() {
        Some(config) => {
            // Check if API key is configured
            if config.provider.api_key.is_empty() {
                println!("{}", "API key not configured. Starting setup...".yellow());
                config_manager.interactive_setup()
            } else {
                println!("  {} AI: {} ({})", "●".blue(),
                         config.provider.provider, config.provider.model);
                config
            }
        }
        None => {
            println!("{}", "First run — configuring AI provider.".yellow());
            println!("{}", "This only needs to be done once.".dimmed());
            println!();
            config_manager.interactive_setup()
        }
    };

    // Step 2: Select or create project
    println!();
    let project_manager = ProjectManager::new();
    let project_name = match project_manager.interactive_select() {
        Some(name) => name,
        None => {
            println!("{}", "No project selected. Goodbye.".dimmed());
            return;
        }
    };

    // Step 3: Start interactive chat
    let mut session = ChatSession::new(
        project_name,
        config_manager,
        app_config.provider,
    );
    session.run();

    println!("\n{} See you next time!", "👋".to_string());
}

fn print_banner() {
    println!();
    println!("{}", r#"
  +-------------------------------------------------------------------------------+
  |                                                                               |
  |   ______  ____    __  __  ____    _____   ____    ______  ______  ____        |
  |  /\  _  \/\  _`\ /\ \/\ \/\  _`\ /\  __`\/\  _`\ /\__  _\/\__  _\/\  _`\      |
  |  \ \ \L\ \ \ \L\ \ \ \_\ \ \ \L\ \ \ \/\ \ \ \/\ \/_/\ \/\/_/\ \/\ \ \L\_\    |
  |   \ \  __ \ \ ,__/\ \  _  \ \ ,  /\ \ \ \ \ \ \ \ \ \ \ \   \ \ \ \ \  _\L    |
  |    \ \ \/\ \ \ \/  \ \ \ \ \ \ \\ \\ \ \_\ \ \ \_\ \ \_\ \__ \ \ \ \ \ \L\ \  |
  |     \ \_\ \_\ \_\   \ \_\ \_\ \_\ \_\ \_____\ \____/ /\_____\ \ \_\ \ \____/  |
  |      \/_/\/_/\/_/    \/_/\/_/\/_/\/ /\/_____/\/___/  \/_____/  \/_/  \/___/   |
  |                                                                               |
  |   ____     __  __  ______   __       ____    ____    ____                     |
  |  /\  _`\  /\ \/\ \/\__  _\ /\ \     /\  _`\ /\  _`\ /\  _`\                   |
  |  \ \ \L\ \\ \ \ \ \/_/\ \/ \ \ \    \ \ \/\ \ \ \L\_\ \ \L\ \                 |
  |   \ \  _ <'\ \ \ \ \ \ \ \  \ \ \  __\ \ \ \ \ \  _\L\ \ ,  /                 |
  |    \ \ \L\ \\ \ \_\ \ \_\ \__\ \ \L\ \\ \ \_\ \ \ \L\ \ \ \\ \                |
  |     \ \____/ \ \_____\/\_____\\ \____/ \ \____/\ \____/\ \_\ \_\              |
  |      \/___/   \/_____/\/_____/ \/___/   \/___/  \/___/  \/_/\/ /              |
  |                                                                               |
  |  Organic Battery Molecular Design Platform                                    |
  |  Molecule -> Quantum -> Synthesis -> Cell -> Product                          |
  |                                                                               |
  +-------------------------------------------------------------------------------+
"#.cyan());
    println!("  {} v{}", "Aphrodite-Builder".bold(), VERSION);
    println!();
}

fn print_help() {
    print_banner();
    println!("{}", "Usage:".bold());
    println!("  batteryfold              Start interactive AI session");
    println!("  batteryfold setup        Configure AI provider");
    println!("  batteryfold projects     List existing projects");
    println!("  batteryfold --version    Show version");
    println!("  batteryfold help         Show this help");
    println!();
    println!("{}", "First Run:".bold());
    println!("  1. Run {} to configure AI provider", "batteryfold setup".green());
    println!("     Supports: Claude (Anthropic), GLM (Zhipu), DeepSeek");
    println!("  2. Run {} to start designing", "batteryfold".green());
    println!("  3. Create or select a project");
    println!("  4. Chat naturally about your battery design goals");
    println!();
    println!("{}", "Supported AI Providers:".bold());
    println!("  • Claude (Anthropic)  — claude-sonnet-4-6, claude-opus-4-7");
    println!("  • GLM (Zhipu)        — glm-4-plus, glm-4-flash");
    println!("  • DeepSeek           — deepseek-chat, deepseek-reasoner");
    println!();
    println!("{}", "In-Session Commands:".bold());
    println!("  /help         Show available commands");
    println!("  /capabilities Show all platform capabilities");
    println!("  /workflows    List available design workflows");
    println!("  /save <text>  Save important finding to memory");
    println!("  /memory       View project knowledge base");
    println!("  /projects     Switch to different project");
    println!("  /config       Reconfigure AI provider");
    println!("  /quit         Exit BatteryFold");
}
