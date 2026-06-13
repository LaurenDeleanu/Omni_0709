import json
import logging
import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("successcore.nl_workflow_builder")

SUPPORTED_ACTION_TYPES = {
    "send_email": {"params": {"to", "subject", "body"}},
    "send_notification": {"params": {"recipient_role", "title", "message", "channel"}},
    "create_task": {"params": {"title", "description", "assignee", "priority"}},
    "assign_task": {"params": {"task_name", "title", "assignee_role", "deadline_days"}},
    "schedule_meeting": {"params": {"title", "attendees", "duration_minutes"}},
    "update_user_field": {"params": {"field", "value"}},
    "enroll_in_training": {"params": {"course_name", "enrollment_type"}},
    "create_it_ticket": {"params": {"title", "description", "category", "priority"}},
    "generate_document": {"params": {"template_name", "output_format"}},
    "wait_for_approval": {"params": {"approver_role", "timeout_hours"}},
    "webhook_call": {"params": {"url", "method", "body"}},
    "agent_step": {"params": {"agent_id", "prompt", "timeout"}},
    "conditional_branch": {"params": {"field", "operator", "value", "true_branch_name", "false_branch_name"}},
}

WORKFLOW_GENERATION_PROMPT = """You are an expert workflow designer for an HR platform (SuccessCore). 
Given a natural language description of a business process, generate a complete workflow definition in JSON.

Rules:
1. Identify the trigger event that starts the workflow (e.g., "employee.hired", "employee.offboarded", "review.period.start")
2. Break the process into sequential steps. If steps can happen in parallel, note dependencies (depends_on_step_index: null means no dependency).
3. For each step, choose the most appropriate action_type from this list:
   {action_types}
4. Assign assignee_role for each step: hr_admin, it_admin, manager, employee, sys_admin
5. Set reasonable deadline_days for each step. Default to 3 if unclear.
6. Include notification specs where appropriate (who gets notified when step completes).
7. If the description mentions conditions (e.g., "if remote employee..."), add conditional_branch steps.
8. If the description mentions approvals, add wait_for_approval steps.
9. Default workflow type: "onboarding" unless the description clearly describes offboarding.

Output ONLY valid JSON, no markdown, no explanation. Format:
{{
  "trigger": "event.name",
  "type": "onboarding",
  "steps": [
    {{
      "name": "Send Welcome Email",
      "description": "Send welcome email to new employee",
      "action_type": "send_email",
      "assignee_role": "hr_admin",
      "deadline_days": 1,
      "depends_on_step_index": null,
      "conditions": null,
      "notifications": [{{"role": "employee", "message": "Welcome email sent"}}]
    }}
  ],
  "estimated_total_days": 14,
  "rationale": "Brief summary of why this workflow was structured this way"
}}"""


def _build_system_prompt() -> str:
    action_list = "\n   ".join(f"- {k}: {v['params']}" for k, v in SUPPORTED_ACTION_TYPES.items())
    return WORKFLOW_GENERATION_PROMPT.format(action_types=action_list)


def _parse_llm_json(raw: str) -> dict:
    clean = raw.strip()
    if "```json" in clean:
        clean = clean[clean.find("```json") + 7:]
        if "```" in clean:
            clean = clean[:clean.rfind("```")]
    elif "```" in clean:
        clean = clean[clean.find("```") + 3:]
        if "```" in clean:
            clean = clean[:clean.rfind("```")]
    if "{" in clean and "}" in clean:
        clean = clean[clean.find("{"):clean.rfind("}") + 1]
    return json.loads(clean)


def _validate_steps(definition: dict) -> List[str]:
    errors = []
    steps = definition.get("steps", [])
    if not steps:
        errors.append("No steps defined in the workflow")
        return errors
    for i, step in enumerate(steps):
        action_type = step.get("action_type", "")
        if not action_type:
            errors.append(f"Step {i} ('{step.get('name', 'unnamed')}') has no action_type")
        elif action_type not in SUPPORTED_ACTION_TYPES:
            errors.append(f"Step {i} ('{step.get('name', 'unnamed')}'): action_type '{action_type}' is not supported. Available: {list(SUPPORTED_ACTION_TYPES.keys())}")
        if not step.get("name"):
            errors.append(f"Step {i} has no name")
        assignee = step.get("assignee_role", "")
        if assignee not in ("hr_admin", "it_admin", "manager", "employee", "sys_admin", ""):
            errors.append(f"Step {i} ('{step.get('name', 'unnamed')}'): assignee_role '{assignee}' is invalid")
    return errors


