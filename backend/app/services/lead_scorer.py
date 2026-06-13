import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.llm_router import get_llm_client
from app.models.sales import Lead, Client

logger = logging.getLogger(__name__)

SCORING_MODEL = "gpt-4o-mini"


def _compute_engagement_signals(lead: Lead) -> dict:
    score = 0
    details = {}

    domain = ""
    if lead.email and "@" in lead.email:
        domain = lead.email.split("@")[-1].lower()
    free_domains = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com",
                    "proton.me", "protonmail.com", "mail.com", "gmx.com", "icloud.com"}
    if domain and domain not in free_domains:
        details["email_domain_quality"] = "business"
        score += 10
    elif domain and domain in free_domains:
        details["email_domain_quality"] = "personal"
        score += 3
    else:
        details["email_domain_quality"] = "unknown"
        score += 0

    if lead.phone and len(lead.phone.strip()) >= 8:
        details["phone_complete"] = True
        score += 8
    else:
        details["phone_complete"] = False
        score += 0

    response_score = 5
    if lead.stage in ("discovery", "proposal", "negotiation"):
        response_score = 7
    elif lead.stage == "won":
        response_score = 10
    elif lead.stage == "lost":
        response_score = 0
    details["response_time_score"] = response_score
    score += response_score

    max_possible = 25
    normalized = min(score / max_possible * 25, 25) if max_possible > 0 else 0
    return {"raw_score": round(score, 1), "normalized": round(normalized, 1), "details": details}


def _compute_demographic_fit(lead: Lead) -> dict:
    score = 0
    details = {}

    if lead.company_name and len(lead.company_name.strip()) > 2:
        details["company_name_present"] = True
        score += 10
    else:
        details["company_name_present"] = False

    title_seniority_keywords = ["ceo", "cto", "cfo", "vp", "director", "head", "president",
                                 "founder", "owner", "manager", "lead", "senior", "chief",
                                 "gerente", "director", "jefe", "coordinador"]
    title_text = (lead.title or "").lower()
    seniority = "unknown"
    if any(kw in title_text for kw in title_seniority_keywords[:6]):
        seniority = "executive"
        score += 12
    elif any(kw in title_text for kw in title_seniority_keywords[6:]):
        seniority = "manager"
        score += 8
    else:
        score += 3
    details["title_seniority"] = seniority

    details["industry_match"] = "unknown"
    score += 3
    details["geography_match"] = "unknown"
    score += 3

    max_possible = 30
    normalized = min(score / max_possible * 30, 30) if max_possible > 0 else 0
    return {"raw_score": round(score, 1), "normalized": round(normalized, 1), "details": details}


def _compute_behavioral_signals(lead: Lead) -> dict:
    score = 0
    details = {}
    sparse = True

    if lead.stage in ("discovery", "proposal", "negotiation"):
        details["meeting_scheduled"] = True
        score += 12
        sparse = False
    else:
        details["meeting_scheduled"] = False

    if lead.stage in ("proposal", "negotiation", "won"):
        details["advanced_stage"] = True
        score += 8
        sparse = False
    else:
        details["advanced_stage"] = False

    if lead.probability and lead.probability >= 40:
        details["high_manual_probability"] = True
        score += 5
        sparse = False
    else:
        details["high_manual_probability"] = False

    max_possible = 25
    normalized = min(score / max_possible * 25, 25) if max_possible > 0 else 0
    return {"raw_score": round(score, 1), "normalized": round(normalized, 1), "details": details, "sparse": sparse}


def _compute_deal_signals(lead: Lead) -> dict:
    score = 0
    details = {}

    value = lead.estimated_value or 0
    if value >= 50000:
        details["deal_size"] = "large"
        score += 5
    elif value >= 10000:
        details["deal_size"] = "medium"
        score += 3
    elif value > 0:
        details["deal_size"] = "small"
        score += 1
    else:
        details["deal_size"] = "unspecified"
        score += 0

    if lead.stage in ("proposal", "negotiation"):
        details["timeline"] = "active"
        score += 7
    elif lead.stage == "discovery":
        details["timeline"] = "early"
        score += 4
    elif lead.stage == "won":
        details["timeline"] = "closed"
        score += 0
    elif lead.stage == "lost":
        details["timeline"] = "dead"
        score += 0
    else:
        details["timeline"] = "inbound"
        score += 2

    if lead.stage in ("negotiation",):
        details["decision_maker_involved"] = True
        score += 4
    else:
        details["decision_maker_involved"] = lead.stage in ("proposal",)

    details["competition_mentioned"] = "unknown"
    score += 2

    max_possible = 20
    normalized = min(score / max_possible * 20, 20) if max_possible > 0 else 0
    return {"raw_score": round(score, 1), "normalized": round(normalized, 1), "details": details}


