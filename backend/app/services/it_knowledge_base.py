import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func
from app.models.it import ITTicket, ITKnowledgeArticle
from app.models.user import User
from app.services.rag_service import add_document_to_knowledge, query_knowledge_base, generate_embedding
from app.services.llm_router import get_openai_client
import uuid

logger = logging.getLogger(__name__)

IT_KB_AGENT_ID = "__it_knowledge_base__"


async def _get_or_create_agent_id(db: AsyncSession) -> str:
    from app.models.agent import Agent
    result = await db.execute(select(Agent).where(Agent.id == IT_KB_AGENT_ID))
    agent = result.scalar_one_or_none()
    if not agent:
        agent = Agent(
            id=IT_KB_AGENT_ID,
            name="IT Knowledge Base",
            description="RAG-powered IT knowledge base for ticket resolution",
            model="gpt-4o-mini",
            system_prompt="You are an IT knowledge base assistant.",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        db.add(agent)
        await db.flush()
    return IT_KB_AGENT_ID


# (a) index_resolved_tickets
async def index_resolved_tickets(db: AsyncSession) -> dict:
    """
    Queries all resolved IT tickets that have resolution_notes and indexes them into the RAG knowledge base.
    """
    try:
        agent_id = await _get_or_create_agent_id(db)

        result = await db.execute(
            select(ITTicket).where(
                ITTicket.status.in_(["resolved", "closed"]),
                ITTicket.resolution_notes.isnot(None),
                ITTicket.resolution_notes != ""
            )
        )
        tickets = result.scalars().all()

        indexed_count = 0
        for ticket in tickets:
            content_parts = [f"Description: {ticket.description}"]
            if ticket.resolution_notes:
                content_parts.append(f"Resolution: {ticket.resolution_notes}")
            content_parts.append(f"Category: {ticket.category}")
            if ticket.assignee_id:
                user_result = await db.execute(select(User).where(User.id == ticket.assignee_id))
                assigned_user = user_result.scalar_one_or_none()
                if assigned_user:
                    content_parts.append(f"Assigned To: {assigned_user.full_name or assigned_user.email}")

            content = "\n".join(content_parts)

            resolution_time = None
            if ticket.resolved_at and ticket.created_at:
                resolution_time = (ticket.resolved_at - ticket.created_at).total_seconds() / 3600.0

            metadata = {
                "tags": [ticket.category, ticket.priority],
                "source_ticket_id": ticket.id,
                "resolution_time": round(resolution_time, 2) if resolution_time else None,
                "solved_by": ticket.solved_by or ticket.assignee_id
            }

            try:
                doc = await add_document_to_knowledge(
                    db=db,
                    agent_id=agent_id,
                    filename=f"ticket_{ticket.id}_{ticket.title[:30]}",
                    content=content
                )
                indexed_count += 1
            except Exception as e:
                logger.error(f"Failed to index ticket {ticket.id}: {e}")

        return {"status": "success", "indexed_count": indexed_count, "total_resolved": len(tickets)}
    except Exception as e:
        logger.error(f"Error in index_resolved_tickets: {e}")
        return {"status": "error", "message": str(e)}


# (b) suggest_solutions
async def suggest_solutions(ticket_id: str, db: AsyncSession) -> dict:
    """
    When a new IT ticket is created, searches for similar resolved tickets via RAG.
    """
    try:
        ticket_result = await db.execute(select(ITTicket).where(ITTicket.id == ticket_id))
        ticket = ticket_result.scalar_one_or_none()
        if not ticket:
            return {"status": "error", "message": "Ticket not found"}

        agent_id = await _get_or_create_agent_id(db)

        similar_chunks = await query_knowledge_base(
            db=db,
            agent_id=agent_id,
            query_text=f"{ticket.title}\n{ticket.description}",
            limit=5
        )

        suggestions = []
        seen_ticket_ids = set()
        for chunk in similar_chunks:
            metadata = chunk.get("metadata", {})
            source_id = metadata.get("source_ticket_id") if isinstance(metadata, dict) else None
            if not source_id or source_id in seen_ticket_ids:
                continue
            seen_ticket_ids.add(source_id)

            source_result = await db.execute(select(ITTicket).where(ITTicket.id == source_id))
            source_ticket = source_result.scalar_one_or_none()
            if not source_ticket:
                continue

            solved_by_name = None
            if source_ticket.solved_by:
                user_result = await db.execute(select(User).where(User.id == source_ticket.solved_by))
                solved_user = user_result.scalar_one_or_none()
                solved_by_name = solved_user.full_name if solved_user else None

            suggestions.append({
                "similarity_score": chunk.get("similarity", 0),
                "original_problem": source_ticket.title,
                "solution": source_ticket.resolution_notes,
                "solved_by": solved_by_name,
                "resolution_time": metadata.get("resolution_time") if isinstance(metadata, dict) else None,
                "apply_suggestion": False
            })

        suggestions.sort(key=lambda x: x["similarity_score"], reverse=True)
        return {"status": "success", "ticket_id": ticket_id, "suggestions": suggestions[:3]}
    except Exception as e:
        logger.error(f"Error in suggest_solutions: {e}")
        return {"status": "error", "message": str(e)}


# (c) auto_tag_ticket
async def auto_tag_ticket(ticket_id: str, db: AsyncSession) -> dict:
    """
    Uses LLM to auto-categorize ticket content and assign metadata.
    """
    try:
        ticket_result = await db.execute(select(ITTicket).where(ITTicket.id == ticket_id))
        ticket = ticket_result.scalar_one_or_none()
        if not ticket:
            return {"status": "error", "message": "Ticket not found"}

        client, _ = await get_openai_client()

        prompt = f"""Analyze this IT support ticket and suggest categorization:

Title: {ticket.title}
Description: {ticket.description}

Return a JSON object with:
- category: one of [hardware, software, network, access, email, other]
- priority: one of [low, medium, high, critical] based on urgency keywords (e.g. "urgent", "production down", "cannot work" = critical)
- suggested_tags: array of 2-5 relevant tags
- reasoning: brief explanation of your categorization

Respond ONLY with valid JSON, no markdown, no explanation outside the JSON."""

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300
        )
        content = response.choices[0].message.content.strip()
        content = content.removeprefix("```json").removesuffix("```").strip()
        analysis = json.loads(content)

        analyst_name = None
        if ticket.assignee_id:
            user_result = await db.execute(select(User).where(User.id == ticket.assignee_id))
            user = user_result.scalar_one_or_none()
            analyst_name = user.full_name if user else None
        elif ticket.solved_by:
            user_result = await db.execute(select(User).where(User.id == ticket.solved_by))
            user = user_result.scalar_one_or_none()
            analyst_name = user.full_name if user else None

        suggested_assignee = analyst_name
        tags = {
            "auto_category": analysis.get("category", ticket.category),
            "auto_priority": analysis.get("priority", ticket.priority),
            "auto_tags": analysis.get("suggested_tags", []),
            "auto_reasoning": analysis.get("reasoning", ""),
            "suggested_assignee": suggested_assignee,
            "auto_tagged_at": datetime.now(timezone.utc).isoformat()
        }

        existing_metadata = ticket.ticket_meta or {}
        existing_metadata["auto_tags"] = tags
        ticket.ticket_meta = existing_metadata
        await db.commit()

        return {
            "status": "success",
            "ticket_id": ticket_id,
            "suggested_tags": {
                "category": analysis.get("category"),
                "priority": analysis.get("priority"),
                "suggested_tags": analysis.get("suggested_tags", []),
                "suggested_assignee": suggested_assignee,
                "reasoning": analysis.get("reasoning"),
            }
        }
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing LLM response in auto_tag_ticket: {e}")
        return {"status": "error", "message": f"Failed to parse LLM response: {e}"}
    except Exception as e:
        logger.error(f"Error in auto_tag_ticket: {e}")
        return {"status": "error", "message": str(e)}


