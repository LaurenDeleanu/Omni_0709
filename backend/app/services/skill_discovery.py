import logging
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.agent import AgentExecutionRun, DiscoveryReport as DiscoveryReportModel

logger = logging.getLogger("successcore.skill_discovery")


@dataclass
class UsageAnalysis:
    top_tools: list = field(default_factory=list)
    top_combinations: list = field(default_factory=list)
    top_patterns: list = field(default_factory=list)
    module_usage: dict = field(default_factory=dict)
    time_period: str = "30 days"


@dataclass
class TaskPattern:
    name: str = ""
    tool_sequence: list = field(default_factory=list)
    frequency: int = 0
    users_affected: int = 0
    potential_savings_hours: float = 0.0
    suggested_skill: str = ""


@dataclass
class ToolSuggestion:
    name: str = ""
    module: str = ""
    description: str = ""
    inputs: dict = field(default_factory=dict)
    outputs: dict = field(default_factory=dict)
    demand_rating: int = 0


@dataclass
class DiscoveryReport:
    analysis: Optional[UsageAnalysis] = None
    tasks: list = field(default_factory=list)
    suggestions: list = field(default_factory=list)
    report_text: str = ""
    confidence_scores: dict = field(default_factory=dict)


class SkillDiscovery:

    async def analyze_platform_usage(
        self, db: AsyncSession, days: int = 30
    ) -> UsageAnalysis:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        try:
            result = await db.execute(
                select(AgentExecutionRun).where(
                    AgentExecutionRun.created_at >= cutoff,
                    AgentExecutionRun.status.in_(["success", "failed"]),
                )
            )
            runs = result.scalars().all()
        except Exception as e:
            logger.warning(f"Could not query AgentExecutionRun: {e}")
            return UsageAnalysis(time_period=f"{days} days")

        tool_counter: dict = {}
        combination_counter: dict = {}
        module_usage: dict = {}
        query_patterns: dict = {}

        for run in runs:
            trace = run.execution_trace or ""
            try:
                steps = []
                if isinstance(run.input_payload, dict):
                    message = run.input_payload.get("message", "")
                    if message:
                        query_patterns.setdefault(message[:60], 0)
                        query_patterns[message[:60]] += 1
                else:
                    trace_str = str(run.input_payload)
                    if trace_str:
                        query_patterns.setdefault(trace_str[:60], 0)
                        query_patterns[trace_str[:60]] += 1

                trace_tokens = trace.replace("[", " ").replace("]", " ").replace('"', " ").split()
                for token in trace_tokens:
                    token_clean = token.strip(",")
                    if token_clean:
                        tool_counter.setdefault(token_clean, 0)
                        tool_counter[token_clean] += 1
            except Exception:
                pass

            trigger_source = run.trigger_source or "unknown"
            module_usage.setdefault(trigger_source, 0)
            module_usage[trigger_source] += 1

            try:
                if run.execution_trace and len(run.execution_trace) > 5:
                    combo_key = run.execution_trace[:80]
                    combination_counter.setdefault(combo_key, 0)
                    combination_counter[combo_key] += 1
            except Exception:
                pass

        top_tools = sorted(
            [{"tool": k, "count": v} for k, v in tool_counter.items() if v > 1],
            key=lambda x: x["count"],
            reverse=True,
        )[:10]

        top_combinations = sorted(
            [{"trace": k[:60], "count": v} for k, v in combination_counter.items() if v > 1],
            key=lambda x: x["count"],
            reverse=True,
        )[:5]

        top_patterns = sorted(
            [{"pattern": k, "frequency": v} for k, v in query_patterns.items() if v > 1],
            key=lambda x: x["frequency"],
            reverse=True,
        )[:10]

        analysis = UsageAnalysis(
            top_tools=top_tools,
            top_combinations=top_combinations,
            top_patterns=top_patterns,
            module_usage=module_usage,
            time_period=f"{days} days",
        )

        logger.info(f"Platform usage analysis: {len(top_tools)} tools, {len(top_patterns)} patterns")
        return analysis

    async def discover_repetitive_tasks(
        self, db: AsyncSession, min_frequency: int = 20
    ) -> list:
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        try:
            result = await db.execute(
                select(AgentExecutionRun).where(
                    AgentExecutionRun.created_at >= cutoff,
                    AgentExecutionRun.status != "running",
                )
            )
            runs = result.scalars().all()
        except Exception as e:
            logger.warning(f"Could not query AgentExecutionRun for repetitive tasks: {e}")
            return []

        sequence_counter: dict = {}
        for run in runs:
            trace = run.execution_trace or ""
            if not trace:
                continue
            trace_compact = trace.replace(" ", "").replace("\n", "")
            if trace_compact:
                sequence_counter.setdefault(trace_compact, {"count": 0, "runs": []})
                sequence_counter[trace_compact]["count"] += 1
                sequence_counter[trace_compact]["runs"].append(run)

        tasks = []
        for seq, data in sequence_counter.items():
            freq = data["count"]
            if freq >= min_frequency:
                sim_trace = seq[:80]
                tasks.append(TaskPattern(
                    name=f"Pattern from {sim_trace}...",
                    tool_sequence=[sim_trace],
                    frequency=freq,
                    users_affected=min(freq, 5),
                    potential_savings_hours=freq * 0.05,
                    suggested_skill=f"Auto-{sim_trace[:30]}",
                ))

        tasks.sort(key=lambda x: x.frequency, reverse=True)
        logger.info(f"Discovered {len(tasks)} repetitive task patterns (min_freq={min_frequency})")
        return tasks

    async def suggest_new_tools(self, db: AsyncSession) -> list:
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        try:
            result = await db.execute(
                select(AgentExecutionRun).where(
                    AgentExecutionRun.created_at >= cutoff,
                    AgentExecutionRun.status == "failed",
                )
            )
            failed_runs = result.scalars().all()
        except Exception as e:
            logger.warning(f"Could not query failed runs for tool suggestions: {e}")
            return []

        suggestions = []
        failure_patterns: dict = {}

        for run in failed_runs:
            payload_text = ""
            if isinstance(run.input_payload, dict):
                payload_text = run.input_payload.get("message", "") or str(run.input_payload)
            else:
                payload_text = str(run.input_payload or "")

            failure_patterns.setdefault(payload_text[:80], 0)
            failure_patterns[payload_text[:80]] += 1

        for pattern, count in sorted(failure_patterns.items(), key=lambda x: x[1], reverse=True)[:5]:
            if count >= 3:
                module = "general"
                if "payroll" in pattern.lower():
                    module = "payroll"
                elif "it" in pattern.lower() or "device" in pattern.lower():
                    module = "it"
                elif "crm" in pattern.lower() or "client" in pattern.lower():
                    module = "crm"

                suggestions.append(ToolSuggestion(
                    name=f"auto_{pattern[:20].replace(' ', '_').lower()}",
                    module=module,
                    description=f"Suggested tool to handle failed queries like: {pattern}",
                    inputs={"query": "string"},
                    outputs={"result": "string"},
                    demand_rating=min(count * 10, 100),
                ))

        logger.info(f"Generated {len(suggestions)} tool suggestions from {len(failed_runs)} failed runs")
        return suggestions

    async def generate_discovery_report(self, db: AsyncSession) -> DiscoveryReport:
        analysis = await self.analyze_platform_usage(db, days=7)
        tasks = await self.discover_repetitive_tasks(db, min_frequency=5)
        suggestions = await self.suggest_new_tools(db)

        confidence = {
            "usage_analysis": 0.85,
            "repetitive_tasks": 0.70 if tasks else 0.0,
            "tool_suggestions": 0.60 if suggestions else 0.0,
        }

        summary_lines = []
        if analysis.top_tools:
            summary_lines.append(
                f"Top tool: {analysis.top_tools[0]['tool']} ({analysis.top_tools[0]['count']} uses)"
            )
        if tasks:
            summary_lines.append(
                f"Found {len(tasks)} repetitive patterns. Top: {tasks[0].frequency}x"
            )
        if suggestions:
            summary_lines.append(
                f"Suggested {len(suggestions)} new tools. Top demand: {suggestions[0].demand_rating}"
            )
        if not summary_lines:
            summary_lines.append("No significant patterns found this period. Increase usage to enable discovery.")

        executive_summary = ". ".join(summary_lines) + "."

        report_text = (
            f"=== Skill Discovery Report ===\n"
            f"Period: {analysis.time_period}\n"
            f"Top Tools: {[t['tool'] for t in analysis.top_tools[:5]]}\n"
            f"Repetitive Tasks: {len(tasks)}\n"
            f"Tool Suggestions: {len(suggestions)}\n"
            f"Summary: {executive_summary}\n"
        )

        report = DiscoveryReport(
            analysis=analysis,
            tasks=tasks,
            suggestions=suggestions,
            report_text=report_text,
            confidence_scores=confidence,
        )

        try:
            db_report = DiscoveryReportModel(
                report_type="weekly",
                analysis_data={
                    "top_tools": analysis.top_tools,
                    "top_combinations": analysis.top_combinations,
                    "top_patterns": analysis.top_patterns,
                    "module_usage": analysis.module_usage,
                    "time_period": analysis.time_period,
                },
                tasks_discovered=[
                    {
                        "name": t.name,
                        "frequency": t.frequency,
                        "suggested_skill": t.suggested_skill,
                        "potential_savings_hours": t.potential_savings_hours,
                    }
                    for t in tasks
                ],
                tools_suggested=[
                    {
                        "name": s.name,
                        "module": s.module,
                        "description": s.description,
                        "demand_rating": s.demand_rating,
                    }
                    for s in suggestions
                ],
                executive_summary=executive_summary,
                status="generated",
            )
            db.add(db_report)
            await db.commit()
            logger.info(f"Discovery report stored: {db_report.id}")
        except Exception as e:
            logger.error(f"Failed to store discovery report: {e}")

        return report

    async def get_discovery_reports(self, db: AsyncSession, limit: int = 20) -> list:
        result = await db.execute(
            select(DiscoveryReportModel)
            .order_by(DiscoveryReportModel.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_discovery_report(self, db: AsyncSession, report_id: str):
        result = await db.execute(
            select(DiscoveryReportModel).where(DiscoveryReportModel.id == report_id)
        )
        return result.scalar_one_or_none()
