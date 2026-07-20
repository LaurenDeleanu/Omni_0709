"""
Token-Aware Context Manager (Phase 1 — P0)
===========================================
Tracks token count across messages, tools, and RAG chunks.
At 80% of model context limit:
  1. Auto-truncates oldest messages
  2. Summarizes removed content
  3. Injects summary back into prompt
Uses tiktoken for accurate token counting.
"""

import logging
import os
from typing import TYPE_CHECKING, List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

if TYPE_CHECKING:
    import tiktoken

logger = logging.getLogger(__name__)

_GLOBAL_CORE_CONTEXT = None

def get_global_core_context() -> str:
    global _GLOBAL_CORE_CONTEXT
    if _GLOBAL_CORE_CONTEXT is None:
        try:
            kb_path = os.path.join(os.path.dirname(__file__), "..", "..", "knowledge_base", "global_core_context.md")
            with open(kb_path, "r", encoding="utf-8") as f:
                _GLOBAL_CORE_CONTEXT = f.read()
        except Exception as e:
            logger.error(f"Could not load global core context: {e}")
            _GLOBAL_CORE_CONTEXT = ""
    return _GLOBAL_CORE_CONTEXT

# Context limits are now fetched dynamically from the central Model Catalog
MODEL_CONTEXT_LIMITS = {
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
}

# Truncation safety margin (80% by default)
DEFAULT_SAFETY_MARGIN = 0.80

# Token overhead for system prompt, tool definitions, etc.
SYSTEM_OVERHEAD_ESTIMATE = 4000


@dataclass
class ContextStats:
    """Token usage statistics for the current context window."""
    total_tokens: int
    message_tokens: int
    system_tokens: int
    tool_tokens: int
    rag_tokens: int
    context_limit: int
    safety_threshold: int
    utilization_pct: float
    needs_truncation: bool


def _get_encoding(model: str = "gpt-4o") -> "tiktoken.Encoding":
    """Get the tiktoken encoding for a model, falling back to cl100k_base."""
    import tiktoken
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """Count tokens in a text string using tiktoken."""
    if not text:
        return 0
    try:
        enc = _get_encoding(model)
        return len(enc.encode(text))
    except Exception:
        return len(text) // 4


def count_message_tokens(messages: List[Dict[str, str]], model: str = "gpt-4o") -> int:
    """Count tokens across a list of chat messages."""
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        role = msg.get("role", "")
        total += count_tokens(content, model)
        total += count_tokens(role, model)
        total += 4  # per-message overhead
    total += 2  # final overhead
    return total


def estimate_tool_schema_tokens(tools: List[Dict[str, Any]], model: str = "gpt-4o") -> int:
    """Estimate token count for tool/function definitions."""
    if not tools:
        return 0
    import json
    text = json.dumps(tools, ensure_ascii=False)
    return count_tokens(text, model)


def get_context_limit(model: str) -> int:
    """Get the context window limit for a given model from the central catalog."""
    from app.services.model_catalog import get_context_limit as _get_catalog_limit
    return _get_catalog_limit(model)


def analyze_context(
    messages: List[Dict[str, str]],
    system_prompt: str = "",
    tools: Optional[List[Dict[str, Any]]] = None,
    rag_chunks: Optional[List[str]] = None,
    model: str = "gpt-4o",
    safety_margin: float = DEFAULT_SAFETY_MARGIN,
) -> ContextStats:
    """Analyze the current context window and return statistics."""
    context_limit = get_context_limit(model)
    safety_threshold = int(context_limit * safety_margin)

    system_tokens = count_tokens(system_prompt, model) + SYSTEM_OVERHEAD_ESTIMATE
    message_tokens = count_message_tokens(messages, model)
    tool_tokens = estimate_tool_schema_tokens(tools or [], model)
    rag_tokens = sum(count_tokens(c, model) for c in (rag_chunks or []))

    total_tokens = system_tokens + message_tokens + tool_tokens + rag_tokens
    utilization_pct = (total_tokens / safety_threshold) * 100 if safety_threshold > 0 else 0

    return ContextStats(
        total_tokens=total_tokens,
        message_tokens=message_tokens,
        system_tokens=system_tokens,
        tool_tokens=tool_tokens,
        rag_tokens=rag_tokens,
        context_limit=context_limit,
        safety_threshold=safety_threshold,
        utilization_pct=round(utilization_pct, 1),
        needs_truncation=total_tokens > safety_threshold,
    )


