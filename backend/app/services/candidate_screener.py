"""
candidate_screener.py — AI-powered resume parsing and candidate screening.

Parses resume text into structured candidate profiles and scores candidates
against job requirements using the existing LLM cascade.
"""
import json
import logging
from typing import Optional
from pydantic import BaseModel

from app.services.agent_executor import _call_llm_cascade
from app.services.llm_router import get_llm_client

logger = logging.getLogger("successcore.candidate_screener")

RESUME_PARSE_PROMPT = """Extract structured candidate information from the following resume text.
Return ONLY valid JSON with these fields:
- full_name: string
- email: string (leave empty if not found)
- phone: string (leave empty if not found)
- location: string (city, country)
- years_experience: integer (total years of professional experience)
- current_role: string (most recent job title)
- current_company: string (most recent employer)
- education: list of {degree: string, institution: string, year: integer}
- skills: list of strings (technical and soft skills)
- languages: list of strings
- linkedin_url: string (leave empty if not found)
- summary: string (2-3 sentence professional summary)

Resume text:
{resume_text}

JSON:"""

SCORE_PROMPT = """Score this candidate against the job requirements on a scale of 0-100.

Job Title: {job_title}
Job Requirements: {requirements}

Candidate Profile:
{profile}

Return ONLY valid JSON with:
- overall_score: integer (0-100)
- skill_match: integer (0-100)
- experience_match: integer (0-100)
- education_match: integer (0-100)
- strengths: list of strings (top 3 matching strengths)
- gaps: list of strings (top 3 skill/experience gaps)
- recommendation: string ("strong_hire" | "hire" | "maybe" | "pass")
- reasoning: string (2-3 sentence explanation)

JSON:"""


INTERVIEW_QUESTIONS_PROMPT = """Generate between 5 and 8 tailored interview questions for this candidate and job.

Job Requirements:
{job_requirements}

Candidate Profile:
{profile}

Return ONLY valid JSON with:
- questions: list of objects, each with:
  - question: string (the interview question)
  - category: string ("technical" | "behavioral" | "situational")
  - rationale: string (1 sentence explaining why this question fits this candidate)

JSON:"""


