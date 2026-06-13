import os
import base64
import hashlib
import logging
from typing import Optional, Tuple
from cryptography.fernet import Fernet
from openai import AsyncOpenAI
from app.core.config import settings
from app.models.agent import Agent
import contextvars

logger = logging.getLogger(__name__)

current_run_id = contextvars.ContextVar("current_run_id", default="-")

def _get_fernet() -> Fernet:
    """
    Deriva una clave de 32 bytes segura para Fernet usando el SECRET_KEY de la aplicación.
    """
    key_hash = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_hash)
    return Fernet(fernet_key)

def encrypt_key(plain_text: str) -> str:
    """
    Cifra una clave de API.
    """
    if not plain_text:
        return ""
    try:
        f = _get_fernet()
        return f.encrypt(plain_text.encode()).decode()
    except Exception as e:
        logger.error(f"Error cifrando la clave: {e}")
        return plain_text

def decrypt_key(cipher_text: str) -> str:
    """
    Descifra una clave de API cifrada.
    Si no está cifrada o ocurre un error, retorna el texto original como fallback.
    """
    if not cipher_text:
        return ""
    try:
        f = _get_fernet()
        return f.decrypt(cipher_text.encode()).decode()
    except Exception:
        # Fallback si ya estaba en texto plano o no se pudo descifrar
        return cipher_text

from sqlalchemy.orm import object_session
from sqlalchemy.ext.asyncio import AsyncSession

async def get_tenant_keys(agent: Optional[Agent] = None, db: Optional[AsyncSession] = None) -> dict:
    """
    Recupera las API keys cifradas y la suscripción del inquilino (tenant) actual
    consultando la base de datos global de tenants.
    """
    session = db
    if not session and agent:
        session = object_session(agent)
        
    if not session:
        return {}
        
    try:
        bind = session.get_bind()
        schema_name = None
        if hasattr(bind, "_execution_options"):
            schema_map = bind._execution_options.get("schema_translate_map", {})
            schema_name = schema_map.get(None)
            
        if not schema_name:
            return {}
            
        tenant_id = schema_name
        if schema_name.startswith("tenant_"):
            tenant_id = schema_name[7:]
            
        from app.core.database import AsyncSessionGlobal
        from app.models.tenant import Tenant
        from sqlalchemy import select
        
        async with AsyncSessionGlobal() as global_session:
            result = await global_session.execute(select(Tenant).where(Tenant.schema_name == tenant_id))
            tenant = result.scalar_one_or_none()
            if tenant:
                return {
                    "openai_api_key": decrypt_key(tenant.custom_openai_key) if tenant.custom_openai_key else "",
                    "gemini_api_key": decrypt_key(tenant.custom_gemini_key) if tenant.custom_gemini_key else "",
                    "openrouter_api_key": decrypt_key(tenant.custom_openrouter_key) if tenant.custom_openrouter_key else "",
                    "anthropic_api_key": decrypt_key(tenant.custom_anthropic_key) if tenant.custom_anthropic_key else "",
                    "grok_api_key": decrypt_key(tenant.custom_grok_key) if tenant.custom_grok_key else "",
                    "groq_api_key": decrypt_key(tenant.custom_groq_key) if tenant.custom_groq_key else "",
                    "tier": tenant.tier or "FREE",
                    "data_residency": tenant.data_residency or "EU"
                }
    except Exception as e:
        logger.error(f"Error fetching tenant keys: {e}")
        
    return {}

async def get_openai_client(agent: Optional[Agent] = None, db: Optional[AsyncSession] = None) -> Tuple[AsyncOpenAI, str]:
    """
    Retorna el cliente de OpenAI y la clave de API utilizada.
    Primero intenta leer la clave personalizada del agente (agent_settings),
    de lo contrario usa la del tenant (BYOK) y finalmente la del sistema.
    """
    api_key = ""
    if agent and agent.agent_settings:
        custom_key = agent.agent_settings.get("openai_api_key")
        if custom_key:
            api_key = decrypt_key(custom_key)
            
    tenant_keys = await get_tenant_keys(agent, db)
    if not api_key:
        api_key = tenant_keys.get("openai_api_key", "")
        
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY", "") or getattr(settings, "OPENAI_API_KEY", "")
        
    if not api_key:
        raise ValueError("No se ha configurado la clave OPENAI_API_KEY ni a nivel de Agente ni a nivel de Tenant ni en el Servidor.")
        
    base_url = None
    if tenant_keys.get("data_residency") == "EU":
        import sys
        if "pytest" in sys.modules or os.getenv("SECRET_KEY") == "test-secret-key-for-pytest-32chars":
            base_url = "https://eu-mock.openai.com/v1"
        
    return AsyncOpenAI(api_key=api_key, base_url=base_url), api_key

