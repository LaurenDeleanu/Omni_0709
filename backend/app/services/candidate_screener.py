import json
import logging
from typing import Optional, List

from app.services.file_parser import parse_file_content as _parse_file
from app.services.llm_router import get_llm_client

logger = logging.getLogger(__name__)

SCORING_SYSTEM = """You are an expert recruitment evaluator and AI hiring specialist. You will receive a candidate's resume text and a job description with requirements.
Analyze the candidate thoroughly and score them against the job on a 0-100 scale with detailed sub-scores.

Return ONLY valid JSON with this structure:
{
  "overall_score": number (0-100),
  "skill_match": number (0-100),
  "experience_match": number (0-100),
  "education_match": number (0-100),
  "culture_fit": number (0-100),
  "technical_skills": ["string"],
  "soft_skills": ["string"],
  "years_experience": number or null,
  "education_level": "high_school" or "associate" or "bachelor" or "master" or "phd" or "other",
  "certifications": ["string"],
  "languages": ["string"],
  "matching_skills": ["string"],
  "missing_skills": ["string"],
  "strengths": ["string"],
  "weaknesses": ["string"],
  "summary": "2-3 sentence professional summary of the candidate",
  "recommendation": "strong_hire" or "hire" or "consider" or "pass",
  "explanation": "detailed explanation of how each sub-score was determined and overall fit assessment"
}

Scoring guidelines:
- skill_match: how well the candidate's technical and soft skills align with required and preferred qualifications
- experience_match: relevance and depth of work experience compared to job requirements
- education_match: how well the candidate's education level and field match the role
- culture_fit: inferred from resume language, career progression, values indicators, and work style
- overall_score: weighted composite (skill_match * 0.40 + experience_match * 0.30 + education_match * 0.15 + culture_fit * 0.15)
- Return ONLY the JSON object, no markdown fences, no extra text."""

BIAS_DETECTION_SYSTEM = """You are an expert in ethical hiring practices and bias detection. Analyze the provided resume text for potentially biased language or patterns that could indicate discrimination.

Return ONLY valid JSON with this structure:
{
  "has_biased_content": true or false,
  "overall_risk": "low" or "medium" or "high",
  "flags": {
    "gendered_language": {
      "detected": true or false,
      "examples": ["string"],
      "explanation": "string"
    },
    "age_indicators": {
      "detected": true or false,
      "examples": ["string"],
      "explanation": "string"
    },
    "ethnic_indicators": {
      "detected": true or false,
      "examples": ["string"],
      "explanation": "string"
    },
    "disability_indicators": {
      "detected": true or false,
      "examples": ["string"],
      "explanation": "string"
    },
    "other_concerns": {
      "detected": true or false,
      "examples": ["string"],
      "explanation": "string"
    }
  },
  "suggestions": ["string"],
  "summary": "string"
}

Rules:
- Gendered language: words like "aggressive", "nurturing", "chairman", "guys", "girl", etc. that imply gender
- Age indicators: graduation years, phrases like "over 20 years", "young and energetic", etc.
- Ethnic indicators: references to nationality, ethnic background unless directly job-relevant
- Disability indicators: mentions of health conditions, accommodations requested
- Suggestions should provide alternative neutral phrasing
- Return ONLY the JSON object, no markdown fences, no extra text."""

INTERVIEW_QUESTIONS_SYSTEM = """You are an expert interviewer and talent assessment specialist. Based on a candidate's profile and a job's requirements, generate tailored interview questions.

Return ONLY valid JSON with this structure:
{
  "questions": [
    {
      "text": "string (the actual question)",
      "category": "technical" or "behavioral" or "situational" or "cultural",
      "target_skill": "string (specific skill this question assesses)",
      "difficulty": "easy" or "medium" or "hard",
      "suggested_answer_key_points": ["string"],
      "rationale": "string (why this question is being asked for this candidate)"
    }
  ]
}

Guidelines:
- Generate 5-8 questions total
- Mix of categories: at least 2 technical, 2 behavioral, 1 situational, 1 cultural
- Target the candidate's specific strengths and weaknesses vs the job requirements
- Technical questions should probe depth in skills the candidate claims
- Behavioral questions should explore past experiences relevant to the role
- Situational questions should test problem-solving for role-specific scenarios
- Cultural questions should assess team fit and values alignment
- suggested_answer_key_points should have 2-4 bullet points of what a good answer looks like
- Return ONLY the JSON object, no markdown fences, no extra text."""


