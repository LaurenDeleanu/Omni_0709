"""
Centralized Model Catalog — single source of truth for all supported LLM models.

Adding a new model requires only adding an entry to MODEL_CATALOG below.
All other components (model_router, model_fallback, context_manager) read from here.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger("successcore.model_catalog")


@dataclass
class ModelSpec:
    """Specification for a single LLM model."""
    id: str                           # The model identifier string used in API calls
    display_name: str                 # Human-readable name
    provider: str                     # openai | anthropic | gemini | openrouter | xai | groq
    context_window: int               # Max context window in tokens
    max_output_tokens: int = 4096     # Max output tokens
    supports_tools: bool = True       # Whether it supports function/tool calling
    supports_vision: bool = False     # Whether it supports image inputs
    supports_json_mode: bool = True   # Whether it supports structured JSON output
    input_cost_per_1k: float = 0.0    # USD per 1K input tokens
    output_cost_per_1k: float = 0.0   # USD per 1K output tokens
    tier: str = "standard"            # fast | standard | reasoning
    deprecated: bool = False          # Mark models as deprecated without removing
    notes: str = ""                   # Any additional notes


# =============================================================================
# MODEL CATALOG — Add new models here
# =============================================================================

MODEL_CATALOG: Dict[str, ModelSpec] = {}


def _register(*specs: ModelSpec):
    for s in specs:
        MODEL_CATALOG[s.id] = s


# ---- OpenAI ----
_register(
    ModelSpec("gpt-4o", "GPT-4o", "openai", 128000, 16384,
             supports_vision=True, input_cost_per_1k=0.0025, output_cost_per_1k=0.01, tier="standard"),
    ModelSpec("gpt-4o-mini", "GPT-4o Mini", "openai", 128000, 16384,
             supports_vision=True, input_cost_per_1k=0.00015, output_cost_per_1k=0.0006, tier="fast"),
    ModelSpec("gpt-4.1", "GPT-4.1", "openai", 1047576, 32768,
             supports_vision=True, input_cost_per_1k=0.002, output_cost_per_1k=0.008, tier="standard"),
    ModelSpec("gpt-4.1-mini", "GPT-4.1 Mini", "openai", 1047576, 32768,
             supports_vision=True, input_cost_per_1k=0.0004, output_cost_per_1k=0.0016, tier="fast"),
    ModelSpec("gpt-4.1-nano", "GPT-4.1 Nano", "openai", 1047576, 32768,
             supports_vision=True, input_cost_per_1k=0.0001, output_cost_per_1k=0.0004, tier="fast"),
    ModelSpec("o3-mini", "o3-mini", "openai", 200000, 100000,
             supports_tools=True, input_cost_per_1k=0.00110, output_cost_per_1k=0.00440, tier="reasoning"),
    ModelSpec("o4-mini", "o4-mini", "openai", 200000, 100000,
             supports_tools=True, input_cost_per_1k=0.00110, output_cost_per_1k=0.00440, tier="reasoning"),
)

# ---- Anthropic ----
_register(
    ModelSpec("claude-sonnet-4-20250514", "Claude Sonnet 4", "anthropic", 200000, 16384,
             supports_vision=True, input_cost_per_1k=0.003, output_cost_per_1k=0.015, tier="standard"),
    ModelSpec("claude-opus-4-20250514", "Claude Opus 4", "anthropic", 200000, 32000,
             supports_vision=True, input_cost_per_1k=0.015, output_cost_per_1k=0.075, tier="reasoning"),
    ModelSpec("claude-3-5-haiku-20241022", "Claude 3.5 Haiku", "anthropic", 200000, 8192,
             input_cost_per_1k=0.0008, output_cost_per_1k=0.004, tier="fast"),
)

# ---- Google Gemini ----
_register(
    ModelSpec("gemini-2.5-pro", "Gemini 2.5 Pro", "gemini", 1048576, 65536,
             supports_vision=True, input_cost_per_1k=0.00125, output_cost_per_1k=0.01, tier="reasoning"),
    ModelSpec("gemini-2.5-flash", "Gemini 2.5 Flash", "gemini", 1048576, 65536,
             supports_vision=True, input_cost_per_1k=0.00015, output_cost_per_1k=0.0006, tier="fast"),
    ModelSpec("gemini-2.0-flash", "Gemini 2.0 Flash", "gemini", 1048576, 8192,
             supports_vision=True, input_cost_per_1k=0.0001, output_cost_per_1k=0.0004, tier="fast"),
)

# ---- xAI / Grok ----
_register(
    ModelSpec("grok-3", "Grok 3", "xai", 131072, 16384,
             input_cost_per_1k=0.003, output_cost_per_1k=0.015, tier="standard"),
    ModelSpec("grok-3-mini", "Grok 3 Mini", "xai", 131072, 16384,
             input_cost_per_1k=0.0003, output_cost_per_1k=0.0005, tier="fast"),
)

# ---- OpenRouter (pass-through models) ----
_register(
    ModelSpec("openrouter/google/gemini-2.0-flash-001", "Gemini 2.0 Flash (OR)", "openrouter", 1048576, 8192,
             input_cost_per_1k=0.0001, output_cost_per_1k=0.0004, tier="fast"),
    ModelSpec("openrouter/openai/gpt-4o-mini", "GPT-4o Mini (OR)", "openrouter", 128000, 16384,
             input_cost_per_1k=0.00015, output_cost_per_1k=0.0006, tier="fast"),
    ModelSpec("meta-llama/llama-3.1-70b-instruct", "Llama 3.1 70B (OR)", "openrouter", 131072, 16384,
             input_cost_per_1k=0.00035, output_cost_per_1k=0.0004, tier="standard"),
    ModelSpec("meta-llama/llama-4-maverick", "Llama 4 Maverick (OR)", "openrouter", 1048576, 65536,
             input_cost_per_1k=0.0002, output_cost_per_1k=0.0006, tier="standard"),
    ModelSpec("google/gemini-2.5-flash-preview-05-20", "Gemini 2.5 Flash Free (OR)", "openrouter", 1048576, 8192,
             input_cost_per_1k=0.0, output_cost_per_1k=0.0, tier="fast"),
    ModelSpec("google/gemini-2.5-pro-preview-05-06", "Gemini 2.5 Pro Free (OR)", "openrouter", 1048576, 8192,
             input_cost_per_1k=0.0, output_cost_per_1k=0.0, tier="standard"),
    ModelSpec("meta-llama/llama-3.3-70b-instruct:free", "Llama 3.3 70B Free (OR)", "openrouter", 131072, 8192,
             input_cost_per_1k=0.0, output_cost_per_1k=0.0, tier="standard"),
    ModelSpec("openrouter/auto", "Auto Free Router (OR)", "openrouter", 128000, 8192,
             input_cost_per_1k=0.0, output_cost_per_1k=0.0, tier="fast"),
    ModelSpec("openrouter/free", "Auto Free Cascade (OR)", "openrouter", 128000, 8192,
             input_cost_per_1k=0.0, output_cost_per_1k=0.0, tier="fast"),
)

# ---- Groq ----
_register(
    ModelSpec("llama-3.3-70b-versatile", "Llama 3.3 70B (Groq)", "groq", 128000, 8192,
             input_cost_per_1k=0.0, output_cost_per_1k=0.0, tier="standard"),
    ModelSpec("llama3-8b-8192", "Llama 3 8B (Groq)", "groq", 8192, 8192,
             input_cost_per_1k=0.0, output_cost_per_1k=0.0, tier="fast"),
    ModelSpec("mixtral-8x7b-32768", "Mixtral 8x7B (Groq)", "groq", 32768, 8192,
             input_cost_per_1k=0.0, output_cost_per_1k=0.0, tier="fast"),
    ModelSpec("gemma2-9b-it", "Gemma 2 9B (Groq)", "groq", 8192, 8192,
             input_cost_per_1k=0.0, output_cost_per_1k=0.0, tier="fast"),
)


# =============================================================================
# Query helpers
# =============================================================================

def get_model_spec(model_id: str) -> Optional[ModelSpec]:
    """Get a model specification by its ID. Returns None if not found."""
    return MODEL_CATALOG.get(model_id)


def get_context_limit(model_id: str) -> int:
    """Get the context window for a model, defaulting to 128K if unknown."""
    spec = MODEL_CATALOG.get(model_id)
    return spec.context_window if spec else 128000


def get_cost_per_token(model_id: str) -> tuple[float, float]:
    """Return (input_cost_per_1k, output_cost_per_1k) for a model."""
    spec = MODEL_CATALOG.get(model_id)
    if not spec:
        return (0.00015, 0.0006)  # default to gpt-4o-mini pricing
    return (spec.input_cost_per_1k, spec.output_cost_per_1k)


def get_provider_for_model(model_id: str) -> str:
    """Return the provider string for a model."""
    spec = MODEL_CATALOG.get(model_id)
    if spec:
        return spec.provider
    # Fallback heuristic for models not in catalog
    model_lower = model_id.lower()
    if "/" in model_lower or "openrouter" in model_lower:
        return "openrouter"
    elif "gemini" in model_lower:
        return "gemini"
    elif "claude" in model_lower or "anthropic" in model_lower:
        return "anthropic"
    elif "grok" in model_lower:
        return "xai"
    elif "groq" in model_lower:
        return "groq"
    elif "llama" in model_lower or "meta" in model_lower:
        return "openrouter"
    return "openai"


def get_models_by_tier(tier: str) -> List[ModelSpec]:
    """Return all non-deprecated models in a given tier."""
    return [m for m in MODEL_CATALOG.values() if m.tier == tier and not m.deprecated]


def get_models_by_provider(provider: str) -> List[ModelSpec]:
    """Return all non-deprecated models from a given provider."""
    return [m for m in MODEL_CATALOG.values() if m.provider == provider and not m.deprecated]


def get_all_model_ids() -> List[str]:
    """Return all non-deprecated model IDs."""
    return [m.id for m in MODEL_CATALOG.values() if not m.deprecated]


def get_catalog_summary() -> List[dict]:
    """Return a summary suitable for API responses / frontend model selectors."""
    return [
        {
            "id": m.id,
            "name": m.display_name,
            "provider": m.provider,
            "tier": m.tier,
            "context_window": m.context_window,
            "supports_vision": m.supports_vision,
            "supports_tools": m.supports_tools,
            "input_cost_per_1k": m.input_cost_per_1k,
            "output_cost_per_1k": m.output_cost_per_1k,
        }
        for m in MODEL_CATALOG.values()
        if not m.deprecated
    ]
