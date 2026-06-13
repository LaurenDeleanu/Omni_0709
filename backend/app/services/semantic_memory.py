import json
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from datetime import datetime, timezone

from app.models.agent import EpisodicMemory, ConversationEpoch, UserMemoryPreference, AgentExecutionRun
from app.services.llm_router import get_llm_client

logger = logging.getLogger("successcore.semantic_memory")

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

_pgvector_available = True
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    _pgvector_available = False


async def _generate_embedding(text: str, agent: Optional[Any] = None, db: Optional[AsyncSession] = None) -> list:
    from app.services.llm_router import get_openai_client
    client, _ = await get_openai_client(agent, db)
    response = await client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text[:8191],
    )
    return response.data[0].embedding


async def embed_and_store_memory(
    content: str,
    metadata: dict,
    db: AsyncSession,
) -> str:
    import uuid

    embedding = None
    try:
        agent = None
        agent_id = metadata.get("agent_id")
        if agent_id:
            from app.models.agent import Agent
            agent = await db.get(Agent, agent_id)
        embedding = await _generate_embedding(content, agent=agent, db=db)
    except Exception as e:
        logger.warning(f"Embedding generation failed, storing without vector: {e}")

    memory = EpisodicMemory(
        id=uuid.uuid4().hex,
        user_id=metadata.get("user_id", ""),
        agent_id=metadata.get("agent_id"),
        memory_type=metadata.get("memory_type", "general"),
        content=content,
        metadata_info=metadata,
        entities=metadata.get("entities", {}),
        importance_score=float(metadata.get("importance_score", 0.5)),
        occurred_at=metadata.get("occurred_at", datetime.now(timezone.utc)),
        expires_at=metadata.get("expires_at"),
    )

    if embedding is not None:
        if _pgvector_available:
            memory.embedding = embedding
        else:
            memory.embedding = json.dumps(embedding)

    db.add(memory)
    await db.flush()
    logger.info(f"Stored memory {memory.id} (type={memory.memory_type}, importance={memory.importance_score})")
    return memory.id


async def retrieve_similar_memories(
    query: str,
    user_id: str,
    agent_id: Optional[str] = None,
    top_k: int = 5,
    db: AsyncSession = None,
) -> list:
    agent = None
    if agent_id and db:
        from app.models.agent import Agent
        agent = await db.get(Agent, agent_id)
    query_embedding = await _generate_embedding(query, agent=agent, db=db)

    if _pgvector_available:
        distance_expr = text(
            "embedding <=> :embedding"
        ).bindparams(embedding=str(query_embedding))

        stmt = (
            select(
                EpisodicMemory,
                EpisodicMemory.embedding.cosine_distance(query_embedding).label("distance"),
            )
            .where(
                EpisodicMemory.user_id == user_id,
            )
            .order_by("distance")
            .limit(top_k)
        )
    else:
        stmt = (
            select(EpisodicMemory)
            .where(EpisodicMemory.user_id == user_id)
            .order_by(EpisodicMemory.importance_score.desc())
            .limit(top_k)
        )

    if agent_id:
        stmt = stmt.where(EpisodicMemory.agent_id == agent_id)

    result = await db.execute(stmt)

    memories = []
    if _pgvector_available:
        for row in result.all():
            memory = row[0]
            distance = float(row[1]) if row[1] is not None else 1.0
            relevance = max(0.0, 1.0 - distance)
            memories.append({
                "id": memory.id,
                "content": memory.content,
                "memory_type": memory.memory_type,
                "importance_score": memory.importance_score,
                "entities": memory.entities,
                "occurred_at": memory.occurred_at.isoformat() if memory.occurred_at else None,
                "relevance": round(relevance, 4),
            })
    else:
        for memory in result.scalars().all():
            memories.append({
                "id": memory.id,
                "content": memory.content,
                "memory_type": memory.memory_type,
                "importance_score": memory.importance_score,
                "entities": memory.entities,
                "occurred_at": memory.occurred_at.isoformat() if memory.occurred_at else None,
                "relevance": 0.5,
            })

    logger.info(f"Retrieved {len(memories)} similar memories for user={user_id}")
    return memories