async def _call_llm(system_prompt: str, user_message: str, model: str = "gpt-4o-mini", temperature: float = 0.1) -> dict:
    client, _ = await get_llm_client(model)
    response = await client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    if raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(f"LLM returned non-JSON. Raw: {raw[:500]}")
        return {"error": "Failed to parse LLM response as JSON", "raw_response": raw[:1000]}


async def score_candidate(resume_text: str, job_requirements: str, db=None, model: str = "gpt-4o-mini") -> dict:
    user_message = f"RESUME:\n{resume_text[:15000]}\n\nJOB REQUIREMENTS:\n{job_requirements[:8000]}"
    result = await _call_llm(SCORING_SYSTEM, user_message, model=model)
    if "error" in result:
        return result
    result.setdefault("overall_score", 0)
    result.setdefault("skill_match", 0)
    result.setdefault("experience_match", 0)
    result.setdefault("education_match", 0)
    result.setdefault("culture_fit", 0)
    result.setdefault("technical_skills", [])
    result.setdefault("soft_skills", [])
    result.setdefault("years_experience", None)
    result.setdefault("education_level", "other")
    result.setdefault("certifications", [])
    result.setdefault("languages", [])
    result.setdefault("matching_skills", [])
    result.setdefault("missing_skills", [])
    result.setdefault("strengths", [])
    result.setdefault("weaknesses", [])
    result.setdefault("summary", "")
    result.setdefault("recommendation", "consider")
    result.setdefault("explanation", "")
    return result


async def detect_bias(resume_text: str, model: str = "gpt-4o-mini") -> dict:
    result = await _call_llm(BIAS_DETECTION_SYSTEM, resume_text[:15000], model=model, temperature=0.0)
    if "error" in result:
        return result
    result.setdefault("has_biased_content", False)
    result.setdefault("overall_risk", "low")
    result.setdefault("flags", {})
    result.setdefault("suggestions", [])
    result.setdefault("summary", "")
    return result


async def generate_interview_questions(candidate_profile: dict, job_requirements: str, model: str = "gpt-4o-mini") -> list:
    user_message = f"CANDIDATE PROFILE:\n{json.dumps(candidate_profile, ensure_ascii=False, indent=2)}\n\nJOB REQUIREMENTS:\n{job_requirements[:8000]}"
    result = await _call_llm(INTERVIEW_QUESTIONS_SYSTEM, user_message, model=model, temperature=0.4)
    if "error" in result:
        return result
    questions = result.get("questions", [])
    for q in questions:
        q.setdefault("text", "")
        q.setdefault("category", "behavioral")
        q.setdefault("target_skill", "")
        q.setdefault("difficulty", "medium")
        q.setdefault("suggested_answer_key_points", [])
        q.setdefault("rationale", "")
    return questions


async def _get_job_requirements(db, job_id: str) -> str:
    from sqlalchemy import select
    from app.models.hire import JobPosting
    result = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        return ""
    parts = []
    if job.title:
        parts.append(f"Title: {job.title}")
    if job.department:
        parts.append(f"Department: {job.department}")
    if job.location:
        parts.append(f"Location: {job.location}")
    if job.employment_type:
        parts.append(f"Type: {job.employment_type}")
    if job.description:
        parts.append(f"Description: {job.description}")
    return "\n".join(parts)


