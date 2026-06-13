import os
import time
import json
import logging
import subprocess
from typing import Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
import uuid

from app.models.agent import Agent, AgentConfig, AgentExecutionRun
from app.services.llm_router import get_llm_client
from app.services.omni_orchestrator import OmniOrchestrator
from app.services.branch_edit_manager import BranchEditManager

logger = logging.getLogger(__name__)

# Base Workspace Root (SAS directory)
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

def sanitize_path(relative_path: str) -> str:
    """
    Sanitiza una ruta relativa y asegura que esté dentro del Workspace Root.
    """
    # Remove leading slashes/backslashes
    clean_rel = relative_path.lstrip("/\\")
    absolute = os.path.abspath(os.path.join(WORKSPACE_ROOT, clean_rel))
    if not absolute.startswith(WORKSPACE_ROOT):
        raise PermissionError("Access denied: path is outside workspace root")
    return absolute

def list_files(dir_path: str) -> List[str]:
    """
    Lista archivos y carpetas dentro de una ruta. Excluye carpetas del sistema.
    """
    full_path = sanitize_path(dir_path)
    if not os.path.exists(full_path) or not os.path.isdir(full_path):
        return []
        
    entries = os.listdir(full_path)
    results = []
    
    ignore_names = {
        "node_modules", ".next", ".git", ".idea", ".gemini", 
        "dist", "venv", "__pycache__", "successcore.db"
    }
    
    for entry in entries:
        if entry in ignore_names:
            continue
        full_entry_path = os.path.join(full_path, entry)
        rel_path = os.path.relpath(full_entry_path, WORKSPACE_ROOT).replace("\\", "/")
        is_dir = os.path.isdir(full_entry_path)
        type_str = "DIR" if is_dir else "FILE"
        results.append(f"{rel_path} ({type_str})")
        
    return results

def read_file(file_path: str) -> str:
    """
    Lee el contenido de un archivo del workspace.
    """
    full_path = sanitize_path(file_path)
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        return "Error: File not found or is a directory."
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