# (d) generate_kb_article
async def generate_kb_article(ticket_id: str, db: AsyncSession) -> dict:
    """
    Generates a knowledge base article from a resolved ticket using LLM.
    """
    try:
        ticket_result = await db.execute(select(ITTicket).where(ITTicket.id == ticket_id))
        ticket = ticket_result.scalar_one_or_none()
        if not ticket:
            return {"status": "error", "message": "Ticket not found"}

        if not ticket.resolution_notes:
            return {"status": "error", "message": "Ticket has no resolution notes"}

        client, _ = await get_openai_client()

        author_name = None
        if ticket.solved_by:
            user_result = await db.execute(select(User).where(User.id == ticket.solved_by))
            author = user_result.scalar_one_or_none()
            author_name = author.full_name if author else None

        prompt = f"""Generate a knowledge base article from this resolved IT ticket:

Title: {ticket.title}
Original Problem: {ticket.description}
Category: {ticket.category}
Resolution Notes: {ticket.resolution_notes}

Author: {author_name or 'IT Support'}

Return a JSON object with:
- title: a clear KB article title
- problem_description: detailed problem description
- symptoms: array of strings, 3-5 observable symptoms
- root_cause: the identified root cause
- resolution_steps: array of numbered step strings (5-10 clear, actionable steps)
- prevention_tips: array of strings, 2-4 prevention tips
- tags: array of 3-6 relevant tags
- category: confirm or adjust the category

Respond ONLY with valid JSON, no markdown, no explanation outside the JSON."""

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=800
        )
        content = response.choices[0].message.content.strip()
        content = content.removeprefix("```json").removesuffix("```").strip()
        article_data = json.loads(content)

        article = ITKnowledgeArticle(
            id=uuid.uuid4().hex,
            title=article_data.get("title", ticket.title),
            problem_description=article_data.get("problem_description", ticket.description),
            symptoms=article_data.get("symptoms", []),
            root_cause=article_data.get("root_cause", ""),
            resolution_steps=article_data.get("resolution_steps", []),
            prevention_tips=article_data.get("prevention_tips", []),
            category=article_data.get("category", ticket.category),
            tags=article_data.get("tags", [ticket.category]),
            source_ticket_id=ticket_id,
            author=author_name,
        )
        db.add(article)
        await db.flush()

        # Index the article into RAG
        try:
            agent_id = await _get_or_create_agent_id(db)
            kb_content = f"Title: {article.title}\nCategory: {article.category}\n\nProblem: {article.problem_description}\n\nSymptoms: {json.dumps(article.symptoms or [])}\n\nRoot Cause: {article.root_cause}\n\nResolution Steps: {json.dumps(article.resolution_steps or [])}\n\nPrevention: {json.dumps(article.prevention_tips or [])}"
            doc = await add_document_to_knowledge(
                db=db,
                agent_id=agent_id,
                filename=f"kb_article_{article.id}",
                content=kb_content
            )
            article.embedding_id = doc.id
        except Exception as e:
            logger.error(f"Failed to index KB article {article.id}: {e}")

        await db.commit()
        await db.refresh(article)

        return {
            "status": "success",
            "article": {
                "id": article.id,
                "title": article.title,
                "category": article.category,
                "symptoms": article.symptoms,
                "root_cause": article.root_cause,
                "resolution_steps": article.resolution_steps,
                "prevention_tips": article.prevention_tips,
                "tags": article.tags,
                "author": article.author,
            }
        }
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing LLM response in generate_kb_article: {e}")
        return {"status": "error", "message": f"Failed to parse LLM response: {e}"}
    except Exception as e:
        logger.error(f"Error in generate_kb_article: {e}")
        return {"status": "error", "message": str(e)}