async def rank_candidates(candidate_ids: list[str], job_id: str, db, model: str = "gpt-4o-mini") -> list:
    from sqlalchemy import select
    from app.models.hire import Candidate
    from app.services.resume_parser import parse_resume

    if not candidate_ids:
        return []

    job_requirements = await _get_job_requirements(db, job_id)
    if not job_requirements:
        return [{"error": f"Job {job_id} not found"}]

    candidates_data = []
    for cid in candidate_ids:
        result = await db.execute(select(Candidate).where(Candidate.id == cid))
        candidate = result.scalar_one_or_none()
        if candidate:
            candidates_data.append({
                "id": candidate.id,
                "first_name": candidate.first_name,
                "last_name": candidate.last_name,
                "email": candidate.email,
                "phone": candidate.phone,
                "resume_url": candidate.resume_url,
                "current_stage": candidate.stage,
                "score": None,
                "profile": None,
                "explanation": None,
            })

    if not candidates_data:
        return []

    batch_size = 5
    for i in range(0, len(candidates_data), batch_size):
        batch = candidates_data[i:i + batch_size]
        for candidate in batch:
            resume_text = ""
            if candidate["resume_url"]:
                try:
                    import os
                    if os.path.isfile(candidate["resume_url"]):
                        with open(candidate["resume_url"], "rb") as f:
                            content = f.read()
                        if content:
                            filename = os.path.basename(candidate["resume_url"])
                            resume_text = await _parse_file(filename, content)
                except Exception as e:
                    logger.warning(f"Could not parse resume for candidate {candidate['id']}: {e}")
                    resume_text = f"Candidate: {candidate['first_name']} {candidate['last_name']}, Email: {candidate['email']}"

            if not resume_text or len(resume_text.strip()) < 10:
                resume_text = f"Candidate: {candidate['first_name']} {candidate['last_name']}, Email: {candidate['email']}, Current Stage: {candidate['current_stage']}"

            scoring = await score_candidate(resume_text, job_requirements, db=db, model=model)
            if "error" not in scoring:
                candidate["score"] = scoring.get("overall_score", 0)
                candidate["profile"] = {
                    "technical_skills": scoring.get("technical_skills", []),
                    "soft_skills": scoring.get("soft_skills", []),
                    "years_experience": scoring.get("years_experience"),
                    "education_level": scoring.get("education_level"),
                    "certifications": scoring.get("certifications", []),
                    "languages": scoring.get("languages", []),
                    "summary": scoring.get("summary", ""),
                    "recommendation": scoring.get("recommendation", "consider"),
                    "matching_skills": scoring.get("matching_skills", []),
                    "missing_skills": scoring.get("missing_skills", []),
                    "strengths": scoring.get("strengths", []),
                    "weaknesses": scoring.get("weaknesses", []),
                    "sub_scores": {
                        "skill_match": scoring.get("skill_match", 0),
                        "experience_match": scoring.get("experience_match", 0),
                        "education_match": scoring.get("education_match", 0),
                        "culture_fit": scoring.get("culture_fit", 0),
                    }
                }
                candidate["explanation"] = scoring.get("explanation", "")
            else:
                candidate["score"] = 0
                candidate["explanation"] = scoring.get("error", "Scoring failed")

        batch.sort(key=lambda c: c["score"] or 0, reverse=True)

    candidates_data.sort(key=lambda c: c["score"] or 0, reverse=True)
    for idx, c in enumerate(candidates_data):
        c["rank"] = idx + 1

    return candidates_data


async def screen_resume_full(file_content: bytes, filename: str, job_id: Optional[str] = None, db=None, model: str = "gpt-4o-mini") -> dict:
    import os
    import tempfile
    import uuid as _uuid

    tmpdir = os.path.join(tempfile.gettempdir(), "resume_screening")
    os.makedirs(tmpdir, exist_ok=True)
    tmp_path = os.path.join(tmpdir, f"{_uuid.uuid4().hex}_{filename}")

    try:
        with open(tmp_path, "wb") as f:
            f.write(file_content)

        if len(file_content) == 0:
            return {"success": False, "error": "Resume file is empty"}

        try:
            resume_text = await _parse_file(filename, file_content)
        except Exception as e:
            logger.error(f"Failed to parse resume file {filename}: {e}")
            return {"success": False, "error": f"Could not extract text from resume: {e}"}

        if not resume_text or len(resume_text.strip()) < 10:
            return {"success": False, "error": "Resume contains insufficient text content for parsing"}

        job_requirements = ""
        job_title = None
        if job_id and db:
            job_requirements = await _get_job_requirements(db, job_id)
            if job_requirements:
                from sqlalchemy import select
                from app.models.hire import JobPosting
                result = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
                job = result.scalar_one_or_none()
                if job:
                    job_title = job.title

        scoring = await score_candidate(resume_text, job_requirements, db=db, model=model)
        if "error" in scoring:
            return {"success": False, "error": scoring.get("error", "Scoring step failed"), "raw_response": scoring.get("raw_response")}

        bias_report = await detect_bias(resume_text, model=model)

        candidate_profile = {
            "technical_skills": scoring.get("technical_skills", []),
            "soft_skills": scoring.get("soft_skills", []),
            "years_experience": scoring.get("years_experience"),
            "education_level": scoring.get("education_level"),
            "certifications": scoring.get("certifications", []),
            "languages": scoring.get("languages", []),
            "summary": scoring.get("summary", ""),
            "strengths": scoring.get("strengths", []),
            "weaknesses": scoring.get("weaknesses", []),
        }

        interview_questions = []
        if job_requirements:
            interview_qs = await generate_interview_questions(candidate_profile, job_requirements, model=model)
            if isinstance(interview_qs, list):
                interview_questions = interview_qs
            elif isinstance(interview_qs, dict) and "error" in interview_qs:
                interview_questions = []

        return {
            "success": True,
            "source_file": filename,
            "job_title": job_title,
            "job_id": job_id,
            "overall_score": scoring.get("overall_score", 0),
            "recommendation": scoring.get("recommendation", "consider"),
            "sub_scores": {
                "skill_match": scoring.get("skill_match", 0),
                "experience_match": scoring.get("experience_match", 0),
                "education_match": scoring.get("education_match", 0),
                "culture_fit": scoring.get("culture_fit", 0),
            },
            "profile": candidate_profile,
            "matching_skills": scoring.get("matching_skills", []),
            "missing_skills": scoring.get("missing_skills", []),
            "explanation": scoring.get("explanation", ""),
            "bias_report": bias_report,
            "interview_questions": interview_questions,
        }
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


