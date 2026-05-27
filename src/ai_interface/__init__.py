"""
AI model configuration and interface layer.

Supports Claude (Anthropic), GLM (Zhipu), and DeepSeek APIs.
Users configure API keys and endpoints through interactive setup
or config file. All AI calls go through a unified interface.
"""
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, List
from enum import Enum


class AIProvider(Enum):
    CLAUDE = "claude"
    GLM = "glm"
    DEEPSEEK = "deepseek"


@dataclass
class ProviderConfig:
    name: str
    api_key_env: str  # environment variable name for API key
    base_url: str
    default_model: str
    available_models: List[str]
    max_tokens: int = 4096
    temperature: float = 0.3


PROVIDERS = {
    AIProvider.CLAUDE: ProviderConfig(
        name="Claude (Anthropic)",
        api_key_env="ANTHROPIC_API_KEY",
        base_url="https://api.anthropic.com",
        default_model="claude-sonnet-4-6",
        available_models=[
            "claude-opus-4-7",
            "claude-sonnet-4-6",
            "claude-haiku-4-5-20251001",
        ],
    ),
    AIProvider.GLM: ProviderConfig(
        name="GLM (Zhipu)",
        api_key_env="GLM_API_KEY",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        default_model="glm-4-plus",
        available_models=[
            "glm-4-plus",
            "glm-4-flash",
            "glm-4-long",
        ],
    ),
    AIProvider.DEEPSEEK: ProviderConfig(
        name="DeepSeek",
        api_key_env="DEEPSEEK_API_KEY",
        base_url="https://api.deepseek.com",
        default_model="deepseek-chat",
        available_models=[
            "deepseek-chat",
            "deepseek-reasoner",
        ],
    ),
}


@dataclass
class AIConfig:
    provider: str = "claude"
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.3

    def get_effective_model(self) -> str:
        if self.model:
            return self.model
        provider = AIProvider(self.provider)
        return PROVIDERS[provider].default_model

    def get_api_key(self) -> Optional[str]:
        if self.api_key:
            return self.api_key
        provider = AIProvider(self.provider)
        return os.environ.get(PROVIDERS[provider].api_key_env)