def _to_template_steps(steps: List[dict]) -> List[dict]:
    result = []
    for i, step in enumerate(steps):
        result.append({
            "id": step.get("id", f"step_{i + 1:03d}"),
            "title": step.get("name", f"Step {i + 1}"),
            "role": step.get("assignee_role", "employee"),
            "action_type": step.get("action_type", ""),
            "description": step.get("description", ""),
            "deadline_days": step.get("deadline_days", 3),
            "depends_on_step_index": step.get("depends_on_step_index"),
            "conditions": step.get("conditions"),
            "notifications": step.get("notifications", []),
        })
    return result


async def generate_workflow_from_text(description: str, tenant_id: str, db: Optional[AsyncSession] = None) -> dict:
    from app.services.llm_router import get_llm_client

    system_prompt = _build_system_prompt()

    try:
        client, _ = await get_llm_client("gpt-4o-mini", db=db)
        logger.info(f"Generating workflow from description (len={len(description)})")
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Process description: {description}"},
            ],
        )

        if not response.choices:
            logger.error("LLM returned empty choices for workflow generation")
            return {
                "error": "LLM returned no response",
                "detail": "The model returned an empty choices list",
                "trigger": "manual",
                "type": "onboarding",
                "steps": [],
                "estimated_total_days": 0,
                "rationale": "",
                "validation_errors": ["LLM returned empty choices"],
                "step_count": 0,
            }

        raw = response.choices[0].message.content.strip() if response.choices[0].message.content else "{}"
        logger.debug(f"LLM workflow response (first 200 chars): {raw[:200]}")
        definition = _parse_llm_json(raw)

        validation_errors = _validate_steps(definition)
        if validation_errors:
            logger.warning(f"Workflow generation validation issues: {validation_errors}")
            for error in validation_errors:
                logger.warning(f"  - {error}")

        steps = definition.get("steps", [])
        template_steps = _to_template_steps(steps)

        return {
            "trigger": definition.get("trigger", "manual"),
            "type": definition.get("type", "onboarding"),
            "steps": template_steps,
            "estimated_total_days": definition.get("estimated_total_days", sum(s.get("deadline_days", 3) for s in steps)),
            "rationale": definition.get("rationale", ""),
            "validation_errors": validation_errors,
            "step_count": len(steps),
        }
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        return {
            "error": "Failed to generate workflow definition",
            "detail": str(e),
            "trigger": "manual",
            "type": "onboarding",
            "steps": [],
            "estimated_total_days": 0,
            "rationale": "",
            "validation_errors": ["LLM response was not valid JSON"],
            "step_count": 0,
        }
    except Exception as e:
        logger.error(f"Error generating workflow from text: {e}")
        return {
            "error": str(e),
            "trigger": "manual",
            "type": "onboarding",
            "steps": [],
            "estimated_total_days": 0,
            "rationale": "",
            "validation_errors": [str(e)],
            "step_count": 0,
        }


async def create_workflow_from_nl(description: str, name: str, user_id: str, tenant_id: str, db: AsyncSession) -> dict:
    from app.models.workflow import WorkflowTemplate

    generated = await generate_workflow_from_text(description, tenant_id, db=db)

    if generated.get("error") and not generated.get("steps"):
        return {
            "success": False,
            "error": generated.get("error", "Generation failed"),
            "validation_errors": generated.get("validation_errors", []),
            "workflow": None,
        }

    template = WorkflowTemplate(
        id=uuid.uuid4().hex,
        name=name,
        type=generated.get("type", "onboarding"),
        steps=generated.get("steps", []),
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)

    return {
        "success": True,
        "workflow": {
            "id": template.id,
            "name": template.name,
            "type": template.type,
            "steps": template.steps,
            "trigger": generated.get("trigger", "manual"),
            "estimated_total_days": generated.get("estimated_total_days", 0),
            "rationale": generated.get("rationale", ""),
        },
        "validation_errors": generated.get("validation_errors", []),
    }