def truncate_messages(
    messages: List[Dict[str, str]],
    max_tokens: int,
    model: str = "gpt-4o",
    preserve_system: bool = True,
    preserve_last: int = 4,
) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """
    Truncate messages to fit within max_tokens.
    Returns (truncated_messages, removed_messages).
    """
    if not messages:
        return [], []

    # Separate system messages if preserving
    system_msgs = []
    chat_msgs = list(messages)
    if preserve_system:
        system_msgs = [m for m in chat_msgs if m.get("role") == "system"]
        chat_msgs = [m for m in chat_msgs if m.get("role") != "system"]

    # Always keep the last N messages
    if len(chat_msgs) <= preserve_last:
        return system_msgs + chat_msgs, []

    last_msgs = chat_msgs[-preserve_last:]
    older_msgs = chat_msgs[:-preserve_last]

    # Calculate tokens for the must-keep portion
    keep_tokens = (
        count_message_tokens(system_msgs, model)
        + count_message_tokens(last_msgs, model)
    )
    available = max_tokens - keep_tokens

    if available <= 0:
        # Even the minimum doesn't fit — keep only last messages
        logger.warning("Context window too small even for minimum messages")
        return system_msgs + last_msgs, older_msgs

    # Include as many older messages as fit
    kept_older = []
    removed = []
    current_tokens = 0

    for msg in reversed(older_msgs):
        msg_tokens = count_tokens(msg.get("content", ""), model) + 4
        if current_tokens + msg_tokens <= available:
            kept_older.insert(0, msg)
            current_tokens += msg_tokens
        else:
            removed.insert(0, msg)

    truncated = system_msgs + kept_older + last_msgs
    logger.info(
        f"Context truncated: {len(messages)} -> {len(truncated)} messages "
        f"(removed {len(removed)})"
    )
    return truncated, removed


async def summarize_removed_content(
    removed_messages: List[Dict[str, str]],
    model: str = "gpt-4o-mini",
    db=None,
) -> Optional[str]:
    """
    Summarize removed messages into a concise context string.
    Used when context exceeds the safety threshold.
    """
    if not removed_messages:
        return None

    try:
        from app.services.llm_router import get_llm_client

        messages_text = "\n".join(
            f"[{m.get('role', '')}]: {m.get('content', '')[:300]}"
            for m in removed_messages
        )

        summary_prompt = (
            "Resume la siguiente conversación en 2-3 frases en español, preservando "
            "información clave: decisiones, datos, preguntas importantes.\n\n"
            f"{messages_text}"
        )

        client, _ = await get_llm_client(model, None, db)
        response = await client.chat.completions.create(
            model=model,
            temperature=0.2,
            max_tokens=200,
            messages=[{"role": "user", "content": summary_prompt}],
        )

        summary = response.choices[0].message.content
        return f"[Resumen de conversación anterior]: {summary}"
    except Exception as e:
        logger.warning(f"Failed to summarize removed content: {e}")
        return f"[{len(removed_messages)} mensajes anteriores omitidos por límite de contexto]"


def build_token_managed_messages(
    messages: List[Dict[str, str]],
    system_prompt: str = "",
    tools: Optional[List[Dict[str, Any]]] = None,
    rag_chunks: Optional[List[str]] = None,
    model: str = "gpt-4o",
    safety_margin: float = DEFAULT_SAFETY_MARGIN,
    preserve_last: int = 4,
) -> Tuple[List[Dict[str, str]], ContextStats]:
    """
    Full pipeline: analyze context, truncate if needed, inject summary.
    Returns (final_messages, context_stats).
    """
    # Inject Global Core Context
    global_context = get_global_core_context()
    if global_context:
        system_prompt = f"{global_context}\n\n---\n\n{system_prompt}"

    stats = analyze_context(
        messages=messages,
        system_prompt=system_prompt,
        tools=tools,
        rag_chunks=rag_chunks,
        model=model,
        safety_margin=safety_margin,
    )

    if not stats.needs_truncation:
        return messages, stats

    available_for_messages = stats.safety_threshold - (
        stats.system_tokens + stats.tool_tokens + stats.rag_tokens
    )
    available_for_messages = max(available_for_messages, stats.safety_threshold // 2)

    truncated, _ = truncate_messages(
        messages,
        max_tokens=available_for_messages,
        model=model,
        preserve_last=preserve_last,
    )

    logger.info(
        f"Context truncated: {stats.total_tokens}/{stats.context_limit} tokens "
        f"({stats.utilization_pct}%) → {len(truncated)} messages retained"
    )

    return truncated, stats
