import logging
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from datetime import datetime, timezone
import uuid

from app.models.rag import KnowledgeDocument, KnowledgeChunk
from app.models.agent import Agent
from app.services.rerank import rerank_chunks, _compute_keyword_overlap

logger = logging.getLogger(__name__)

def semantic_chunk_text(text: str, max_chars: int = 1000, overlap_chars: int = 200) -> List[str]:
    """
    Chunks text semantically by paragraph and sentence boundaries using LangChain's RecursiveCharacterTextSplitter.
    """
    if not text:
        return []
        
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_chars,
            chunk_overlap=overlap_chars,
            separators=["\n\n", "\n", " ", ""]
        )
        return splitter.split_text(text)
    except ImportError:
        logger.warning("langchain-text-splitters not installed, falling back to basic chunking")
        # Fallback to basic chunking if not installed
        chunks = []
        current = ""
        for word in text.split(" "):
            if len(current) + len(word) > max_chars:
                chunks.append(current.strip())
                current = ""
            current += word + " "
        if current:
            chunks.append(current.strip())
        return chunks


CATEGORY_KEYWORDS = {
    "finance": ["nomina", "salary", "sueldo", "payroll", "pago", "factura", "invoice", "budget", "presupuesto", "gasto", "expense", "contable", "accounting", "ledger", "fiscal", "tax", "irpf", "iva"],
    "legal": ["contrato", "legal", "compliance", "gdpr", "fundae", "ley", "reglamento", "auditoria", "denuncia", "whistleblower", "clausula", "juridico", "juzgado"],
    "policy": ["policy", "politica", "handbook", "manual", "procedimiento", "norma", "regla", "protocolo", "guia", "codigo", "conducta"],
    "training": ["training", "formacion", "course", "lms", "curso", "capacitacion", "aprendizaje", "certificacion", "habilidad", "skill"],
    "it": ["ticket", "it", "support", "asset", "soporte", "incidencia", "vpn", "wifi", "password", "software", "hardware", "servidor", "server", "red"],
    "hr": ["employee", "empleado", "vacation", "vacaciones", "permiso", "leave", "baja", "contract", "contratacion", "onboarding", "offboarding", "beneficio"],
    "sales": ["client", "cliente", "sale", "venta", "deal", "pipeline", "lead", "prospecto", "crm", "oportunidad", "comercial"],
    "recruitment": ["candidate", "candidato", "interview", "entrevista", "job", "oferta", "vacante", "reclutamiento", "cv", "resume", "curriculum"],
}


def classify_document(filename: str, content: str) -> str:
    text = (filename + " " + content[:1000]).lower()
    words = set(text.replace(",", " ").replace(".", " ").replace(";", " ").replace(":", " ").split())
    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        matches = sum(1 for kw in keywords if kw in text and (kw in words or len(kw) > 3))
        if matches > 0:
            scores[category] = matches

    if scores:
        return max(scores, key=scores.get)
    return "general"

async def generate_embedding(text: str, agent: Optional[Agent] = None, use_cache: bool = True) -> List[float]:
    if use_cache:
        try:
            from app.services.cache_services import get_cached_embedding, set_cached_embedding
            cached = await get_cached_embedding(text)
            if cached:
                return cached
        except Exception:
            pass

    from app.services.embedding_providers import generate_embedding as generate_embedding_provider

    try:
        vector = await generate_embedding_provider(text, provider="gemini")
    except Exception as gemini_err:
        logger.warning(f"Gemini embedding failed, trying OpenAI: {gemini_err}")
        try:
            vector = await generate_embedding_provider(text, provider="openai")
        except Exception as openai_err:
            raise RuntimeError(f"All embedding providers failed. Gemini: {gemini_err}, OpenAI: {openai_err}") from openai_err

    if use_cache:
        try:
            from app.services.cache_services import set_cached_embedding
            await set_cached_embedding(text, vector)
        except Exception:
            pass

    return vector

async def add_document_to_knowledge(db: AsyncSession, agent_id: str, filename: str, content: str) -> KnowledgeDocument:
    """
    Creates a document, chunks it semantically, assigns document-level metadata,
    generates embeddings, and stores chunks atomically.
    """
    # 1. Create document
    doc = KnowledgeDocument(
        id=uuid.uuid4().hex,
        agent_id=agent_id,
        filename=filename,
        content=content
    )
    db.add(doc)
    await db.flush()
    
    # 2. Semantic chunking
    chunks = semantic_chunk_text(content)
    
    agent_res = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = agent_res.scalar_one_or_none()
    
    # 3. Infer document category metadata (filename + content keywords)
    category = classify_document(filename, content)

    # 4. Generate and store embeddings
    total = len(chunks)
    for idx, text_chunk in enumerate(chunks):
        vector = await generate_embedding(text_chunk, agent)
        chunk = KnowledgeChunk(
            id=uuid.uuid4().hex,
            document_id=doc.id,
            content=text_chunk,
            embedding=vector,
            chunk_metadata={
                "chunk_index": idx,
                "total_chunks": total,
                "source": filename,
                "title": filename.rsplit(".", 1)[0].replace("_", " ").title(),
                "date": datetime.now(timezone.utc).isoformat(),
                "category": category,
                "char_offset": idx * 800,
            }
        )
        db.add(chunk)
        
    await db.commit()
    await db.refresh(doc)
    return doc