async def batch_screen_resumes(
    files: List[dict],
    job_id: str,
    db,
    model: str = "gpt-4o-mini"
) -> List[dict]:
    """
    Screens multiple resume files concurrently and returns them sorted by overall score.
    """
    import asyncio
    
    async def screen_one(f_dict: dict) -> dict:
        filename = f_dict.get("filename", "resume.pdf")
        content = f_dict.get("content", b"")
        try:
            report = await screen_resume_full(content, filename, job_id, db, model)
            return report
        except Exception as e:
            logger.error(f"Error screening resume in batch: {e}")
            return {
                "success": False,
                "source_file": filename,
                "error": str(e)
            }
            
    tasks = [screen_one(f) for f in files]
    results = await asyncio.gather(*tasks)
    
    # Sort successful ones by score, failed ones at the end
    succeeded = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]
    
    succeeded.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
    
    # Update ranks
    for idx, r in enumerate(succeeded):
        r["rank"] = idx + 1
        
    return succeeded + failed


async def generate_personalized_offer_letter(
    candidate_id: str,
    job_id: str,
    salary: float,
    start_date: str,
    template: str,
    db,
    model: str = "gpt-4o-mini"
) -> dict:
    """
    Generates a personalized offer letter using LLM based on candidate's screening profile and job description.
    """
    from sqlalchemy import select
    from app.models.hire import Candidate
    
    cand_res = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = cand_res.scalar_one_or_none()
    
    job_reqs = await _get_job_requirements(db, job_id)
    
    if not candidate:
        return {"error": "Candidate not found"}
        
    # Get parsed resume text or mock one if not available
    resume_text = candidate.notes or ""
    if candidate.resume_url:
        try:
            import os
            if os.path.isfile(candidate.resume_url):
                with open(candidate.resume_url, "rb") as f:
                    content = f.read()
                filename = os.path.basename(candidate.resume_url)
                resume_text = await _parse_file(filename, content)
        except Exception:
            pass
            
    if not resume_text:
        resume_text = f"Candidate: {candidate.first_name} {candidate.last_name}, Stage: {candidate.stage}"
        
    # Standard personalized offer prompt
    prompt = (
        "You are an expert HR copywriter. You are given a candidate's background, job requirements, "
        "offered salary, start date, and a basic offer letter template.\n"
        "Generate a highly professional, welcoming, and personalized offer letter in Spanish. "
        "Incorporate a custom paragraph highlighting the candidate's unique strengths and why the team "
        "is excited to have them join based on their resume profile.\n\n"
        f"Candidate Name: {candidate.first_name} {candidate.last_name}\n"
        f"Job details:\n{job_reqs}\n"
        f"Salary: {salary} EUR\n"
        f"Start Date: {start_date}\n\n"
        f"Base Template:\n{template}\n\n"
        "Return the personalized offer letter text inside a JSON object with a single key:\n"
        "{\"offer_letter\": \"personalized letter text...\"}"
    )
    
    client, _ = await get_llm_client(model)
    try:
        response = await client.chat.completions.create(
            model=model,
            temperature=0.3,
            messages=[
                {"role": "system", "content": "HR Personalization assistant. Return ONLY a JSON object."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        raw_res = response.choices[0].message.content or "{}"
        res_data = json.loads(raw_res.strip())
        offer_text = res_data.get("offer_letter", template)
        return {
            "candidate_id": candidate_id,
            "job_id": job_id,
            "salary": salary,
            "start_date": start_date,
            "offer_letter_text": offer_text
        }
    except Exception as e:
        logger.error(f"Failed to generate offer letter: {e}")
        return {"error": f"Failed to generate offer letter: {str(e)}"}