def write_file(file_path: str, content: str) -> str:
    """
    Escribe contenido en un archivo del workspace. Crea directorios si no existen.
    """
    full_path = sanitize_path(file_path)
    dir_path = os.path.dirname(full_path)
    try:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote file: {file_path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"

async def run_build_command() -> str:
    """
    Ejecuta comandos de compilación en el frontend para validar que compile limpiamente.
    """
    frontend_dir = os.path.join(WORKSPACE_ROOT, "frontend")
    try:
        # Running typescript compiler check dynamically resolving cmd on Windows
        cmd = ["npx.cmd" if os.name == "nt" else "npx", "tsc", "--noEmit"]
        process = subprocess.run(
            cmd,
            cwd=frontend_dir,
            shell=False,
            capture_output=True,
            text=True,
            timeout=30.0
        )
        output = f"STDOUT:\n{process.stdout}\n\nSTDERR:\n{process.stderr}"
        if process.returncode != 0:
            output += f"\n\nExit Code: {process.returncode}\nStatus: Compilation FAILED"
        else:
            output += f"\n\nStatus: Compilation SUCCESS"
        return output
    except Exception as e:
        return f"Error running build check: {str(e)}"

async def execute_orchestration(
    db: AsyncSession,
    user_prompt: str,
    user_id: str,
    max_sub_agents: int = 5,
) -> Dict[str, Any]:
    """
    Ejecuta el OmniOrchestrator para tareas complejas multi-agente.
    """
    from app.models.agent import Agent as AgentModel
    from sqlalchemy import select as _select

    agent_res = await db.execute(
        _select(AgentModel).where(AgentModel.agent_type == "OMNI_MASTER").order_by(AgentModel.created_at.desc()).limit(1)
    )
    agent = agent_res.scalar_one_or_none()

    if not agent:
        return {"success": False, "error": "Omni Master Agent not configured", "response": "No Omni Master agent found."}

    try:
        orchestrator = OmniOrchestrator(db, agent, user_prompt, user_id)
        result = await orchestrator.run_orchestration(max_sub_agents=max_sub_agents)

        return {
            "success": result.status == "completed",
            "response": result.final_answer,
            "orchestration": {
                "status": result.status,
                "sub_results": [
                    {
                        "sub_task_id": sr.sub_task_id,
                        "agent_type": sr.agent_type,
                        "status": sr.status,
                        "tokens_used": sr.tokens_used,
                        "cost_usd": sr.cost_usd,
                        "latency_ms": sr.latency_ms,
                    }
                    for sr in result.sub_results
                ],
                "total_tokens_used": result.total_tokens_used,
                "total_cost_usd": result.total_cost_usd,
                "total_latency_ms": result.total_latency_ms,
            },
        }
    except Exception as e:
        logger.error(f"Orchestration failed: {e}")
        return {"success": False, "error": str(e), "response": f"Orchestration error: {str(e)}"}


async def execute_omni_master(
    db: AsyncSession,
    user_prompt: str,
    user_id: str
) -> Dict[str, Any]:
    """
    Ejecuta el bucle del Agente Omni Master, resolviendo instrucciones directas en la codebase.
    """
    start_time = time.monotonic()
    
    # 1. Load the Omni Master agent (already created by omni.py API)
    agent_res = await db.execute(
        select(Agent).where(Agent.agent_type == "OMNI_MASTER").order_by(Agent.created_at.desc()).limit(1)
    )
    agent = agent_res.scalar_one_or_none()
    
    if not agent:
        return {"success": False, "error": "Omni Master Agent not configured. Configure it in CodeLab first.", "response": "No Omni Master agent found. Please configure it in the Omni settings tab."}

    config_res = await db.execute(select(AgentConfig).where(AgentConfig.agent_id == agent.id))
    config = config_res.scalar_one_or_none()
    max_loops = config.max_loops if config else 10
    
    # 2. Inicializar registro de ejecución
    run_log = AgentExecutionRun(
        id=uuid.uuid4().hex,
        agent_id=agent.id,
        trigger_source="OMNI_CONSOLE",
        status="running",
        input_payload={"prompt": user_prompt},
        loop_count=0,
        token_usage=0,
        cost_usd=0.0,
        latency_ms=0,
        execution_trace=""
    )
    db.add(run_log)
    await db.flush()
    
    agent_system_prompt = agent.ai_system_prompt or "Eres el Omni Master Controller de SuccessCore, un agente con privilegios elevados capaz de leer, escribir y compilar el código fuente de la plataforma."

    edit_mode = (agent.agent_settings or {}).get("edit_mode", "direct")
    branch_manager = BranchEditManager()
    active_branch_session = None
    branch_mode_instruction = ""

    if edit_mode == "proposal":
        try:
            base_branch = (agent.agent_settings or {}).get("base_branch", "main")
            active_branch_session = await branch_manager.initialize_branch(
                agent.id, base_branch, user_id, db
            )
            branch_mode_instruction = (
                f"\n\nIMPORTANT: You are working in PROPOSAL mode. Your file changes will NOT be applied directly. "
                f"They will be stored as proposals on branch '{active_branch_session.branch_name}' for review. "
                f"After making changes, explain WHY each change was made using the 'reason' field in codebase_write_file."
            )
        except Exception as e:
            logger.error(f"Failed to create branch session: {e}")

        system_prompt = f"""{agent_system_prompt}

Tu objetivo es resolver la directiva del supervisor ejecutando acciones a través de tus herramientas codebase.

Si la solicitud es una pregunta compleja de RRHH que involucra múltiples módulos o requiere análisis de datos, usa 'codebase_orchestrate' para dividir el trabajo entre agentes especializados.

Debes analizar el estado actual, decidir qué herramienta llamar, y responder estrictamente en formato JSON en cada paso.{branch_mode_instruction}

Herramientas disponibles:
1. codebase_list_files: {{"path": "ruta/relativa"}}
2. codebase_read_file: {{"path": "ruta/relativa/archivo.ts"}}
3. codebase_write_file: {{"path": "ruta/relativa/nuevo.ts", "content": "código completo...", "reason": "explicación del cambio"}}
4. codebase_run_build: {{}} (compila el proyecto con tsc para verificar errores)
5. codebase_orchestrate: {{"message": "pregunta compleja de RRHH a orquestar", "max_sub_agents": 5}} (divide la tarea en sub-agentes especializados para consultas multi-modulo)
6. codebase_commit_changes: {{"title": "título del commit", "body": "descripción del cambio"}} (confirma todos los cambios propuestos)
7. branch_edit_mode: {{"action": "status"|"switch", "mode": "direct"|"proposal"}} (consulta o cambia el modo de edición)
8. finish: {{"response": "Resumen amigable del trabajo realizado."}}

Usa 'codebase_orchestrate' para preguntas complejas de RRHH que abarquen múltiples áreas (nómina, cumplimiento, rendimiento, contratación, etc.). Usa las herramientas codebase_* para modificar código.

Asegúrate de ejecutar 'codebase_run_build' después de modificar archivos para comprobar si compila sin errores.

Formato de Respuesta Requerido (JSON Estricto):
{{
  "thought": "Tu razonamiento paso a paso aquí...",
  "tool": "codebase_list_files" | "codebase_read_file" | "codebase_write_file" | "codebase_run_build" | "codebase_orchestrate" | "codebase_commit_changes" | "branch_edit_mode" | "finish",
  "arguments": {{ ... }}
}}
"""

    history = []
    execution_traces = []
    current_prompt = user_prompt
    loop_count = 0
    final_response = "Timeout error: Max loop iterations reached."
    
    # Obtener cliente de LLM
    client, _ = await get_llm_client(agent.ai_model, agent, db)
    
    while loop_count < max_loops:
        loop_count += 1
        run_log.loop_count = loop_count
        step_start = time.monotonic()
        
        # Mezclar historia para la llamada
        messages = [{"role": "system", "content": system_prompt}]
        for hist_turn in history:
            messages.append(hist_turn)
        messages.append({"role": "user", "content": current_prompt})
        
        try:
            response = await client.chat.completions.create(
                model=agent.ai_model,
                temperature=0.2,
                messages=messages
            )
            raw_text = response.choices[0].message.content
            if not raw_text:
                raw_text = ""
            raw_text = raw_text.strip()
            
            # Try parsing: first as single JSON, then line-by-line (JSONL), take last valid one
            parsed_response = None
            # Try extracting JSON from the response — find the last complete JSON object
            for attempt in range(3):
                try:
                    if attempt == 0:
                        clean = raw_text[raw_text.find("{"):raw_text.rfind("}") + 1]
                        parsed_response = json.loads(clean)
                    elif attempt == 1:
                        lines = raw_text.replace("\r\n", "\n").split("\n")
                        for line in reversed(lines):
                            line = line.strip()
                            if line.startswith("{") and line.endswith("}"):
                                try:
                                    parsed_response = json.loads(line)
                                    if "tool" in parsed_response:
                                        break
                                except Exception:
                                    continue
                    else:
                        # Find all { } pairs and try each
                        import re
                        matches = re.findall(r'\{[^{}]*\}', raw_text)
                        for m in reversed(matches):
                            try:
                                candidate = json.loads(m)
                                if "tool" in candidate or "thought" in candidate:
                                    parsed_response = candidate
                                    break
                            except Exception:
                                continue
                    if parsed_response:
                        break
                except Exception:
                    continue
            
            if not parsed_response:
                parsed_response = {
                    "thought": "Processing request",
                    "tool": "finish",
                    "arguments": {"response": raw_text[:2000]}
                }
                
            latency = int((time.monotonic() - step_start) * 1000)
            execution_traces.append({
                "step": loop_count,
                "thought": parsed_response.get("thought", "No thought provided."),
                "tool": parsed_response.get("tool", "none"),
                "arguments": parsed_response.get("arguments", {}),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "latencyMs": latency
            })
            
            # Guardar en historia
            history.append({"role": "user", "content": current_prompt})
            history.append({"role": "assistant", "content": json.dumps(parsed_response, ensure_ascii=False)})
            
            if parsed_response.get("tool") == "finish":
                final_response = parsed_response.get("arguments", {}).get("response", "Completado.")
                break
                
            tool_output = ""
            args = parsed_response.get("arguments", {})
            tool_name = parsed_response.get("tool")
            
            if tool_name == "codebase_list_files":
                files = list_files(args.get("path", "."))
                tool_output = f"Files in directory \"{args.get('path')}\":\n" + "\n".join(files)
            elif tool_name == "codebase_read_file":
                tool_output = read_file(args.get("path", ""))
            elif tool_name == "codebase_write_file":
                file_path = args.get("path", "")
                content = args.get("content", "")
                reason = args.get("reason", "")
                if active_branch_session:
                    original_content = read_file(file_path)
                    if original_content.startswith("Error"):
                        original_content = ""
                    proposal = await branch_manager.write_file_proposal(
                        active_branch_session.id,
                        file_path,
                        content,
                        original_content,
                        reason,
                        db,
                        agent_id=agent.id,
                    )
                    tool_output = (
                        f"[PROPOSAL MODE] Change stored as proposal {proposal.id} on branch "
                        f"'{active_branch_session.branch_name}'. NOT written to disk. "
                        f"Status: pending review. File: {file_path}"
                    )
                else:
                    tool_output = write_file(file_path, content)
            elif tool_name == "codebase_run_build":
                tool_output = await run_build_command()
            elif tool_name == "codebase_commit_changes":
                if not active_branch_session:
                    tool_output = "Error: No active proposal branch session. Switch to proposal mode first."
                else:
                    try:
                        patch_path = await branch_manager.create_patch_file(
                            active_branch_session.id, db
                        )
                        await branch_manager.apply_patch_file(patch_path, db)
                        from app.services.local_git_service import commit_changes as git_commit
                        commit_hash = await git_commit(
                            args.get("title", "Omni Agent changes"),
                            [],
                        )
                        apply_result = await branch_manager.apply_all_pending(
                            active_branch_session.id, "omni_agent", db
                        )
                        tool_output = (
                            f"Committed {apply_result['applied']} proposals to branch "
                            f"'{active_branch_session.branch_name}'. Commit: {commit_hash[:12]}. "
                            f"Status: {apply_result['branch_status']}"
                        )
                        if apply_result.get("errors"):
                            tool_output += f"\nErrors: {apply_result['errors']}"
                    except Exception as e:
                        tool_output = f"Error committing changes: {str(e)}"
            elif tool_name == "branch_edit_mode":
                action = args.get("action", "status")
                if action == "switch":
                    new_mode = args.get("mode", "direct")
                    await branch_manager.set_edit_mode(agent.id, {"mode": new_mode}, db)
                    tool_output = f"Edit mode switched to '{new_mode}'. Restart agent execution for it to take effect."
                else:
                    mode_info = await branch_manager.get_edit_mode(agent.id, db)
                    tool_output = f"Current edit mode: {mode_info['mode']}. Branch: {active_branch_session.branch_name if active_branch_session else 'N/A'}"
            elif tool_name == "codebase_orchestrate":
                orchestrator_message = args.get("message", user_prompt)
                orchestrator_max_agents = args.get("max_sub_agents", 5)
                orchestration_result = await execute_orchestration(
                    db, orchestrator_message, user_id, max_sub_agents=orchestrator_max_agents
                )
                if orchestration_result.get("success"):
                    org_response = orchestration_result.get("response", "")
                    org_meta = json.dumps(orchestration_result.get("orchestration", {}), default=str)
                    tool_output = f"Orchestration completed successfully.\n\n{org_response}\n\n---\nMetrics: {org_meta}"
                    final_response = org_response
                    parsed_response["tool"] = "finish"
                    parsed_response["arguments"] = {"response": org_response}
                else:
                    tool_output = f"Orchestration failed: {orchestration_result.get('error', orchestration_result.get('response', 'Unknown error'))}"
            else:
                tool_output = f"Error: Unknown tool \"{tool_name}\"."
                
            current_prompt = f"Tool Output for {tool_name}:\n{tool_output}"
            
        except Exception as e:
            logger.error(f"[Omni Master Loop Error]: {e}")
            final_response = f"Error executing master loop: {str(e)}"
            break
            
    # 4. Guardar corrida
    try:
        run_log.status = "failed" if final_response.startswith("Error") or "Timeout" in final_response else "success"
        run_log.output_result = {"reply": final_response}
        run_log.latency_ms = int((time.monotonic() - start_time) * 1000)
        run_log.token_usage = loop_count * 1500 # Estimado
        run_log.cost_usd = loop_count * 0.005
        run_log.execution_trace = json.dumps(execution_traces, ensure_ascii=False)
        
        # AI Reseller Billing Hook for Omni Master
        try:
            from app.services.llm_router import get_tenant_keys
            tenant_keys = await get_tenant_keys(agent, db)
            
            # Determine model provider
            model_name = agent.ai_model.lower()
            provider = "openai"
            if "/" in model_name or "openrouter" in model_name:
                provider = "openrouter"
            elif "gemini" in model_name:
                provider = "gemini"
                
            byok_active = False
            if provider == "openai" and tenant_keys.get("openai_api_key"):
                byok_active = True
            elif provider == "openrouter" and tenant_keys.get("openrouter_api_key"):
                byok_active = True
            elif provider == "gemini" and tenant_keys.get("gemini_api_key"):
                byok_active = True
                
            if agent.agent_settings:
                if provider == "openai" and agent.agent_settings.get("openai_api_key"):
                    byok_active = True
                elif provider == "openrouter" and agent.agent_settings.get("openrouter_api_key"):
                    byok_active = True
                elif provider == "gemini" and agent.agent_settings.get("gemini_api_key"):
                    byok_active = True
                    
            if not byok_active and user_id:
                from app.models.user import User
                user_res = await db.execute(
                    select(User).where((User.id == user_id) | (User.email == user_id))
                )
                user = user_res.scalar_one_or_none()
                if user:
                    user.current_debt += run_log.cost_usd
        except Exception as e:
            logger.error(f"Error in reseller billing cost hook for omni: {e}")
            
        await db.commit()
    except Exception as log_err:
        logger.error(f"Failed to log Omni Execution Run: {log_err}")
        
    return {
        "success": not (final_response.startswith("Error") or "Timeout" in final_response),
        "response": final_response,
        "trace": execution_traces
    }