async def suggest_workflow_improvements(workflow_id: str, db: AsyncSession) -> dict:
    from app.services.llm_router import get_llm_client
    from sqlalchemy import select
    from app.models.workflow import WorkflowTemplate

    result = await db.execute(select(WorkflowTemplate).where(WorkflowTemplate.id == workflow_id))
    template = result.scalar_one_or_none()
    if not template:
        return {"error": "Workflow not found", "suggestions": []}

    workflow_json = json.dumps({
        "id": template.id,
        "name": template.name,
        "type": template.type,
        "steps": template.steps,
    }, default=str)

    system_prompt = (
        "You are an expert workflow optimization analyst for an HR platform. "
        "Analyze the given workflow definition and suggest concrete improvements.\n\n"
        "Check for:\n"
        "- Steps that could run in parallel (no true dependency between them)\n"
        "- Redundant or unnecessary approval steps\n"
        "- Missing notifications (critical steps with no notify)\n"
        "- SLA improvements (steps with unusually long deadlines)\n"
        "- Missing edge case handling (no conditional branches where there should be)\n"
        "- Automation opportunities (manual steps that could be system actions)\n\n"
        "Output ONLY valid JSON. Format:\n"
        '{"suggestions": [{"priority": "high|medium|low", "category": "parallelism|redundancy|notifications|sla|edge_cases|automation", "title": "...", "description": "...", "affected_step_indices": [0, 2]}]}'
    )

    try:
        client, _ = await get_llm_client("gpt-4o-mini", db=db)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Workflow to analyze: {workflow_json}"},
            ],
        )

        raw = response.choices[0].message.content.strip() if response.choices else "{}"
        analysis = _parse_llm_json(raw)

        suggestions = analysis.get("suggestions", [])
        high = sum(1 for s in suggestions if s.get("priority") == "high")
        medium = sum(1 for s in suggestions if s.get("priority") == "medium")
        low = sum(1 for s in suggestions if s.get("priority") == "low")

        return {
            "workflow_id": workflow_id,
            "workflow_name": template.name,
            "total_suggestions": len(suggestions),
            "priority_breakdown": {"high": high, "medium": medium, "low": low},
            "suggestions": suggestions,
        }
    except Exception as e:
        logger.error(f"Error suggesting workflow improvements: {e}")
        return {"error": str(e), "suggestions": []}


async def validate_workflow_description(description: str) -> dict:
    if not description or not description.strip():
        return {
            "valid": False,
            "missing_elements": ["description"],
            "suggestions": "Please provide a description of the process you want to automate.",
        }

    min_words = 5
    words = description.split()
    missing = []

    if len(words) < min_words:
        missing.append("description_too_short")

    has_trigger = any(kw in description.lower() for kw in ["when", "if", "on ", "after", "trigger", "event"])
    has_actions = any(kw in description.lower() for kw in ["send", "create", "assign", "schedule", "notify", "approve", "generate", "enroll", "update", "check"])
    has_roles = any(kw in description.lower() for kw in ["hr", "manager", "it ", "admin", "employee", "team", "supervisor"])

    if not has_trigger:
        missing.append("trigger")
    if not has_actions:
        missing.append("actions")
    if not has_roles:
        missing.append("roles_or_assignees")

    suggestions = []
    if "trigger" in missing:
        suggestions.append("Describe what event starts the process, e.g. 'When a new employee is hired...'")
    if "actions" in missing:
        suggestions.append("Describe the actions to take, e.g. 'send welcome email, create IT ticket...'")
    if "roles_or_assignees" in missing:
        suggestions.append("Mention who performs each action, e.g. 'HR sends welcome email, IT assigns laptop...'")
    if "description_too_short" in missing:
        suggestions.append("Provide a more detailed description (at least 5 words).")

    return {
        "valid": len(missing) == 0,
        "missing_elements": missing,
        "suggestions": " ".join(suggestions) if suggestions else "Description looks sufficient for workflow generation.",
    }