class ParsedResume(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    years_experience: int = 0
    current_role: str = ""
    current_company: str = ""
    education: list = []
    skills: list[str] = []
    languages: list[str] = []
    linkedin_url: str = ""
    summary: str = ""


class CandidateScore(BaseModel):
    overall_score: int = 0
    skill_match: int = 0
    experience_match: int = 0
    education_match: int = 0
    strengths: list[str] = []
    gaps: list[str] = []
    recommendation: str = "maybe"
    reasoning: str = ""


async def parse_resume(resume_text: str, model: str = "gpt-4o-mini") -> Optional[ParsedResume]:
    """Parse a resume into structured candidate data using LLM."""
    if not resume_text or len(resume_text.strip()) < 50:
        return None

    prompt = RESUME_PARSE_PROMPT.format(resume_text=resume_text[:8000])

    try:
        response = await _call_llm_cascade(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            temperature=0.1,
            max_tokens=1500,
        )
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        data = json.loads(response)
        return ParsedResume(**data)
    except Exception as e:
        logger.error(f"Resume parsing failed: {e}")
        return None


async def score_candidate(
    candidate_profile: dict,
    job_title: str,
    requirements: str,
    model: str = "gpt-4o-mini",
) -> Optional[CandidateScore]:
    """Score a candidate against job requirements."""
    profile_str = json.dumps(candidate_profile, indent=2)
    prompt = SCORE_PROMPT.format(
        job_title=job_title,
        requirements=requirements[:2000],
        profile=profile_str[:4000],
    )

    try:
        response = await _call_llm_cascade(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            temperature=0.2,
            max_tokens=1000,
        )
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        data = json.loads(response)
        return CandidateScore(**data)
    except Exception as e:
        logger.error(f"Candidate scoring failed: {e}")
        return None


async def screen_candidate(
    resume_text: str,
    job_title: str,
    requirements: str,
    model: str = "gpt-4o-mini",
) -> dict:
    """Full pipeline: parse resume + score against job requirements."""
    parsed = await parse_resume(resume_text, model)
    if not parsed:
        return {"error": "Failed to parse resume", "parsed": None, "score": None}

    score = await score_candidate(parsed.model_dump(), job_title, requirements, model)
    return {
        "parsed": parsed.model_dump(),
        "score": score.model_dump() if score else None,
    }


async def screen_resume_full(
    content: bytes,
    filename: str,
    job_id: str = "",
    db=None,
    model: str = "gpt-4o-mini",
) -> dict:
    """
    Full resume screening pipeline: extract text, parse, score against job.
    This is the function called by the existing POST /candidates/screen endpoint.
    """
    # file_parser expone parse_file_content(filename, content) — resuelve la extensión internamente
    from app.services.file_parser import parse_file_content

    resume_text = await parse_file_content(filename, content)

    if not resume_text or len(resume_text.strip()) < 50:
        raise ValueError("Could not extract sufficient text from the resume file.")

    requirements = ""
    job_title = ""
    if db and job_id:
        try:
            from sqlalchemy import select
            from app.models.hire import JobPosting
            result = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
            job = result.scalar_one_or_none()
            if job:
                job_title = job.title or ""
                requirements = job.description or ""
        except Exception:
            pass

    parsed = await parse_resume(resume_text, model)
    if not parsed:
        raise ValueError("Failed to parse resume content.")

    score = None
    if job_title and requirements:
        score = await score_candidate(parsed.model_dump(), job_title, requirements, model)

    return {
        "parsed": parsed.model_dump(),
        "score": score.model_dump() if score else None,
        "job_title": job_title,
        "word_count": len(resume_text.split()),
    }


async def batch_screen_resumes(files: list[dict], job_id: str, db=None, model: str = "gpt-4o-mini") -> list[dict]:
    """Batch screen multiple resumes against a job and return ranked reports."""
    results = []
    for f in files:
        try:
            content = f.get("content", b"")
            filename = f.get("filename", "resume.pdf")
            res = await screen_resume_full(content, filename, job_id, db, model)
            # Accommodate expected test format
            if "score" in res and res["score"]:
                res["overall_score"] = res["score"].get("overall_score", 0)
            else:
                res["overall_score"] = res.get("overall_score", 0)
            res["success"] = True
            results.append(res)
        except Exception as e:
            results.append({"success": False, "error": str(e), "overall_score": 0})
    
    # Sort by overall_score descending
    results.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
    
    # Add rank
    for i, res in enumerate(results):
        res["rank"] = i + 1
        
    return results


async def rank_candidates(
    candidate_ids: list,
    job_id: str,
    db=None,
    model: str = "gpt-4o-mini",
) -> list:
    """
    Puntúa y clasifica varios candidatos existentes frente a una oferta de trabajo.

    Devuelve una lista ordenada (mejor puntuación primero) con sub-puntuaciones,
    fortalezas, carencias y recomendación por candidato. Si la oferta o los
    candidatos no existen, devuelve [{"error": ...}] para que el llamador lo gestione.
    """
    from sqlalchemy import select
    from app.models.hire import Candidate, JobPosting

    if db is None:
        return [{"error": "Se requiere una sesión de base de datos para clasificar candidatos"}]

    job_res = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
    job = job_res.scalar_one_or_none()
    if not job:
        return [{"error": f"Oferta de trabajo '{job_id}' no encontrada"}]

    cand_res = await db.execute(select(Candidate).where(Candidate.id.in_(candidate_ids)))
    candidates = cand_res.scalars().all()
    if not candidates:
        return [{"error": "No se encontró ningún candidato con los IDs proporcionados"}]

    job_title = job.title or ""
    requirements = job.description or ""

    ranked = []
    for candidate in candidates:
        profile = {
            "first_name": candidate.first_name,
            "last_name": candidate.last_name,
            "email": candidate.email,
            "phone": candidate.phone,
            "notes": candidate.notes,
            "stage": candidate.stage,
        }
        score = await score_candidate(profile, job_title, requirements, model)
        entry = {
            "candidate_id": candidate.id,
            "candidate_name": f"{candidate.first_name or ''} {candidate.last_name or ''}".strip(),
            "email": candidate.email,
            "stage": candidate.stage,
        }
        if score:
            entry.update(score.model_dump())
            entry["scoring_failed"] = False
        else:
            # Degradación honesta: sin puntuación LLM el candidato queda a 0 y marcado
            entry.update(CandidateScore(reasoning="No se pudo generar la puntuación con el LLM").model_dump())
            entry["scoring_failed"] = True
        ranked.append(entry)

    ranked.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
    for i, entry in enumerate(ranked):
        entry["rank"] = i + 1

    return ranked


async def generate_interview_questions(
    candidate_profile: dict,
    job_requirements: str,
    model: str = "gpt-4o-mini",
) -> list:
    """
    Genera 5-8 preguntas de entrevista personalizadas según el perfil del
    candidato y los requisitos del puesto. Devuelve una lista de objetos
    {question, category, rationale}. Lanza ValueError si el LLM no devuelve
    una lista válida.
    """
    profile_str = json.dumps(candidate_profile, indent=2, ensure_ascii=False, default=str)
    prompt = INTERVIEW_QUESTIONS_PROMPT.format(
        job_requirements=(job_requirements or "")[:2000],
        profile=profile_str[:4000],
    )

    response = await _call_llm_cascade(
        messages=[{"role": "user", "content": prompt}],
        model=model,
        temperature=0.4,
        max_tokens=1200,
    )
    response = response.strip()
    if response.startswith("```"):
        response = response.split("```")[1]
        if response.startswith("json"):
            response = response[4:]

    try:
        data = json.loads(response)
    except json.JSONDecodeError as e:
        logger.error(f"Interview question generation returned invalid JSON: {e}")
        raise ValueError("El LLM no devolvió JSON válido al generar preguntas de entrevista")

    questions = data.get("questions", []) if isinstance(data, dict) else data
    if not isinstance(questions, list) or not questions:
        raise ValueError("El LLM no devolvió una lista válida de preguntas de entrevista")

    return questions


async def _get_job_requirements(job_id: str, db) -> str:
    """Helper to fetch job requirements for offer letters."""
    from sqlalchemy import select
    from app.models.hire import JobPosting
    if not db or not job_id:
        return ""
    try:
        result = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
        job = result.scalar_one_or_none()
        if job:
            return f"Title: {job.title}\nDescription: {job.description or ''}"
    except Exception:
        pass
    return ""


async def generate_personalized_offer_letter(
    candidate_id: str, job_id: str, salary: float, start_date: str, template: str, db
) -> dict:
    """Generate a personalized offer letter using LLMs."""
    from sqlalchemy import select
    from app.models.hire import Candidate
    
    cand_res = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = cand_res.scalar_one_or_none()
    if not candidate:
        raise ValueError("Candidate not found")
        
    requirements = await _get_job_requirements(job_id, db)
    
    prompt = f"""Generate a personalized offer letter for the following candidate.
Candidate: {candidate.first_name} {candidate.last_name}
Salary: {salary}
Start Date: {start_date}
Job Requirements: {requirements}
Template Guidelines: {template}

Return ONLY valid JSON with:
- offer_letter: string (the full text of the personalized offer letter)
JSON:"""

    client, _ = await get_llm_client("gpt-4o-mini", None, db)
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    data = json.loads(raw)
    
    return {"offer_letter_text": data.get("offer_letter", "")}

