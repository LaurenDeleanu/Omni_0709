import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger("successcore.nlq")

DATABASE_SCHEMA_SUMMARY = """
Tables available:
- users(id, email, full_name, department, role, is_active, base_salary, hire_date, country, vacation_allowance)
- expense_claims(id, user_id, amount, category, status, description, created_at)
- time_logs(id, user_id, clock_in, clock_out, total_hours)
- vacation_requests(id, user_id, start_date, end_date, status, days_requested)
- course_enrollments(id, user_id, course_id, status, enrolled_at, completed_at)
- hire_candidates(id, name, stage, job_id, applied_at)
- hire_jobs(id, title, department, status, created_at)
- pay_payslips(id, cycle_id, employee_id, gross_salary, net_salary, status)
- kudos(id, sender_id, receiver_id, sender_name, receiver_name, message, created_at)
- notifications(id, user_id, title, message, type, is_read, created_at)
- agent_execution_runs(id, agent_id, status, cost_usd, latency_ms, created_at)
"""


async def text_to_sql_query(db: AsyncSession, question: str, model: str = "gpt-4o-mini") -> dict:
    from app.services.llm_router import get_llm_client
    from app.core.retry import async_retry

    system_prompt = (
        f"Eres un generador de SQL experto. A partir de la pregunta del usuario en lenguaje natural, "
        f"genera una consulta SQL SELECT valida para PostgreSQL basada en el siguiente esquema:\n\n"
        f"{DATABASE_SCHEMA_SUMMARY}\n\n"
        f"Reglas:\n"
        f"- Solo genera SELECT, nunca INSERT/UPDATE/DELETE/DDL\n"
        f"- Usa LIMIT 50 por defecto si no se especifica\n"
        f"- Usa COALESCE para manejar NULLs\n"
        f"- Siempre incluye un alias descriptivo\n"
        f"- Responde con JSON: {{\"sql\": \"...\", \"explanation\": \"...\"}}"
    )

    try:
        client, _ = await get_llm_client(model, db=db)
        response = await client.chat.completions.create(
            model=model,
            temperature=0.0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Question: {question}"},
            ]
        )

        raw = response.choices[0].message.content.strip() if response.choices else "{}"
        import json
        clean = raw
        if "{" in clean and "}" in clean:
            clean = clean[clean.find("{"):clean.rfind("}")+1]
        result = json.loads(clean)
        generated_sql = result.get("sql", "")
        explanation = result.get("explanation", "")

        if not generated_sql.upper().startswith("SELECT"):
            return {"error": "Generated SQL is not a SELECT query", "sql": generated_sql}

        rows = []
        try:
            exec_result = await db.execute(text(generated_sql))
            columns = exec_result.keys()
            rows = [dict(zip(columns, row)) for row in exec_result.all()]
        except Exception as sql_err:
            return {"error": f"SQL execution failed: {sql_err}", "sql": generated_sql, "explanation": explanation}

        return {
            "question": question,
            "sql": generated_sql,
            "explanation": explanation,
            "row_count": len(rows),
            "results": rows[:100],
        }
    except Exception as e:
        return {"error": str(e), "question": question}