# (e) suggest_sla_estimate
async def suggest_sla_estimate(ticket_id: str, db: AsyncSession) -> dict:
    """
    Predicts resolution time based on category, priority, similar tickets, and current workload.
    """
    try:
        ticket_result = await db.execute(select(ITTicket).where(ITTicket.id == ticket_id))
        ticket = ticket_result.scalar_one_or_none()
        if not ticket:
            return {"status": "error", "message": "Ticket not found"}

        similar_result = await db.execute(
            select(ITTicket).where(
                ITTicket.category == ticket.category,
                ITTicket.priority == ticket.priority,
                ITTicket.status.in_(["resolved", "closed"]),
                ITTicket.resolved_at.isnot(None),
                ITTicket.created_at.isnot(None)
            ).limit(20)
        )
        similar_tickets = similar_result.scalars().all()

        resolution_times = []
        for st in similar_tickets:
            if st.resolved_at and st.created_at:
                hours = (st.resolved_at - st.created_at).total_seconds() / 3600.0
                resolution_times.append(hours)

        avg_hours = round(sum(resolution_times) / len(resolution_times), 2) if resolution_times else 0
        similar_count = len(resolution_times)

        open_result = await db.execute(
            select(sa_func.count(ITTicket.id)).where(ITTicket.status.in_(["open", "in_progress"]))
        )
        current_workload = open_result.scalar() or 0

        confidence = "high" if similar_count >= 5 else "medium" if similar_count >= 2 else "low"

        if current_workload > 10 and avg_hours > 0:
            avg_hours = round(avg_hours * 1.3, 2)

        return {
            "status": "success",
            "ticket_id": ticket_id,
            "estimated_hours": avg_hours,
            "confidence": confidence,
            "similar_tickets_count": similar_count,
            "similar_tickets_avg_time": avg_hours,
            "current_workload_open_tickets": current_workload
        }
    except Exception as e:
        logger.error(f"Error in suggest_sla_estimate: {e}")
        return {"status": "error", "message": str(e)}


