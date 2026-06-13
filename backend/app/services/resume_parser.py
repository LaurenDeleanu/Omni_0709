import json
import logging
import os
from typing import Optional

from app.services.file_parser import parse_file_content as _parse_file
from app.services.llm_router import get_llm_client

logger = logging.getLogger(__name__)

RESUME_EXTRACTION_SYSTEM = """You are an expert resume parser. Extract structured candidate information from the provided resume text.
Return ONLY valid JSON with these fields (use null/empty for missing data):
{
  "first_name": "string",
  "last_name": "string",
  "email": "string",
  "phone": "string",
  "skills": ["string"],
  "years_experience": number or null,
  "education": [{"degree": "string", "school": "string", "year": number or null}],
  "languages": ["string"],
  "current_title": "string or null",
  "current_company": "string or null",
  "linkedin_url": "string or null",
  "summary": "string or null"
}

Rules:
- Extract names exactly as they appear in the resume. Capitalize properly.
- Email should match a valid email pattern. If not found, set to null.
- Phone should include country code if present.
- Skills should be a flat list of individual skills (max 15).
- years_experience should be a number representing total years of professional experience. If unclear, estimate from work history.
- education is an array of {degree, school, year} objects. Include only formal education.
- languages is an array of language names the candidate speaks.
- summary should be a 1-2 sentence professional summary based on the resume content.
- Return ONLY the JSON object, no markdown fences, no extra text."""

CANDIDATE_MATCH_SYSTEM = """You are an expert recruitment evaluator. You will receive a candidate's parsed resume data and a job's requirements.
Score how well the candidate fits the job on a scale of 0-100. Identify which required skills the candidate has and which are missing.
Return ONLY valid JSON with this structure:
{
  "fit_score": number (0-100),
  "matching_skills": ["string"],
  "missing_skills": ["string"],
  "summary": "string",
  "recommendation": "shortlist" or "consider" or "pass"
}"""


async def parse_resume(file_path: str, model: str = "gpt-4o-mini") -> dict:
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Resume file not found: {file_path}")

    filename = os.path.basename(file_path)
    with open(file_path, "rb") as f:
        content = f.read()

    if len(content) == 0:
        raise ValueError("Resume file is empty")

    try:
        text = await _parse_file(filename, content)
    except Exception as e:
        logger.error(f"Failed to parse resume file {filename}: {e}")
        raise ValueError(f"Could not extract text from resume: {e}")

    if not text or len(text.strip()) < 10:
        raise ValueError("Resume contains insufficient text content for parsing")

    client, _ = await get_llm_client(model)
    response = await client.chat.completions.create(
        model=model,
        temperature=0.1,
        messages=[
            {"role": "system", "content": RESUME_EXTRACTION_SYSTEM},
            {"role": "user", "content": text[:12000]},
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
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(f"LLM returned non-JSON for resume parse. Raw: {raw[:500]}")
        return {
            "error": "Failed to parse LLM response as JSON",
            "raw_text": text[:2000],
            "llm_response": raw[:1000]
        }

    parsed.setdefault("first_name", None)
    parsed.setdefault("last_name", None)
    parsed.setdefault("email", None)
    parsed.setdefault("phone", None)
    parsed.setdefault("skills", [])
    parsed.setdefault("years_experience", None)
    parsed.setdefault("education", [])
    parsed.setdefault("languages", [])
    parsed.setdefault("current_title", None)
    parsed.setdefault("current_company", None)
    parsed.setdefault("linkedin_url", None)
    parsed.setdefault("summary", None)

    return {
        "success": True,
        "candidate": parsed,
        "source_file": filename
    }


async def match_candidate_to_job(
    candidate_data: dict,
    job_requirements: str,
    model: str = "gpt-4o-mini"
) -> dict:
    candidate_str = json.dumps(candidate_data, ensure_ascii=False, indent=2)

    client, _ = await get_llm_client(model)
    response = await client.chat.completions.create(
        model=model,
        temperature=0.1,
        messages=[
            {"role": "system", "content": CANDIDATE_MATCH_SYSTEM},
            {"role": "user", "content": f"CANDIDATE DATA:\n{candidate_str}\n\nJOB REQUIREMENTS:\n{job_requirements}"},
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
        result = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(f"LLM returned non-JSON for candidate match. Raw: {raw[:500]}")
        return {"error": "Failed to parse match result as JSON", "llm_response": raw[:1000]}

    return {"success": True, "match": result}


async def screen_resume(
    file_content: bytes,
    filename: str,
    job_id: Optional[str] = None,
    model: str = "gpt-4o-mini"
) -> dict:
    import tempfile
    import uuid as _uuid

    tmpdir = os.path.join(tempfile.gettempdir(), "resume_screening")
    os.makedirs(tmpdir, exist_ok=True)
    tmp_path = os.path.join(tmpdir, f"{_uuid.uuid4().hex}_{filename}")

    try:
        with open(tmp_path, "wb") as f:
            f.write(file_content)

        parse_result = await parse_resume(tmp_path, model=model)

        if not parse_result.get("success"):
            return parse_result

        return {
            "success": True,
            "candidate": parse_result["candidate"],
            "source_file": filename,
        }
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