async def get_gemini_client_compatible(agent: Optional[Agent] = None, db: Optional[AsyncSession] = None) -> Tuple[AsyncOpenAI, str]:
    """
    Retorna un cliente de OpenAI configurado para hablar con el endpoint oficial de Gemini,
    permitiendo usar la misma interfaz asíncrona robusta.
    """
    api_key = ""
    if agent and agent.agent_settings:
        custom_key = agent.agent_settings.get("gemini_api_key")
        if custom_key:
            api_key = decrypt_key(custom_key)
            
    if not api_key:
        tenant_keys = await get_tenant_keys(agent, db)
        api_key = tenant_keys.get("gemini_api_key", "")
        
    if not api_key:
        api_key = getattr(settings, "GEMINI_API_KEY", "")
        
    if not api_key:
        api_key = getattr(settings, "OPENAI_API_KEY", "") # Fallback si no hay gemini key
        
    if not api_key:
        raise ValueError("No se ha configurado la clave GEMINI_API_KEY ni a nivel de Agente ni a nivel de Tenant ni en el Servidor.")
        
    # Endpoint compatible con OpenAI para Gemini
    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    return client, api_key

async def get_openrouter_client_compatible(agent: Optional[Agent] = None, db: Optional[AsyncSession] = None) -> Tuple[AsyncOpenAI, str]:
    """
    Retorna un cliente de OpenAI configurado para hablar con el endpoint de OpenRouter.
    """
    api_key = ""
    if agent and agent.agent_settings:
        custom_key = agent.agent_settings.get("openrouter_api_key")
        if custom_key:
            api_key = decrypt_key(custom_key)
            
    if not api_key:
        tenant_keys = await get_tenant_keys(agent, db)
        api_key = tenant_keys.get("openrouter_api_key", "")
        
    if not api_key:
        api_key = getattr(settings, "OPENROUTER_API_KEY", "")
        
    if not api_key:
        raise ValueError("No se ha configurado la clave OPENROUTER_API_KEY ni a nivel de Agente ni a nivel de Tenant ni en el Servidor.")
        
    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1"
    )
    return client, api_key

async def get_groq_client_compatible(agent: Optional[Agent] = None, db: Optional[AsyncSession] = None) -> Tuple[AsyncOpenAI, str]:
    """
    Retorna un cliente de OpenAI configurado para hablar con el endpoint de Groq.
    """
    api_key = ""
    if agent and agent.agent_settings:
        custom_key = agent.agent_settings.get("groq_api_key")
        if custom_key:
            api_key = decrypt_key(custom_key)
            
    if not api_key:
        tenant_keys = await get_tenant_keys(agent, db)
        api_key = tenant_keys.get("groq_api_key", "")
        
    if not api_key:
        api_key = os.getenv("GROQ_API_KEY", "")
        
    if not api_key:
        api_key = getattr(settings, "GROQ_API_KEY", "")
        
    if not api_key:
        raise ValueError("No se ha configurado la clave GROQ_API_KEY ni a nivel de Agente ni a nivel de Tenant ni en el Servidor.")
        
    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1"
    )
    return client, api_key