# (f) detect_recurring_issues
async def detect_recurring_issues(db: AsyncSession) -> dict:
    """
    Analyzes ticket patterns over last 30 days to find recurring issues using embedding similarity.
    """
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)

        tickets_result = await db.execute(
            select(ITTicket).where(ITTicket.created_at >= cutoff).order_by(ITTicket.created_at.desc())
        )
        tickets = tickets_result.scalars().all()

        if len(tickets) < 3:
            return {"status": "success", "recurring_issues": [], "message": "Not enough tickets for pattern detection"}

        agent_id = await _get_or_create_agent_id(db)
        client, _ = await get_openai_client()

        ticket_texts = []
        for t in tickets:
            text = f"Title: {t.title}\nCategory: {t.category}\nDescription: {t.description[:500]}"
            ticket_texts.append({"id": t.id, "text": text, "category": t.category, "title": t.title})

        groups_batch = [t["text"] for t in ticket_texts]
        batch_prompt = f"""Analyze these {len(groups_batch)} IT support tickets from the last 30 days.

Tickets:
{chr(10).join(f"{i+1}. [{t['id']}] {t['text'][:300]}" for i, t in enumerate(ticket_texts))}

Identify if there are recurring issues (clusters of 3+ similar tickets about the same problem).
Return a JSON object with:
- recurring_issues: array of objects with:
  - cluster_id: integer
  - description: summary of the recurring problem
  - ticket_count: number of tickets in this cluster
  - affected_users_estimate: estimated number of unique users
  - severity: one of [low, medium, high, critical]
  - root_cause_hypothesis: likely root cause
  - recommended_permanent_fix: what should be done to prevent it

If no recurring issues found, return an empty array.
Respond ONLY with valid JSON, no markdown."""

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": batch_prompt}],
            temperature=0.3,
            max_tokens=1500
        )
        content = response.choices[0].message.content.strip()
        content = content.removeprefix("```json").removesuffix("```").strip()
        analysis = json.loads(content)

        recurring = analysis.get("recurring_issues", [])
        for issue in recurring:
            issue["detection_date"] = datetime.now(timezone.utc).isoformat()
            issue["analysis_period_days"] = 30

        return {
            "status": "success",
            "recurring_issues": recurring,
            "total_tickets_analyzed": len(tickets),
            "analysis_period_days": 30
        }
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing LLM response in detect_recurring_issues: {e}")
        return {"status": "error", "message": f"Failed to parse LLM response: {e}"}
    except Exception as e:
        logger.error(f"Error in detect_recurring_issues: {e}")
        return {"status": "error", "message": str(e)}


# (g) suggest_preventive_actions
async def suggest_preventive_actions(category: Optional[str] = None, db: AsyncSession = None) -> dict:
    """
    Suggests preventive measures based on ticket history, ranked by ROI.
    """
    try:
        query = select(ITTicket).where(ITTicket.status.in_(["resolved", "closed"]))
        if category:
            query = query.where(ITTicket.category == category)
        result = await db.execute(query.order_by(ITTicket.created_at.desc()).limit(50))
        tickets = result.scalars().all()

        if not tickets:
            return {"status": "success", "actions": [], "message": "No ticket history available"}

        categories = {}
        for t in tickets:
            cat = t.category or "other"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append({
                "title": t.title,
                "priority": t.priority,
                "resolution_notes": t.resolution_notes[:300] if t.resolution_notes else ""
            })

        client, _ = await get_openai_client()

        cat_summaries = []
        for cat, cat_tickets in categories.items():
            cat_summaries.append({
                "category": cat,
                "ticket_count": len(cat_tickets),
                "top_tickets": cat_tickets[:5]
            })

        prompt = f"""Analyze these IT support ticket patterns and suggest preventive actions:

{json.dumps(cat_summaries, indent=2)}

Return a JSON object with:
- by_category: object where keys are category names and values are objects with:
  - top_issues: array of 2-4 strings summarizing top recurring issues
  - prevention_strategies: array of 2-4 actionable prevention strategies
  - automation_opportunities: array of strings for automatable resolutions

- ranked_actions: array of objects (max 10, sorted by ROI) with:
  - rank: integer
  - action: description of the action
  - category: which category this applies to
  - estimated_roi: one of [high, medium, low]
  - effort: one of [low, medium, high]
  - impact: brief description of expected impact

Respond ONLY with valid JSON, no markdown."""

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=1500
        )
        content = response.choices[0].message.content.strip()
        content = content.removeprefix("```json").removesuffix("```").strip()
        analysis = json.loads(content)

        return {
            "status": "success",
            "by_category": analysis.get("by_category", {}),
            "ranked_actions": analysis.get("ranked_actions", []),
            "tickets_analyzed": len(tickets)
        }
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing LLM response in suggest_preventive_actions: {e}")
        return {"status": "error", "message": f"Failed to parse LLM response: {e}"}
    except Exception as e:
        logger.error(f"Error in suggest_preventive_actions: {e}")
        return {"status": "error", "message": str(e)}


# KB search function for the search endpoint
async def search_kb_articles(query: str, db: AsyncSession, top_k: int = 5) -> List[Dict[str, Any]]:
    agent_id = await _get_or_create_agent_id(db)
    chunks = await query_knowledge_base(db=db, agent_id=agent_id, query_text=query, limit=top_k)
    return chunks
