import logging
import json
import uuid
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger("successcore.scorm")


async def parse_scorm_manifest(manifest_xml: str) -> Dict[str, Any]:
    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(manifest_xml)
        ns = {"imscp": "http://www.imsproject.org/xsd/imscp_rootv1p1p2"}

        def find_text(element, path, namespace=ns):
            el = element.find(path, namespace) if namespace else element.find(path)
            return el.text.strip() if el is not None and el.text else ""

        def find_all(element, path, namespace=ns):
            return element.findall(path, namespace) if namespace else element.findall(path)

        ns_found = False
        for prefix, uri in ns.items():
            if f"xmlns:{prefix}" in manifest_xml or f'xmlns="{uri}"' in manifest_xml:
                ns_found = True
                break

        if not ns_found:
            ns = {}

        title = find_text(root, ".//imscp:title") or find_text(root, ".//title")
        description = find_text(root, ".//imscp:description") or find_text(root, ".//description")

        resources = []
        organizations = find_all(root, ".//imscp:item") if ns else find_all(root, ".//item")
        for item in organizations:
            identifierref = item.get("identifierref", "")
            item_title = item.get("title", find_text(item, "imscp:title") if ns else find_text(item, "title"))
            resources.append({
                "id": item.get("identifier", ""),
                "title": item_title,
                "identifierref": identifierref,
            })

        sco_resources = find_all(root, ".//imscp:resource") if ns else find_all(root, ".//resource")
        for res in sco_resources:
            res_id = res.get("identifier", "")
            res_type = res.get("type", "")
            res_href = res.get("href", "")
            is_scorm = "scorm" in res_type.lower() or "sco" in res_type.lower()
            for r in resources:
                if r["identifierref"] == res_id:
                    r["href"] = res_href
                    r["type"] = res_type
                    r["is_scorm"] = is_scorm

        entry_point = ""
        for res in resources:
            if res.get("is_scorm") and res.get("href"):
                entry_point = res["href"]
                break
        if not entry_point and resources:
            entry_point = resources[0].get("href", "")

        return {
            "title": title or "Untitled Course",
            "description": description or "",
            "resources": resources,
            "entry_point": entry_point,
            "total_sections": len(resources),
            "format": "SCORM 1.2" if "scorm" in str(resources).lower() else "SCORM 2004",
        }
    except ET.ParseError as e:
        logger.error(f"SCORM manifest parse error: {e}")
        raise ValueError(f"Invalid SCORM manifest XML: {e}")


def parse_xapi_statement(statement_json: str) -> Dict[str, Any]:
    try:
        data = json.loads(statement_json)
    except json.JSONDecodeError:
        raise ValueError("Invalid xAPI statement JSON")

    actor = data.get("actor", {})
    verb = data.get("verb", {})
    obj = data.get("object", {})
    result = data.get("result", {})
    context = data.get("context", {})

    return {
        "actor_name": actor.get("name", actor.get("mbox", "")),
        "actor_email": actor.get("mbox", "").replace("mailto:", ""),
        "verb": verb.get("id", "").split("/")[-1] if verb.get("id") else "experienced",
        "verb_display": verb.get("display", {}).get("en-US", verb.get("display", {}).get("en", "")),
        "object_name": obj.get("definition", {}).get("name", {}).get("en-US", obj.get("id", "")),
        "object_type": obj.get("objectType", "Activity"),
        "score": result.get("score", {}).get("scaled"),
        "success": result.get("success"),
        "completion": result.get("completion"),
        "duration": result.get("duration"),
        "timestamp": data.get("timestamp", ""),
        "activity_id": obj.get("id", ""),
        "parent_activity": context.get("contextActivities", {}).get("parent", [{}])[0].get("id", ""),
    }


async def store_scorm_course(
    db: AsyncSession,
    manifest_xml: str,
    course_name: str = "",
    tenant_id: str = "default",
) -> Dict[str, Any]:
    manifest = await parse_scorm_manifest(manifest_xml)

    course_id = uuid.uuid4().hex

    from app.models.training import Course

    # El modelo Course guarda el paquete SCORM directamente (is_scorm, scorm_version,
    # package_url); no existe un modelo de módulos, así que los recursos del manifest
    # se devuelven en la respuesta y se registran en el log
    course = Course(
        id=course_id,
        title=course_name or manifest["title"],
        description=manifest["description"],
        is_scorm=True,
        scorm_version=manifest["format"].replace("SCORM ", ""),
        package_url=manifest["entry_point"] or None,
    )
    db.add(course)

    await db.commit()
    await db.refresh(course)

    logger.info(f"SCORM course stored: {course.title} ({course_id[:8]}) with {len(manifest['resources'])} resources")
    return {
        "course_id": course_id,
        "title": course.title,
        "format": "scorm",
        "sections": len(manifest["resources"]),
    }


async def record_xapi_statement(
    db: AsyncSession,
    statement_json: str,
    user_id: str = "",
    tenant_id: str = "default",
) -> Dict[str, Any]:
    parsed = parse_xapi_statement(statement_json)

    log_id = uuid.uuid4().hex

    try:
        # El progreso del alumno se modela con CourseEnrollment (app.models.training)
        from app.models.training import CourseEnrollment

        result = await db.execute(
            select(CourseEnrollment).where(
                CourseEnrollment.user_id == user_id,
                CourseEnrollment.course_id == parsed["activity_id"],
            )
        )
        enrollment = result.scalars().first()
        if not enrollment:
            enrollment = CourseEnrollment(
                id=log_id,
                user_id=user_id,
                course_id=parsed["activity_id"],
            )
            db.add(enrollment)

        if parsed.get("completion"):
            enrollment.status = "completed"
            enrollment.progress_percentage = 100.0
            try:
                enrollment.completed_at = (
                    datetime.fromisoformat(parsed["timestamp"]) if parsed.get("timestamp") else datetime.now(timezone.utc)
                )
            except ValueError:
                enrollment.completed_at = datetime.now(timezone.utc)
        elif enrollment.status == "enrolled":
            enrollment.status = "in_progress"

        if parsed.get("score") is not None:
            # xAPI entrega la puntuación "scaled" (0..1); se almacena como porcentaje
            enrollment.score = round(float(parsed["score"]) * 100, 2)

        await db.commit()
        logger.info(f"xAPI statement recorded: {parsed['verb']} by {parsed['actor_name']}")
    except Exception as e:
        logger.warning(f"xAPI storage skipped (model mismatch): {e}")

    return {
        "statement_id": log_id,
        "actor": parsed["actor_name"],
        "verb": parsed["verb"],
        "success": parsed["success"],
        "completion": parsed["completion"],
        "score": parsed["score"],
    }


def generate_tin_can_package(manifest_data: Dict[str, Any], launch_url: str) -> str:
    return json.dumps({
        "@context": "http://projecttincan.com/tincanapi/",
        "id": str(uuid.uuid4()),
        "objectType": "Activity",
        "definition": {
            "name": {"en-US": manifest_data.get("title", "Course")},
            "description": {"en-US": manifest_data.get("description", "")},
            "type": "http://adlnet.gov/expapi/activities/course",
            "moreInfo": launch_url,
        },
    })
