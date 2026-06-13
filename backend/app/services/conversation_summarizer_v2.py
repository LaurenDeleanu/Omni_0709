import logging
import json
from typing import List, Dict, Any, Optional
from app.services.llm_router import get_llm_client

logger = logging.getLogger("successcore.summarizer")

SUMMARIZATION_PROMPT = """Summarize the following conversation exchanges concisely. 
Retain key facts, decisions, actions taken, data found, and important context.
Drop greetings, filler words, and redundant details.

Conversation to summarize:
{conversation}

Summary (2-5 sentences, capturing only the essential information):"""


async def summarize_conversation(
    messages: List[Dict[str, str]],
    model: str = "gpt-4o-mini",
    db=None,
) -> Optional[str]:
    if not messages or len(messages) < 2:
        return None

    conversation_text = ""
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if isinstance(content, str):
            conversation_text += f"[{role}]: {content[:500]}\n"

    if len(conversation_text) < 50:
        return None

    prompt = SUMMARIZATION_PROMPT.format(conversation=conversation_text)

    try:
        client, _ = await get_llm_client(model, None, db)
        response = await client.chat.completions.create(
            model=model,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
        )
        summary = response.choices[0].message.content or ""
        return summary.strip()
    except Exception as e:
        logger.warning(f"Conversation summarization failed: {e}")
        return None


async def compress_context_window(
    messages: List[Dict[str, Any]],
    max_tokens: int = 8000,
    keep_last: int = 4,
    model: str = "gpt-4o-mini",
    db=None,
) -> List[Dict[str, Any]]:
    if not messages:
        return messages

    total_chars = sum(len(str(m.get("content", ""))) for m in messages)
    estimated_tokens = total_chars // 3

    if estimated_tokens <= max_tokens:
        return messages

    keep_messages = messages[-keep_last:] if len(messages) > keep_last else messages
    summarize_messages = messages[:-keep_last] if len(messages) > keep_last else []

    if not summarize_messages:
        return keep_messages

    summary = await summarize_conversation(summarize_messages, model, db)

    if summary:
        summary_msg = {
            "role": "system",
            "content": f"[CONVERSATION SUMMARY]\n{summary}\n[/CONVERSATION SUMMARY]"
        }
        result = [summary_msg] + keep_messages
        new_chars = sum(len(str(m.get("content", ""))) for m in result)
        logger.info(f"Context compressed: {total_chars} -> {new_chars} chars ({len(messages)} -> {len(result)} messages)")
        return result

    return keep_messages