async def auto_extract_milestones(session_id: str, db: AsyncSession):
    from app.services.llm_router import get_llm_client

    runs_result = await db.execute(
        select(AgentExecutionRun)
        .where(AgentExecutionRun.input_payload.contains({"session_id": session_id}))
        .order_by(AgentExecutionRun.created_at.asc())
        .limit(50)
    )
    runs = list(runs_result.scalars().all())

    if not runs:
        try:
            runs_result = await db.execute(
                select(AgentExecutionRun)
                .where(AgentExecutionRun.output_result != None)
                .order_by(AgentExecutionRun.created_at.desc())
                .limit(30)
            )
            runs = list(runs_result.scalars().all())
        except Exception:
            pass

    if not runs:
        logger.info(f"No runs found for milestone extraction (session={session_id})")
        return []

    conversation_texts = []
    for r in runs:
        user_msg = r.input_payload.get("message", "") if r.input_payload else ""
        reply = r.output_result.get("reply", "") if r.output_result else ""
        if user_msg:
            conversation_texts.append(f"User: {user_msg}")
        if reply:
            conversation_texts.append(f"Assistant: {reply}")

    if not conversation_texts:
        return []

    conversation = "\n".join(conversation_texts[-40:])

    extraction_prompt = (
        "Analyze the following conversation between a user and an AI agent. "
        "Extract key milestones as a JSON array. Each milestone should have:\n"
        "- \"type\": one of [\"decision\", \"fact_learned\", \"preference_expressed\", \"action_taken\"]\n"
        "- \"content\": concise description of what was decided, learned, expressed, or done\n"
        "- \"entities\": list of people, departments, dates, or other named entities mentioned\n"
        "- \"importance\": 0.0-1.0 score (decisions and preferences > 0.7, facts > 0.5)\n"
        "\nReturn ONLY valid JSON array, no other text.\n"
        "\nConversation:\n"
    )

    try:
        client, _ = await get_llm_client("gpt-4o-mini")
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a conversation analyst. Extract key milestones as JSON. Return ONLY a JSON array."},
                {"role": "user", "content": extraction_prompt + conversation[:12000]},
            ],
            temperature=0.2,
            max_tokens=1000,
        )
        raw = response.choices[0].message.content or "[]"
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            if raw.endswith("```"):
                raw = raw[:-3]
        milestones = json.loads(raw)
    except Exception as e:
        logger.warning(f"Milestone extraction failed: {e}")
        return []

    stored_ids = []
    for m in milestones:
        if not isinstance(m, dict):
            continue
        mid = await embed_and_store_memory(
            content=m.get("content", ""),
            metadata={
                "user_id": runs[0].input_payload.get("user_id", "") if runs else "",
                "agent_id": runs[0].agent_id if runs else None,
                "memory_type": "milestone",
                "milestone_type": m.get("type", "fact_learned"),
                "entities": m.get("entities", []),
                "importance_score": float(m.get("importance", 0.7)),
                "occurred_at": datetime.now(timezone.utc),
                "session_id": session_id,
            },
            db=db,
        )
        stored_ids.append(mid)

    logger.info(f"Extracted {len(stored_ids)} milestones from session {session_id}")
    return stored_ids


async def retrieve_context_for_query(
    query: str,
    user_id: str,
    db: AsyncSession,
    max_memories: int = 3,
) -> str:
    context_parts = []

    try:
        similar = await retrieve_similar_memories(query, user_id, db=db, top_k=max_memories)
        if similar:
            mem_lines = ["[Relevant past memories]"]
            for mem in similar:
                mem_lines.append(f"- ({mem['memory_type']}, relevance={mem['relevance']}): {mem['content'][:300]}")
                if mem.get("entities"):
                    entities = mem["entities"]
                    if isinstance(entities, list) and entities:
                        mem_lines.append(f"  Entities: {', '.join(str(e) for e in entities[:5])}")
            context_parts.append("\n".join(mem_lines))
    except Exception as e:
        logger.warning(f"Memory retrieval in context building failed: {e}")

    try:
        epoch_result = await db.execute(
            select(ConversationEpoch)
            .where(ConversationEpoch.user_id == user_id)
            .order_by(ConversationEpoch.epoch_number.desc())
            .limit(3)
        )
        epochs = list(epoch_result.scalars().all())
        if epochs:
            ep_lines = ["[Recent conversation summaries]"]
            for ep in epochs:
                ep_lines.append(f"- Epoch {ep.epoch_number}: {ep.summary_text[:300]}")
            context_parts.append("\n".join(ep_lines))
    except Exception as e:
        logger.warning(f"Epoch retrieval in context building failed: {e}")

    try:
        pref_result = await db.execute(
            select(UserMemoryPreference)
            .where(UserMemoryPreference.user_id == user_id)
        )
        prefs = pref_result.scalar_one_or_none()
        if prefs and prefs.preferences:
            pref_lines = ["[User preferences]"]
            for key, val in list(prefs.preferences.items())[:5]:
                pref_lines.append(f"- {key}: {val}")
            context_parts.append("\n".join(pref_lines))
        if prefs and prefs.frequently_used_tools:
            tools = prefs.frequently_used_tools
            if isinstance(tools, list):
                context_parts.append(f"[Frequently used tools]: {', '.join(tools[:5])}")
    except Exception as e:
        logger.warning(f"Preference retrieval in context building failed: {e}")

    if not context_parts:
        return ""

    return "\n\n".join(context_parts)


