"""
ai/providers/model_catalog.py — Model Catalog (ADR-010)

Defines available models per provider so both configuration and the UI
can work with structured model data rather than raw string IDs.

The user (or config) selects a model. The provider uses the model ID.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ModelInfo:
    """Metadata for a single model available from a provider."""
    id: str                      # The exact model ID string to pass to the provider API
    display_name: str            # Human-readable name
    context_window: int          # Max tokens in context window
    cost_per_1k_input: float     # USD per 1000 input tokens (0.0 for free)
    cost_per_1k_output: float    # USD per 1000 output tokens (0.0 for free)
    supports_json: bool = False
    supports_vision: bool = False
    is_free: bool = False
    notes: Optional[str] = None


# ── OpenRouter Models ────────────────────────────────────────────────────────
OPENROUTER_MODELS: list[ModelInfo] = [
    ModelInfo(
        id="moonshotai/kimi-k2.6:free",
        display_name="Kimi K2.6 (Free)",
        context_window=128_000,
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        supports_json=True,
        is_free=True,
        notes="Primary free model — high quality for HTML generation",
    ),
    ModelInfo(
        id="deepseek/deepseek-r1-0528:free",
        display_name="DeepSeek R1 (Free)",
        context_window=64_000,
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        supports_json=True,
        is_free=True,
        notes="Strong reasoning model — good for complex spec building",
    ),
    ModelInfo(
        id="qwen/qwen3-235b-a22b:free",
        display_name="Qwen3 235B (Free)",
        context_window=40_000,
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        supports_json=True,
        is_free=True,
        notes="Large Qwen3 variant via OpenRouter — very capable",
    ),
    ModelInfo(
        id="meta-llama/llama-3.3-70b-instruct:free",
        display_name="Llama 3.3 70B (Free)",
        context_window=131_000,
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        supports_json=False,
        is_free=True,
    ),
]

# ── Gemini Models ────────────────────────────────────────────────────────────
GEMINI_MODELS: list[ModelInfo] = [
    ModelInfo(
        id="gemini-2.5-flash",
        display_name="Gemini 2.5 Flash",
        context_window=1_000_000,
        cost_per_1k_input=0.0,   # Within free tier limits
        cost_per_1k_output=0.0,
        supports_json=True,
        supports_vision=True,
        is_free=True,
        notes="Very fast, long context — great for full-page generation",
    ),
    ModelInfo(
        id="gemini-2.5-pro",
        display_name="Gemini 2.5 Pro",
        context_window=2_000_000,
        cost_per_1k_input=0.00125,
        cost_per_1k_output=0.01,
        supports_json=True,
        supports_vision=True,
        notes="Best quality Gemini — use for complex or premium generations",
    ),
]

# ── Ollama Models (local) ────────────────────────────────────────────────────
OLLAMA_MODELS: list[ModelInfo] = [
    ModelInfo(
        id="qwen2.5:7b",
        display_name="Qwen2.5 7B (Local)",
        context_window=32_000,
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        supports_json=True,
        is_free=True,
        notes="RTX 3050 compatible — recommended local development model",
    ),
    ModelInfo(
        id="llama3.1:8b",
        display_name="Llama 3.1 8B (Local)",
        context_window=128_000,
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        is_free=True,
        notes="Good general-purpose local model",
    ),
    ModelInfo(
        id="deepseek-r1:7b",
        display_name="DeepSeek R1 7B (Local)",
        context_window=32_000,
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        is_free=True,
        notes="Local reasoning model — excellent for spec building",
    ),
    ModelInfo(
        id="mistral:7b",
        display_name="Mistral 7B (Local)",
        context_window=32_000,
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        is_free=True,
    ),
]


class ModelCatalog:
    """
    Registry of all known models organized by provider.
    Used to validate model selection and compute cost estimates.
    """

    _catalog: dict[str, list[ModelInfo]] = {
        "openrouter": OPENROUTER_MODELS,
        "gemini":     GEMINI_MODELS,
        "ollama":     OLLAMA_MODELS,
    }

    @classmethod
    def get_models(cls, provider: str) -> list[ModelInfo]:
        """Return all models for a given provider name."""
        return cls._catalog.get(provider, [])

    @classmethod
    def find(cls, provider: str, model_id: str) -> Optional[ModelInfo]:
        """Look up a specific model by provider name and model ID."""
        for m in cls.get_models(provider):
            if m.id == model_id:
                return m
        return None

    @classmethod
    def estimate_cost(cls, provider: str, model_id: str, input_tokens: int, output_tokens: int) -> float:
        """Return estimated USD cost for a generation. Returns 0.0 if model is unknown/free."""
        model = cls.find(provider, model_id)
        if not model:
            return 0.0
        return (
            (input_tokens / 1000) * model.cost_per_1k_input
            + (output_tokens / 1000) * model.cost_per_1k_output
        )