async def query_knowledge_base(db: AsyncSession, agent_id: str, query_text: str, limit: int = 4) -> List[Dict[str, Any]]:
    """
    Executes hybrid search (vector pgvector + ILIKE keyword overlap) and applies cross-encoder reranking.
    """
    try:
        agent_res = await db.execute(select(Agent).where(Agent.id == agent_id).limit(1))
        agent = agent_res.scalars().first()
        
        # 1. Vector Search
        query_vector = await generate_embedding(query_text, agent)
        vector_chunks = []
        is_valid_vector = sum(abs(v) for v in query_vector) > 0.0
        
        if is_valid_vector:
            try:
                vector_stmt = (
                    select(KnowledgeChunk)
                    .join(KnowledgeDocument)
                    .where(KnowledgeDocument.agent_id == agent_id)
                    .order_by(KnowledgeChunk.embedding.cosine_distance(query_vector))
                    .limit(limit * 2)
                )
                vector_res = await db.execute(vector_stmt)
                vector_chunks = vector_res.scalars().all()
            except Exception as e:
                import logging
                logging.getLogger("successcore.rag").error(f"Vector search failed: {e}")
                await db.rollback()
        
        # 2. Exact Keyword Search (ILIKE fallback/hybrid)
        words = [w.strip() for w in query_text.split() if len(w.strip()) > 2]
        keyword_chunks = []
        if words:
            conditions = [KnowledgeChunk.content.ilike(f"%{w}%") for w in words]
            kw_stmt = (
                select(KnowledgeChunk)
                .join(KnowledgeDocument)
                .where(KnowledgeDocument.agent_id == agent_id)
                .where(or_(*conditions))
                .limit(limit * 2)
            )
            kw_res = await db.execute(kw_stmt)
            keyword_chunks = kw_res.scalars().all()

        # 3. Hybrid Rank Fusion / Score Merge
        vector_results = {}
        for c in vector_chunks:
            source_dist = c.embedding.cosine_distance(query_vector) if hasattr(c, 'embedding') and c.embedding else 0.5
            similarity = max(0.0, 1.0 - float(source_dist))
            vector_results[c.id] = {
                "chunk": c,
                "vector_sim": similarity
            }
            
        keyword_results = {}
        for c in keyword_chunks:
            overlap = _compute_keyword_overlap(query_text, c.content)
            keyword_results[c.id] = {
                "chunk": c,
                "keyword_score": overlap
            }
            
        merged = {}
        all_ids = set(vector_results.keys()) | set(keyword_results.keys())
        for cid in all_ids:
            v_data = vector_results.get(cid)
            k_data = keyword_results.get(cid)
            
            chunk_obj = (v_data["chunk"] if v_data else k_data["chunk"])
            
            v_sim = v_data["vector_sim"] if v_data else 0.3
            k_score = k_data["keyword_score"] if k_data else _compute_keyword_overlap(query_text, chunk_obj.content)
            
            # Hybrid Score calculation (70% Vector, 30% Keyword)
            similarity = v_sim * 0.7 + k_score * 0.3
            
            merged[cid] = {
                "chunk_id": chunk_obj.id,
                "document_id": chunk_obj.document_id,
                "content": chunk_obj.content,
                "similarity": round(similarity, 4),
                "metadata": chunk_obj.chunk_metadata if hasattr(chunk_obj, 'chunk_metadata') else None,
            }
            
        results = list(merged.values())
        results.sort(key=lambda x: x["similarity"], reverse=True)
        results = results[:limit * 3]
        
        # 4. Reranking using cross-encoder
        if results:
            results = await rerank_chunks(results, query_text, agent, final_limit=limit)

        return results
    except Exception as e:
        logger.error(f"Error en consulta de base de conocimiento (pgvector): {e}")
        try:
            fallback_stmt = (
                select(KnowledgeChunk)
                .join(KnowledgeDocument)
                .where(KnowledgeDocument.agent_id == agent_id)
                .where(KnowledgeChunk.content.ilike(f"%{query_text}%"))
                .limit(limit)
            )
            result = await db.execute(fallback_stmt)
            chunks = result.scalars().all()
            return [{"chunk_id": c.id, "document_id": c.document_id, "content": c.content, "similarity": 0.5} for c in chunks]
        except Exception as inner_e:
            logger.error(f"Error en fallback de base de conocimiento: {inner_e}")
            return []