async def consolidate_memories(
    user_id: str,
    db: AsyncSession,
    agent_id: Optional[str] = None,
    similarity_threshold: float = 0.82,
) -> int:
    """
    Consolidates similar episodic memories for a user into a single merged memory.
    1. Fetch all episodic memories for user (and agent if specified).
    2. Group similar memories using embeddings or Jaccard similarity.
    3. Use LLM to summarize and merge each group of similar memories.
    4. Save the merged memory and delete/archive the source memories to reduce retrieval noise.
    """
    import math
    from app.models.agent import EpisodicMemory, Agent

    # 1. Fetch active episodic memories for user
    stmt = select(EpisodicMemory).where(EpisodicMemory.user_id == user_id)
    if agent_id:
        stmt = stmt.where(EpisodicMemory.agent_id == agent_id)

    # We only consolidate general or conversation memories, not milestones or preferences
    stmt = stmt.where(EpisodicMemory.memory_type.in_(["general", "conversation"]))

    res = await db.execute(stmt)
    memories = res.scalars().all()

    if len(memories) < 2:
        return 0

    # Helper to parse embedding to list of floats
    def get_embedding_list(mem):
        if not mem.embedding:
            return None
        if isinstance(mem.embedding, list):
            return mem.embedding
        if isinstance(mem.embedding, str):
            try:
                return json.loads(mem.embedding)
            except Exception:
                return None
        return None

    # Helper to compute cosine similarity
    def cosine_similarity(v1, v2):
        dot = sum(a * b for a, b in zip(v1, v2))
        norm_a = math.sqrt(sum(a * a for a in v1))
        norm_b = math.sqrt(sum(b * b for b in v2))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    # Helper for Jaccard similarity fallback
    def jaccard_similarity(s1, s2):
        w1 = set(s1.lower().split())
        w2 = set(s2.lower().split())
        if not w1 or not w2:
            return 0.0
        return len(w1 & w2) / len(w1 | w2)

    # 2. Cluster memories greedy-style
    clusters = []
    visited = set()

    for i, mem_i in enumerate(memories):
        if mem_i.id in visited:
            continue

        cluster = [mem_i]
        visited.add(mem_i.id)

        emb_i = get_embedding_list(mem_i)

        for j, mem_j in enumerate(memories):
            if mem_j.id in visited:
                continue

            emb_j = get_embedding_list(mem_j)

            # Check similarity
            sim = 0.0
            if emb_i and emb_j:
                try:
                    sim = cosine_similarity(emb_i, emb_j)
                except Exception:
                    sim = jaccard_similarity(mem_i.content, mem_j.content)
            else:
                sim = jaccard_similarity(mem_i.content, mem_j.content)

            if sim >= similarity_threshold:
                cluster.append(mem_j)
                visited.add(mem_j.id)

        if len(cluster) >= 2:
            clusters.append(cluster)

    if not clusters:
        logger.info(f"No memory clusters found above similarity threshold for user {user_id}")
        return 0

    # 3. Use LLM to consolidate each cluster
    consolidated_count = 0

    agent = None
    if agent_id:
        agent = await db.get(Agent, agent_id)

    try:
        client, _ = await get_llm_client("gpt-4o-mini", agent=agent, db=db)
    except Exception as e:
        logger.warning(f"Could not initialize LLM client for memory consolidation: {e}")
        return 0

    for cluster in clusters:
        mem_contents = "\n".join([f"- [ID: {m.id}, Importance: {m.importance_score}]: {m.content}" for m in cluster])

        prompt = (
            "Eres un gestor de memoria a largo plazo para un agente de IA. "
            "A continuación tienes una lista de recuerdos episódicos similares de un usuario. "
            "Tu tarea es consolidarlos/fusionarlos en un único recuerdo coherente, conciso y redactado en tercera persona en español. "
            "Asegúrate de NO omitir ningún dato específico o cuantificable (como nombres, cifras, fechas, preferencias explícitas). "
            "Además, calcula un nuevo nivel de importancia para este recuerdo (de 0.0 a 1.0), basándote en la relevancia combinada de los recuerdos agrupados.\n\n"
            "Recuerdos a fusionar:\n"
            f"{mem_contents}\n\n"
            "Responde únicamente con un objeto JSON válido que contenga las siguientes claves:\n"
            "- \"content\": el texto consolidado del recuerdo en español\n"
            "- \"importance\": el score de importancia sugerido (float)\n"
            "- \"entities\": lista de entidades clave (nombres, fechas, departamentos, etc.) implicadas\n"
            "Ejemplo de formato: {\"content\": \"...\", \"importance\": 0.75, \"entities\": [\"ventas\", \"Madrid\"]}"
        )

        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Consolidador de memorias en JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            raw_res = response.choices[0].message.content or "{}"
            result_data = json.loads(raw_res.strip())

            new_content = result_data.get("content")
            new_importance = float(result_data.get("importance", 0.6))
            new_entities = result_data.get("entities", [])

            if new_content:
                # Store new consolidated memory
                consolidated_metadata = {
                    "consolidated_from": [m.id for m in cluster],
                    "agent_id": agent_id,
                    "user_id": user_id,
                    "memory_type": "consolidated",
                    "importance_score": new_importance,
                    "entities": new_entities,
                    "occurred_at": datetime.now(timezone.utc)
                }

                # We use embed_and_store_memory to automatically generate the embedding
                await embed_and_store_memory(
                    content=new_content,
                    metadata=consolidated_metadata,
                    db=db
                )

                # Delete the old memories to prevent duplication/retrieval noise
                for old_mem in cluster:
                    await db.delete(old_mem)

                consolidated_count += len(cluster)
                logger.info(f"Consolidated {len(cluster)} memories into a single consolidated memory.")
        except Exception as ex:
            logger.error(f"Failed to consolidate cluster: {ex}")
            continue

    if consolidated_count > 0:
        await db.commit()

    return consolidated_count