def _compute_quality_tier(total_score: float) -> str:
    if total_score >= 65:
        return "hot"
    elif total_score >= 40:
        return "warm"
    else:
        return "cold"


def _estimate_conversion_probability(total_score: float) -> float:
    if total_score >= 80:
        return min(round(total_score * 0.9, 1), 95.0)
    elif total_score >= 65:
        return round(total_score * 0.75, 1)
    elif total_score >= 40:
        return round(total_score * 0.5, 1)
    else:
        return max(round(total_score * 0.3, 1), 2.0)


async def _llm_estimate_behavioral(lead: Lead, db: AsyncSession) -> dict:
    try:
        client, api_key = await get_llm_client(SCORING_MODEL, db=db)
        lead_context = {
            "title": lead.title,
            "company_name": lead.company_name,
            "stage": lead.stage,
            "probability": lead.probability,
            "estimated_value": lead.estimated_value,
            "contact_name": lead.contact_name,
        }
        prompt = (
            "You are a sales intelligence analyst. Based on the lead profile below, "
            "estimate the behavioral engagement signals on a 0-25 scale. Consider: "
            "website visits, email opens, content downloads, and meeting attendance likelihood.\n\n"
            "Lead Profile:\n" + json.dumps(lead_context, indent=2) + "\n\n"
            "Return ONLY valid JSON with:\n"
            '{"estimated_behavioral_score": <float 0-25>, '
            '"website_visits_estimated": <bool>, '
            '"email_opens_estimated": <bool>, '
            '"document_downloads_estimated": <bool>, '
            '"rationale": "<one sentence>"}'
        )
        response = await client.chat.completions.create(
            model=SCORING_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        text = response.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        result = json.loads(text)
        return {
            "normalized": min(float(result.get("estimated_behavioral_score", 10)), 25),
            "details": {
                "website_visits_estimated": result.get("website_visits_estimated", False),
                "email_opens_estimated": result.get("email_opens_estimated", False),
                "document_downloads_estimated": result.get("document_downloads_estimated", False),
                "llm_rationale": result.get("rationale", ""),
                "llm_estimated": True,
            },
            "sparse": False,
        }
    except Exception as e:
        logger.warning(f"LLM behavioral estimate failed, using fallback: {e}")
        return {
            "normalized": 10.0,
            "details": {"website_visits_estimated": False, "email_opens_estimated": False,
                         "document_downloads_estimated": False, "llm_estimated": False, "fallback": True},
            "sparse": True,
        }


async def score_lead(lead_id: str, db: AsyncSession) -> dict:
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalars().first()
    if not lead:
        return {"error": f"Lead {lead_id} not found"}

    engagement = _compute_engagement_signals(lead)
    demographic = _compute_demographic_fit(lead)
    behavioral = _compute_behavioral_signals(lead)
    deal = _compute_deal_signals(lead)

    if behavioral.get("sparse"):
        behavioral = await _llm_estimate_behavioral(lead, db)

    total_score = round(
        engagement["normalized"] + demographic["normalized"] + behavioral["normalized"] + deal["normalized"], 1
    )
    quality_tier = _compute_quality_tier(total_score)
    conversion_prob = _estimate_conversion_probability(total_score)

    lead.score = total_score
    lead.score_breakdown = {
        "engagement": engagement,
        "demographic": demographic,
        "behavioral": behavioral,
        "deal": deal,
        "scored_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.commit()

    return {
        "lead_id": lead_id,
        "score": total_score,
        "score_breakdown": {
            "engagement_signals": engagement["normalized"],
            "demographic_fit": demographic["normalized"],
            "behavioral_signals": behavioral["normalized"],
            "deal_signals": deal["normalized"],
            "engagement_details": engagement["details"],
            "demographic_details": demographic["details"],
            "behavioral_details": behavioral["details"],
            "deal_details": deal["details"],
        },
        "lead_quality_tier": quality_tier,
        "conversion_probability": conversion_prob,
        "explanation": (
            f"Lead '{lead.title}' scored {total_score}/100 ({quality_tier}). "
            f"Estimated {conversion_prob}% conversion probability. "
            f"Strengths: {_summarize_strengths(engagement, demographic, behavioral, deal)}"
        ),
    }


def _summarize_strengths(engagement, demographic, behavioral, deal) -> str:
    strengths = []
    if engagement["normalized"] >= 18:
        strengths.append("strong engagement signals")
    if demographic["normalized"] >= 20:
        strengths.append("excellent demographic fit")
    if behavioral["normalized"] >= 18:
        strengths.append("strong behavioral indicators")
    if deal["normalized"] >= 14:
        strengths.append("promising deal signals")
    return "; ".join(strengths) if strengths else "none identified"


async def suggest_next_action(lead_id: str, db: AsyncSession) -> dict:
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalars().first()
    if not lead:
        return {"error": f"Lead {lead_id} not found"}

    if lead.score is None or lead.score == 0:
        await score_lead(lead_id, db)
        await db.refresh(lead)

    total_score = lead.score or 0
    stage = (lead.stage or "inbound").lower()

    stage_action_map = {
        "inbound": ("follow_up", "immediate", "Review inbound inquiry and establish contact within 24 hours."),
        "discovery": ("call", "this_week", "Schedule a discovery call to understand needs and qualify further."),
        "proposal": ("proposal", "this_week", "Prepare and send a tailored proposal with pricing and timeline."),
        "negotiation": ("call", "immediate", "Address objections and negotiate terms to close the deal."),
        "won": ("nurture", "next_week", "Nurture the relationship for upsell/cross-sell opportunities."),
        "lost": ("disqualify", "next_week", "Archive or re-engage after 90 days if reasons for loss change."),
    }

    default_action = ("email", "next_week", "Send a check-in email to gauge interest and re-engage.")
    action_type, priority, default_reasoning = stage_action_map.get(stage, default_action)

    if total_score >= 65:
        priority = "immediate"
    elif total_score >= 40:
        priority = "this_week" if priority != "immediate" else priority
    else:
        if stage in ("won", "lost"):
            pass
        elif stage == "inbound":
            priority = "next_week"

    try:
        client, api_key = await get_llm_client(SCORING_MODEL, db=db)
        lead_context = {
            "contact_name": lead.contact_name or "there",
            "company_name": lead.company_name or "your company",
            "title": lead.title,
            "stage": stage,
            "score": total_score,
            "estimated_value": lead.estimated_value or 0,
        }
        prompt = (
            "You are a sales coach. Based on this lead, write a short personalized message template.\n"
            "Lead:\n" + json.dumps(lead_context, indent=2) + "\n\n"
            f"Recommended action: {action_type}\n"
            f"Priority: {priority}\n\n"
            "Return ONLY valid JSON with:\n"
            '{"subject": "<email subject>", "body": "<plain text message>", "body_html": "<HTML message>", '
            '"reasoning": "<why this action>", "expected_outcome": "<what should happen>"} '
            "Keep body under 150 words."
        )
        response = await client.chat.completions.create(
            model=SCORING_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        text = response.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        llm_result = json.loads(text)
    except Exception as e:
        logger.warning(f"LLM message generation failed: {e}")
        llm_result = {
            "subject": f"Following up: {lead.title}",
            "body": f"Hi {lead.contact_name or 'there'},\n\nJust checking in on {lead.title}. Looking forward to hearing from you.\n\nBest regards",
            "body_html": f"<p>Hi {lead.contact_name or 'there'},</p><p>Just checking in on <strong>{lead.title}</strong>. Looking forward to hearing from you.</p><p>Best regards</p>",
            "reasoning": default_reasoning,
            "expected_outcome": "Re-engage the lead and advance to the next stage.",
        }

    alternatives = []
    alt_map = [
        ("email", "next_week", "Send a personalized value-prop email highlighting key benefits."),
        ("meeting", "this_week", "Schedule a demo or product walkthrough to showcase ROI."),
        ("call", "immediate", "Make a direct phone call to establish personal rapport."),
    ]
    for alt_type, alt_pri, alt_reason in alt_map:
        if alt_type != action_type:
            alternatives.append({"action_type": alt_type, "priority": alt_pri, "reasoning": alt_reason})

    return {
        "lead_id": lead_id,
        "action_type": action_type,
        "priority": priority,
        "suggested_message_template": {
            "subject": llm_result.get("subject", ""),
            "body": llm_result.get("body", ""),
            "body_html": llm_result.get("body_html", ""),
        },
        "reasoning": llm_result.get("reasoning", default_reasoning),
        "expected_outcome": llm_result.get("expected_outcome", "Advance the lead to the next pipeline stage."),
        "alternative_actions": alternatives[:2],
    }


async def predict_deal_probability(lead_id: str, db: AsyncSession) -> dict:
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalars().first()
    if not lead:
        return {"error": f"Lead {lead_id} not found"}

    try:
        client, api_key = await get_llm_client(SCORING_MODEL, db=db)
        lead_context = {
            "title": lead.title,
            "company_name": lead.company_name,
            "contact_name": lead.contact_name,
            "estimated_value": lead.estimated_value or 0,
            "stage": lead.stage,
            "probability": lead.probability,
            "created_at": lead.created_at.isoformat() if lead.created_at else None,
            "expected_close_date": lead.expected_close_date.isoformat() if lead.expected_close_date else None,
            "score": lead.score or 0,
        }
        pipeline_days = "unknown"
        if lead.created_at:
            delta = datetime.now(timezone.utc) - lead.created_at.replace(tzinfo=timezone.utc)
            pipeline_days = str(delta.days)

        prompt = (
            "You are a sales forecast analyst. Estimate the win probability for this deal.\n"
            "Deal:\n" + json.dumps(lead_context, indent=2) + "\n"
            f"Time in pipeline: {pipeline_days} days\n\n"
            "Consider: deal size, stage, contact seniority, engagement level (score), time in pipeline, competitor presence.\n\n"
            "Return ONLY valid JSON with:\n"
            '{"win_probability": <float 0-100>, "confidence_interval": "<low-high%>", '
            '"key_risks": ["<risk1>", "<risk2>", ...], "accelerators": ["<accelerator1>", ...]}'
        )
        response = await client.chat.completions.create(
            model=SCORING_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        text = response.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        llm_result = json.loads(text)
    except Exception as e:
        logger.warning(f"LLM deal prediction failed: {e}")
        llm_result = {
            "win_probability": float(lead.probability or 10),
            "confidence_interval": f"{max(0, (lead.probability or 10) - 15)}-{min(100, (lead.probability or 10) + 15)}%",
            "key_risks": ["Insufficient data for AI prediction"],
            "accelerators": [],
        }

    return {
        "lead_id": lead_id,
        "win_probability": float(llm_result.get("win_probability", 10)),
        "confidence_interval": llm_result.get("confidence_interval", "N/A"),
        "key_risks": llm_result.get("key_risks", []),
        "accelerators": llm_result.get("accelerators", []),
    }


async def batch_score_pipeline(db: AsyncSession) -> dict:
    result = await db.execute(
        select(Lead).where(Lead.stage.notin_(["won", "lost"]))
    )
    active_leads = result.scalars().all()

    total_leads = len(active_leads)
    hot_leads = 0
    warm_leads = 0
    cold_leads = 0
    weighted_value = 0.0
    expected_closures = 0
    at_risk_count = 0

    for lead in active_leads:
        try:
            scoring = await score_lead(lead.id, db)
            tier = scoring.get("lead_quality_tier", "cold")
            if tier == "hot":
                hot_leads += 1
            elif tier == "warm":
                warm_leads += 1
            else:
                cold_leads += 1

            value = lead.estimated_value or 0
            prob = scoring.get("conversion_probability", 0) / 100.0
            weighted_value += value * prob

            if prob >= 0.5:
                expected_closures += 1

            if lead.stage in ("proposal", "negotiation") and prob < 0.3:
                at_risk_count += 1
        except Exception as e:
            logger.error(f"Error scoring lead {lead.id}: {e}")

    now = datetime.now(timezone.utc)
    current_month = now.month
    current_year = now.year

    return {
        "pipeline_overview": {
            "total_leads": total_leads,
            "hot_leads": hot_leads,
            "warm_leads": warm_leads,
            "cold_leads": cold_leads,
            "scored_at": now.isoformat(),
        },
        "forecasts": {
            "weighted_pipeline_value": round(weighted_value, 2),
            "expected_closures_this_month": expected_closures,
            "at_risk_deals": at_risk_count,
        },
    }


EMAIL_TYPE_CONTEXTS = {
    "cold_outreach": "Initial outreach to a prospect who hasn't heard of us yet. Introduce the company and value prop.",
    "follow_up": "Follow-up after no response to a previous message. Gentle reminder with added value.",
    "demo_invite": "Invite the prospect to a product demo or walkthrough. Highlight key benefits.",
    "proposal_cover": "Cover email for a proposal or quote. Summarize key points and next steps.",
    "check_in": "Friendly check-in to maintain relationship. No specific ask, just nurturing.",
    "re_engagement": "Re-engage a dormant lead who went cold. New angle or offer.",
    "breakup": "Final attempt before closing the lead. Direct, respectful, no hard feelings.",
}


async def generate_email_template(lead_id: str, email_type: str, db: AsyncSession) -> dict:
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalars().first()
    if not lead:
        return {"error": f"Lead {lead_id} not found"}

    if email_type not in EMAIL_TYPE_CONTEXTS:
        return {"error": f"Unknown email_type '{email_type}'. Valid: {list(EMAIL_TYPE_CONTEXTS.keys())}"}

    context_description = EMAIL_TYPE_CONTEXTS[email_type]

    try:
        client, api_key = await get_llm_client(SCORING_MODEL, db=db)
        lead_context = {
            "contact_name": lead.contact_name or "there",
            "company_name": lead.company_name or "your company",
            "title": lead.title,
            "industry": "technology",
            "stage": lead.stage,
            "estimated_value": lead.estimated_value or 0,
        }
        prompt = (
            f"Generate a personalized {email_type} email for this sales lead.\n"
            f"Context: {context_description}\n\n"
            "Lead:\n" + json.dumps(lead_context, indent=2) + "\n\n"
            "Incorporate the company name and contact name. Keep it warm and professional.\n"
            "Return ONLY valid JSON with:\n"
            '{"subject": "<subject line>", "body": "<plain text body>", "body_html": "<HTML body with p/strong tags>", '
            '"suggested_send_time": "<best time to send, e.g. Tuesday 10am>"}'
        )
        response = await client.chat.completions.create(
            model=SCORING_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
        )
        text = response.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        llm_result = json.loads(text)
    except Exception as e:
        logger.warning(f"LLM email generation failed: {e}")
        name = lead.contact_name or "there"
        company = lead.company_name or "your company"
        llm_result = {
            "subject": f"Let's connect: {lead.title}",
            "body": f"Hi {name},\n\nI wanted to reach out regarding {lead.title} at {company}. Let me know if you'd like to discuss further.\n\nBest regards",
            "body_html": f"<p>Hi {name},</p><p>I wanted to reach out regarding <strong>{lead.title}</strong> at {company}. Let me know if you'd like to discuss further.</p><p>Best regards</p>",
            "suggested_send_time": "Tuesday 10:00 AM",
        }

    return {
        "lead_id": lead_id,
        "email_type": email_type,
        "subject": llm_result.get("subject", ""),
        "body": llm_result.get("body", ""),
        "body_html": llm_result.get("body_html", ""),
        "suggested_send_time": llm_result.get("suggested_send_time", "Weekday morning"),
    }


async def analyze_sales_conversation(transcript: str, deal_context: str = "") -> dict:
    try:
        client, api_key = await get_llm_client(SCORING_MODEL, db=None)
        prompt = (
            "Analyze this sales conversation transcript and extract key insights.\n\n"
            f"Deal Context: {deal_context or 'Not provided'}\n\n"
            f"Transcript:\n{transcript}\n\n"
            "Return ONLY valid JSON with:\n"
            '{"sentiment": "<positive|neutral|negative>", '
            '"buying_signals": ["<signal1>", ...], '
            '"objections": ["<objection1>", ...], '
            '"decision_criteria": ["<criteria1>", ...], '
            '"timeline": "<stated timeline or null>", '
            '"budget_indicators": "<budget discussion summary or null>", '
            '"competitors_mentioned": ["<competitor1>", ...], '
            '"next_action_recommendations": [{"action": "<action>", "rationale": "<why>"}, ...]'
            '}'
        )
        response = await client.chat.completions.create(
            model=SCORING_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        text = response.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        return json.loads(text)
    except Exception as e:
        logger.error(f"Conversation analysis failed: {e}")
        return {
            "sentiment": "neutral",
            "buying_signals": [],
            "objections": [],
            "decision_criteria": [],
            "timeline": None,
            "budget_indicators": None,
            "competitors_mentioned": [],
            "next_action_recommendations": [],
            "error": str(e),
        }