async def agentic_rag_query(
    db: AsyncSession,
    agent_id: str,
    query_text: str,
    limit: int = 4,
    similarity_threshold: float = 0.4,
    max_rewrites: int = 2,
) -> List[Dict[str, Any]]:
    """
    Agentic RAG: self-correcting retrieval with automatic query rewriting.
    If initial search returns low-similarity results, rewrites the query and retries.
    """
    results = await query_knowledge_base(db, agent_id, query_text, limit)

    if results:
        avg_sim = sum(r.get("similarity", 0) for r in results) / len(results)
        if avg_sim >= similarity_threshold:
            return results

    for attempt in range(max_rewrites):
        rewritten = await _rewrite_query(query_text, db, agent_id, attempt)
        if rewritten == query_text:
            continue

        logger.info(f"Agentic RAG: rewriting query '{query_text[:50]}...' → '{rewritten[:50]}...' (attempt {attempt+1})")
        new_results = await query_knowledge_base(db, agent_id, rewritten, limit)

        if new_results:
            new_avg = sum(r.get("similarity", 0) for r in new_results) / len(new_results)
            if new_avg > similarity_threshold:
                return new_results
            if results and new_avg <= sum(r.get("similarity", 0) for r in results) / max(len(results), 1):
                continue

        if new_results:
            results = new_results

    return results


async def _rewrite_query(
    query: str,
    db: AsyncSession,
    agent_id: str,
    attempt: int = 0,
) -> str:
    """
    Rewrites a query for better retrieval. Attempt 0: expand keywords.
    Attempt 1: decompose compound queries. Attempt 2+: simplify.
    """
    try:
        from app.models.agent import Agent
        from app.services.llm_router import get_llm_client

        agent = (await db.execute(select(Agent).where(Agent.id == agent_id).limit(1))).scalar_one_or_none()

        strategies = [
            "Reescribe esta consulta expandiendo palabras clave y sinónimos relevantes. Solo devuelve la consulta reescrita.",
            "Descompón esta consulta compuesta en una consulta simple y concreta. Solo devuelve la consulta simplificada.",
            "Simplifica esta consulta a sus términos más esenciales (3-5 palabras clave). Solo devuelve la consulta simplificada.",
        ]
        strategy = strategies[min(attempt, len(strategies) - 1)]

        model = "openai/gpt-4o-mini" if agent is None else getattr(agent, "ai_model", "openai/gpt-4o-mini")
        model = model or "openai/gpt-4o-mini"

        client, _ = await get_llm_client(model, agent, db)
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": strategy},
                {"role": "user", "content": query},
            ],
            max_tokens=100,
            temperature=0.3,
        )
        rewritten = response.choices[0].message.content.strip() if response.choices else query
        if len(rewritten) < 3 or len(rewritten) > 500:
            return query
        return rewritten
    except Exception:
        return query


async def decompose_and_retrieve(
    db: AsyncSession,
    agent_id: str,
    query_text: str,
    limit: int = 6,
) -> List[Dict[str, Any]]:
    """
    Multi-hop RAG: decompose complex queries into sub-queries,
    retrieve for each sub-query independently, then merge and deduplicate.
    """
    sub_queries = await _decompose_query(query_text, db, agent_id)
    if not sub_queries or len(sub_queries) <= 1:
        return await agentic_rag_query(db, agent_id, query_text, limit)

    all_results = []
    seen_ids = set()
    per_query_limit = max(3, limit // len(sub_queries))

    for sub_q in sub_queries:
        sub_results = await agentic_rag_query(db, agent_id, sub_q, per_query_limit)
        for r in sub_results:
            chunk_id = r.get("chunk_id")
            if chunk_id and chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                all_results.append(r)

    if len(all_results) < limit:
        remaining = await agentic_rag_query(db, agent_id, query_text, limit)
        for r in remaining:
            chunk_id = r.get("chunk_id")
            if chunk_id and chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                all_results.append(r)

    all_results.sort(key=lambda r: r.get("similarity", 0), reverse=True)
    return all_results[:limit]


async def _decompose_query(
    query: str,
    db: AsyncSession,
    agent_id: str,
) -> List[str]:
    """
    Decompose a compound query into sub-queries using an LLM.
    E.g., "Compare Python and TypeScript usage in engineering"
    → ["Python skills in engineering", "TypeScript skills in engineering"]
    """
    try:
        from app.models.agent import Agent
        from app.services.llm_router import get_llm_client

        agent = (await db.execute(select(Agent).where(Agent.id == agent_id).limit(1))).scalar_one_or_none()
        model = "openai/gpt-4o-mini" if agent is None else getattr(agent, "ai_model", "openai/gpt-4o-mini")
        model = model or "openai/gpt-4o-mini"

        client, _ = await get_llm_client(model, agent, db)
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Descompón la siguiente consulta en 2-4 sub-consultas simples. Devuelve cada sub-consulta en una línea separada. Solo líneas, sin numeración ni explicación. Si la consulta ya es simple, devuelve solo la consulta original."},
                {"role": "user", "content": query},
            ],
            max_tokens=200,
            temperature=0.2,
        )
        if not response.choices:
            return [query]

        lines = [l.strip() for l in response.choices[0].message.content.strip().split("\n") if l.strip()]
        if not lines:
            return [query]
        return lines[:4]
    except Exception:
        return [query]