async def apply_memory_decay(
    user_id: str,
    db: AsyncSession,
    agent_id: Optional[str] = None,
    decay_rate: float = 0.01,
) -> int:
    """
    Decays the importance scores of episodic memories based on their age.
    Memories with importance below 0.15 are pruned (deleted) to reduce noise.
    Milestones decay at a much slower rate (20% of the normal rate) and are not pruned below 0.35.
    """
    import math
    from app.models.agent import EpisodicMemory

    stmt = select(EpisodicMemory).where(EpisodicMemory.user_id == user_id)
    if agent_id:
        stmt = stmt.where(EpisodicMemory.agent_id == agent_id)

    res = await db.execute(stmt)
    memories = res.scalars().all()

    now = datetime.now(timezone.utc)
    decayed_or_deleted_count = 0

    for memory in memories:
        # Parse occurred_at with timezone
        occurred_at = memory.occurred_at
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=timezone.utc)

        days_old = (now - occurred_at).days
        if days_old <= 0:
            continue

        # Determine specific decay rate
        current_decay_rate = decay_rate
        min_threshold = 0.15

        if memory.memory_type == "milestone":
            current_decay_rate = decay_rate * 0.2
            min_threshold = 0.35

        # Exponential decay: score = score * exp(-decay_rate * days_old)
        old_score = memory.importance_score or 0.5
        new_score = old_score * math.exp(-current_decay_rate * days_old)

        if new_score < min_threshold:
            # Prune memory
            await db.delete(memory)
            decayed_or_deleted_count += 1
            logger.info(f"Deleted decayed memory {memory.id} (type={memory.memory_type}, old_importance={old_score:.3f}, new_importance={new_score:.3f})")
        else:
            if abs(memory.importance_score - new_score) > 0.01:
                memory.importance_score = round(new_score, 4)
                decayed_or_deleted_count += 1
                logger.info(f"Decayed memory {memory.id} importance from {old_score:.3f} to {new_score:.3f}")

    if decayed_or_deleted_count > 0:
        await db.commit()

    return decayed_or_deleted_count