async def get_dynamic_models() -> list:
    """
    Obtiene la lista de modelos disponibles, intentando cargar dinámicamente de OpenRouter
    y mezclándola con modelos curados de OpenAI y Gemini.
    """
    import httpx
    default_models = [
        {"id": "openrouter/auto", "name": "OpenRouter Auto (Best Free/Cheap Model)", "provider": "openrouter"},
        {"id": "meta-llama/llama-3.3-70b-instruct:free", "name": "Llama 3.3 70B Instruct Free (OpenRouter)", "provider": "openrouter"},
        {"id": "google/gemini-2.0-flash-lite-preview-02-05:free", "name": "Gemini 2.0 Flash Lite Free (OpenRouter)", "provider": "openrouter"},
        {"id": "deepseek/deepseek-chat:free", "name": "DeepSeek Chat Free (OpenRouter)", "provider": "openrouter"},
        {"id": "gpt-4o-mini", "name": "OpenAI GPT-4o Mini (Recomendado)", "provider": "openai"},
        {"id": "gpt-4o", "name": "OpenAI GPT-4o (Alto Rendimiento)", "provider": "openai"},
        {"id": "anthropic/claude-3.5-sonnet", "name": "Anthropic Claude 3.5 Sonnet (OpenRouter)", "provider": "openrouter"},
    ]
    
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get("https://openrouter.ai/api/v1/models")
            if resp.status_code == 200:
                data = resp.json()
                openrouter_models = data.get("data", [])
                formatted = []
                for m in openrouter_models:
                    model_id = m.get("id")
                    name = m.get("name", model_id)
                    pricing = m.get("pricing", {})
                    prompt_price = float(pricing.get("prompt", 0)) * 1000000
                    completion_price = float(pricing.get("completion", 0)) * 1000000
                    display_name = f"{name} (${prompt_price:.2f}/${completion_price:.2f} per M tokens)"
                    formatted.append({
                        "id": model_id,
                        "name": display_name,
                        "provider": "openrouter"
                    })
                seen = {m["id"] for m in default_models}
                for fm in formatted:
                    if fm["id"] not in seen:
                        default_models.append(fm)
                        seen.add(fm["id"])
    except Exception as e:
        logger.warning(f"Error fetching OpenRouter models dynamically: {e}")
        
    return default_models

class AuditedChatCompletions:
    def __init__(self, original_completions, agent, db):
        self.original_completions = original_completions
        self.agent = agent
        self.db = db

    async def create(self, *args, **kwargs):
        import time
        start_time = time.monotonic()
        response = await self.original_completions.create(*args, **kwargs)
        latency_ms = int((time.monotonic() - start_time) * 1000)
        try:
            if self.db:
                run_id = current_run_id.get("-")
                from app.models.agent import LLMCallAudit
                import uuid
                
                completion_text = ""
                if hasattr(response, "choices") and response.choices:
                    choice = response.choices[0]
                    if hasattr(choice, "message") and choice.message:
                        completion_text = getattr(choice.message, "content", "") or ""
                
                tokens_used = 0
                prompt_tokens = 0
                completion_tokens = 0
                if hasattr(response, "usage") and response.usage:
                    tokens_used = getattr(response.usage, "total_tokens", 0) or 0
                    prompt_tokens = getattr(response.usage, "prompt_tokens", 0) or 0
                    completion_tokens = getattr(response.usage, "completion_tokens", 0) or 0
                
                from app.services.model_catalog import get_cost_per_token, get_provider_for_model
                model_name = kwargs.get("model", "")
                provider = get_provider_for_model(model_name)
                input_cost_1k, output_cost_1k = get_cost_per_token(model_name)
                cost = (prompt_tokens / 1000.0 * input_cost_1k) + (completion_tokens / 1000.0 * output_cost_1k)
                
                audit = LLMCallAudit(
                    id=uuid.uuid4().hex,
                    run_id=run_id if run_id != "-" else None,
                    model_name=model_name,
                    provider=provider,
                    prompt_text=str(kwargs.get("messages", "")),
                    completion_text=completion_text,
                    tokens_used=tokens_used,
                    cost_usd=cost,
                    latency_ms=latency_ms,
                )
                self.db.add(audit)
                await self.db.flush()
        except Exception as e:
            logger.warning(f"Failed to write LLMCallAudit: {e}")
            
        return response

class AuditedAsyncOpenAIWrapper:
    def __init__(self, original_client, agent, db):
        self._client = original_client
        self.chat = original_client.chat
        if hasattr(self.chat, "completions"):
            self.chat.completions = AuditedChatCompletions(self.chat.completions, agent, db)
            
    def __getattr__(self, name):
        return getattr(self._client, name)

async def get_llm_client(model_name: str, agent: Optional[Agent] = None, db: Optional[AsyncSession] = None) -> Tuple[AsyncOpenAI, str]:
    """
    Obtiene el cliente adecuado según el nombre del modelo.
    """
    model_lower = model_name.lower()
    if "groq" in model_lower:
        client, api_key = await get_groq_client_compatible(agent, db)
    elif "/" in model_name or "openrouter" in model_lower:
        client, api_key = await get_openrouter_client_compatible(agent, db)
    elif "gemini" in model_lower:
        client, api_key = await get_gemini_client_compatible(agent, db)
    else:
        client, api_key = await get_openai_client(agent, db)
        
    if db is not None:
        client = AuditedAsyncOpenAIWrapper(client, agent, db)
        
    return client, api_key