class AIInterface:
    """
    Unified AI interface supporting Claude, GLM, and DeepSeek.

    Usage:
        ai = AIInterface.from_config('config/ai_config.json')
        response = ai.chat("Design a quinone molecule with voltage > 3.5V")

    Setup:
        AIInterface.interactive_setup()  # guided configuration
    """

    def __init__(self, config: AIConfig):
        self.config = config
        self._client = None

    @classmethod
    def from_config(cls, config_path: str = 'config/ai_config.json') -> 'AIInterface':
        """Load AI configuration from file."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(
                f"Config not found: {config_path}\n"
                f"Run: aphrodite setup --ai  to configure"
            )
        with open(path) as f:
            data = json.load(f)
        return cls(AIConfig(**data))

    @classmethod
    def interactive_setup(cls) -> AIConfig:
        """
        Interactive AI configuration wizard.

        Prompts user for:
        1. Provider selection (Claude/GLM/DeepSeek)
        2. API key
        3. Custom base URL (optional, for proxies)
        4. Model selection
        """
        print("\n=== Aphrodite AI Configuration ===\n")

        print("Select AI provider:")
        providers = list(PROVIDERS.keys())
        for i, p in enumerate(providers, 1):
            cfg = PROVIDERS[p]
            print(f"  {i}. {cfg.name}")
            print(f"     Models: {', '.join(cfg.available_models)}")

        choice = input("\nProvider (1-3): ").strip()
        try:
            provider = providers[int(choice) - 1]
        except (ValueError, IndexError):
            print("Invalid choice, defaulting to Claude")
            provider = AIProvider.CLAUDE

        provider_cfg = PROVIDERS[provider]

        # API key
        existing_key = os.environ.get(provider_cfg.api_key_env)
        if existing_key:
            use_existing = input(
                f"Found {provider_cfg.api_key_env} in environment. Use it? (Y/n): "
            ).strip().lower()
            if use_existing != 'n':
                api_key = None  # use env var
            else:
                api_key = input(f"Enter API key: ").strip() or None
        else:
            api_key = input(f"Enter API key: ").strip() or None

        # Base URL
        custom_url = input(
            f"Base URL (Enter for default: {provider_cfg.base_url}): "
        ).strip() or None

        # Model
        print(f"\nAvailable models:")
        for i, m in enumerate(provider_cfg.available_models, 1):
            default_marker = " (default)" if m == provider_cfg.default_model else ""
            print(f"  {i}. {m}{default_marker}")
        model_choice = input(f"Model (1-{len(provider_cfg.available_models)}): ").strip()
        try:
            model = provider_cfg.available_models[int(model_choice) - 1]
        except (ValueError, IndexError):
            model = provider_cfg.default_model

        config = AIConfig(
            provider=provider.value,
            model=model,
            api_key=api_key,
            base_url=custom_url,
        )

        # Save config
        config_path = Path('config/ai_config.json')
        config_path.parent.mkdir(parents=True, exist_ok=True)
        save_data = {k: v for k, v in config.__dict__.items() if v is not None}
        config_path.write_text(json.dumps(save_data, indent=2))
        print(f"\nConfig saved to {config_path}")

        return config

    def _get_client(self):
        """Lazy-initialize API client."""
        if self._client is not None:
            return self._client

        provider = AIProvider(self.config.provider)
        api_key = self.config.get_api_key()

        if not api_key:
            raise ValueError(
                f"No API key for {provider.value}. "
                f"Set {PROVIDERS[provider].api_key_env} or run setup."
            )

        if provider == AIProvider.CLAUDE:
            try:
                import anthropic
                self._client = anthropic.Anthropic(
                    api_key=api_key,
                    base_url=self.config.base_url,
                )
            except ImportError:
                raise ImportError("Install: pip install anthropic")

        elif provider == AIProvider.GLM:
            try:
                from openai import OpenAI
                base = self.config.base_url or PROVIDERS[AIProvider.GLM].base_url
                self._client = OpenAI(api_key=api_key, base_url=base)
            except ImportError:
                raise ImportError("Install: pip install openai")

        elif provider == AIProvider.DEEPSEEK:
            try:
                from openai import OpenAI
                base = self.config.base_url or PROVIDERS[AIProvider.DEEPSEEK].base_url
                self._client = OpenAI(api_key=api_key, base_url=base)
            except ImportError:
                raise ImportError("Install: pip install openai")

        return self._client

    def chat(self, prompt: str, system: str = None) -> str:
        """
        Send a chat completion request to the configured AI provider.

        Args:
            prompt: User message
            system: System prompt (optional)

        Returns:
            AI response text
        """
        client = self._get_client()
        provider = AIProvider(self.config.provider)
        model = self.config.get_effective_model()

        if provider == AIProvider.CLAUDE:
            messages = []
            kwargs = {
                "model": model,
                "max_tokens": self.config.max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                kwargs["system"] = system
            response = client.messages.create(**kwargs)
            return response.content[0].text
        else:
            # GLM and DeepSeek use OpenAI-compatible API
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )
            return response.choices[0].message.content

    def design_molecules(self, target_properties: Dict[str, float],
                         constraints: str = "") -> str:
        """Ask AI to design molecules meeting target battery properties."""
        system = (
            "You are a molecular design expert specializing in organic battery materials. "
            "Given target battery performance properties, propose candidate molecular "
            "structures with SMILES notation and explain the structure-property relationship. "
            "Focus on first-principles reasoning from quantum chemistry."
        )
        prompt = (
            f"Design organic molecules meeting these battery performance targets:\n"
        )
        for prop, value in target_properties.items():
            prompt += f"  - {prop}: {value}\n"
        if constraints:
            prompt += f"\nAdditional constraints: {constraints}\n"
        prompt += "\nProvide SMILES, rationale, and predicted property values."

        return self.chat(prompt, system=system)

    def analyze_results(self, calculation_results: str) -> str:
        """Ask AI to interpret quantum chemistry calculation results."""
        system = (
            "You are a computational chemistry expert. Analyze quantum chemistry "
            "calculation results and provide insights on battery performance, "
            "structure-property relationships, and suggestions for improvement. "
            "Be specific about energy levels, reorganization energies, and "
            "electrochemical implications."
        )
        return self.chat(calculation_results, system=system)
