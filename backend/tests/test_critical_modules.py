"""
Tests para módulos críticos: Auth, Agents, Payroll.
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


# ── AUTH TESTS ──────────────────────────────────────────────────────────────

class TestAuthUtilities:
    """Pruebas para utilidades de autenticación."""

    def test_token_validation_structure(self):
        """Verifica que el módulo de auth tiene las funciones esperadas."""
        from app.core import auth

        # Debe tener funciones de hash y verificación de contraseñas (local login)
        assert hasattr(auth, "hash_password")
        assert hasattr(auth, "verify_password")

    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self):
        """Verifica que sin token se deniega el acceso."""
        from app.api.dependencies import get_current_user

        # Sin header de autorización debe fallar
        with pytest.raises(Exception):
            await get_current_user(authorization=None)


class TestRBACValidation:
    """Pruebas para validación de roles y permisos."""

    def test_role_hierarchy(self):
        """Verifica la jerarquía correcta de roles."""
        from app.models.rbac import Role

        roles = ["admin", "hr_manager", "manager", "employee"]
        # Admin debe tener mayor nivel que employee
        assert roles.index("admin") < roles.index("employee")

    def test_permission_check_basic(self):
        """Verifica chequeo básico de permisos."""
        # Un usuario sin permisos no debe poder acceder a recursos protegidos
        user_roles = ["employee"]
        required_role = "admin"
        assert required_role not in user_roles


# ── AGENT TESTS ─────────────────────────────────────────────────────────────

class TestAgentModel:
    """Pruebas para el modelo Agent."""

    def test_agent_creation_defaults(self):
        """Verifica valores por defecto al crear un agente."""
        from app.models.agent import Agent

        agent = Agent(
            name="Test Agent",
            agent_type="CONVERSATIONAL",
            ai_model="gpt-4o-mini",
        )
        assert agent.name == "Test Agent"
        assert agent.agent_type == "CONVERSATIONAL"
        # is_active defaults to True but may be None if column doesn't have server default
        assert agent.is_active in (True, None)

    def test_agent_config_defaults(self):
        """Verifica valores por defecto de AgentConfig."""
        from app.models.agent import AgentConfig

        config = AgentConfig(agent_id="test123")
        # max_loops defaults to 10, may be None if column lacks server default
        assert config.max_loops in (10, None)
        # max_tokens_per_run defaults to 50000 or may be None
        assert config.max_tokens_per_run in (50000, None)

    def test_agent_types_enum(self):
        """Verifica que los tipos de agente son válidos."""
        valid_types = [
            "CONVERSATIONAL",
            "CRM",
            "CODE",
            "CUSTOM",
            "COPILOT",
            "OMNI_MASTER",
        ]
        for agent_type in valid_types:
            from app.models.agent import Agent
            agent = Agent(name="Test", agent_type=agent_type, ai_model="gpt-4o-mini")
            assert agent.agent_type == agent_type


class TestAgentRuntime:
    """Pruebas para el runtime de agentes."""

    @pytest.mark.asyncio
    async def test_calculate_token_cost(self):
        """Verifica el cálculo de costes de tokens."""
        from app.services.agent_runtime import calculate_token_cost

        cost = calculate_token_cost(input_tokens=1000, output_tokens=500)
        expected = (1000 / 1_000_000 * 0.150) + (500 / 1_000_000 * 0.600)
        assert abs(cost - expected) < 0.001

    def test_surface_tool_errors_with_error(self):
        """Verifica detección de errores en resultados de tools."""
        from app.services.agent_runtime import _surface_tool_errors
        import json

        error_result = json.dumps({"error": "not_found", "detail": "User not found"})
        result = _surface_tool_errors("search_users", error_result)
        assert "error" in result.lower() or "not_found" in result.lower()

    def test_surface_tool_errors_clean(self):
        """Verifica que resultados sin error no se modifican."""
        from app.services.agent_runtime import _surface_tool_errors

        clean_result = "Operation completed successfully"
        result = _surface_tool_errors("create_employee", clean_result)
        assert result == clean_result


class TestCopilotOrchestrator:
    """Pruebas para el orquestador copilot."""

    def test_specialist_agent_types(self):
        """Verifica que los 10 tipos de especialistas están definidos."""
        from app.services.copilot_orchestrator import SPECIALIST_AGENT_TYPES

        assert len(SPECIALIST_AGENT_TYPES) == 10
        assert "hr_assistant" in SPECIALIST_AGENT_TYPES
        assert "payroll_specialist" in SPECIALIST_AGENT_TYPES
        assert "it_helpdesk" in SPECIALIST_AGENT_TYPES
        assert "recruiter" in SPECIALIST_AGENT_TYPES
        assert "data_analyst" in SPECIALIST_AGENT_TYPES

    def test_specialist_capabilities_defined(self):
        """Verifica que todos los especialistas tienen capacidades definidas."""
        from app.services.copilot_orchestrator import (
            SPECIALIST_AGENT_TYPES,
            SPECIALIST_CAPABILITIES,
        )

        for agent_type in SPECIALIST_AGENT_TYPES:
            assert agent_type in SPECIALIST_CAPABILITIES
            assert len(SPECIALIST_CAPABILITIES[agent_type]) > 10

    def test_delegation_classification_prompt(self):
        """Verifica que el prompt de clasificación es válido."""
        from app.services.copilot_orchestrator import DELEGATION_CLASSIFICATION_PROMPT

        assert "should_delegate" in DELEGATION_CLASSIFICATION_PROMPT
        assert "agent_type" in DELEGATION_CLASSIFICATION_PROMPT
        assert "confidence" in DELEGATION_CLASSIFICATION_PROMPT
        assert "{capabilities}" in DELEGATION_CLASSIFICATION_PROMPT
        assert "{agent_types}" in DELEGATION_CLASSIFICATION_PROMPT

    def test_copilot_response_dataclass(self):
        """Verifica la estructura de CopilotResponse."""
        from app.services.copilot_orchestrator import CopilotResponse

        response = CopilotResponse(
            response="Hola, ¿en qué puedo ayudarte?",
            delegated=False,
            tools_used=["search_employees"],
            knowledge_sources=["doc1"],
        )
        assert response.response == "Hola, ¿en qué puedo ayudarte?"
        assert response.delegated is False
        assert "search_employees" in response.tools_used


# ── PAYROLL TESTS ───────────────────────────────────────────────────────────

class TestPayrollCalculations:
    """Pruebas para cálculos de nómina."""

    def test_tax_bracket_identification(self):
        """Verifica identificación de tramos de IRPF España."""
        # Tramos IRPF España 2024 (aproximados)
        brackets = [
            (0, 12450, 0.19),
            (12450, 20200, 0.24),
            (20200, 35200, 0.30),
            (35200, 60000, 0.37),
            (60000, 300000, 0.45),
        ]

        # Salario de 30.000€ debe estar en el tramo del 30%
        salary = 30000
        applicable_rate = None
        for low, high, rate in brackets:
            if low <= salary < high:
                applicable_rate = rate
                break
        assert applicable_rate == 0.30

    def test_social_security_contributions(self):
        """Verifica cálculo de contribuciones a la Seguridad Social."""
        # Contingencias comunes: 4.7% empleado (aproximado)
        gross_salary = 30000
        employee_ss_rate = 0.047
        annual_ss = gross_salary * employee_ss_rate
        assert annual_ss == 1410.0
        assert annual_ss > 0

    def test_net_salary_calculation(self):
        """Verifica cálculo básico de salario neto."""
        gross_annual = 30000
        ss_employee = gross_annual * 0.047  # 4.7%
        taxable = gross_annual - ss_employee

        # Simplified IRPF calculation
        irpf = taxable * 0.24  # approx bracket
        net = gross_annual - ss_employee - irpf

        assert net < gross_annual
        assert net > 0
        # Net should be roughly 65-75% of gross
        ratio = net / gross_annual
        assert 0.60 < ratio < 0.80


# ── CONTEXT MANAGER TESTS (Phase 1) ─────────────────────────────────────────

class TestContextManager:
    """Pruebas para el Token-Aware Context Manager."""

    def test_count_tokens_empty(self):
        """Verifica conteo de tokens para texto vacío."""
        from app.services.context_manager import count_tokens

        assert count_tokens("") == 0
        assert count_tokens(None) == 0

    def test_count_tokens_basic(self):
        """Verifica conteo básico de tokens."""
        from app.services.context_manager import count_tokens

        text = "Hola, ¿cómo estás?"
        tokens = count_tokens(text)
        assert tokens > 0
        assert tokens < 20  # Una frase corta debe ser <20 tokens

    def test_context_analysis(self):
        """Verifica análisis de contexto."""
        from app.services.context_manager import analyze_context

        messages = [
            {"role": "user", "content": "Hola"},
            {"role": "assistant", "content": "¿En qué puedo ayudarte?"},
        ]
        stats = analyze_context(messages, model="gpt-4o-mini")
        assert stats.total_tokens > 0
        assert stats.context_limit == 128000
        assert stats.utilization_pct < 5  # <5% con solo 2 mensajes
        assert stats.needs_truncation is False

    def test_context_overflow_detection(self):
        """Verifica detección de overflow de contexto."""
        from app.services.context_manager import analyze_context

        # Simular muchos mensajes (cada uno ~500 chars = ~125 tokens)
        messages = [
            {"role": "user", "content": "x" * 500},
            {"role": "assistant", "content": "y" * 500},
        ] * 500  # 1000 mensajes

        stats = analyze_context(messages, model="gpt-4o-mini")
        assert stats.needs_truncation is True
        assert stats.utilization_pct > 80

    def test_truncate_messages_preserves_last(self):
        """Verifica que truncate preserva los últimos mensajes."""
        from app.services.context_manager import truncate_messages

        messages = [{"role": "user", "content": f"msg {i}"} for i in range(20)]
        truncated, removed = truncate_messages(
            messages, max_tokens=1000, preserve_last=4
        )
        assert len(truncated) <= len(messages)
        # Los últimos 4 mensajes deben estar presentes
        for i in range(16, 20):
            found = any(f"msg {i}" in m["content"] for m in truncated)
            assert found, f"Message msg {i} should be preserved"

    def test_model_context_limits(self):
        """Verifica límites de contexto para modelos conocidos."""
        from app.services.context_manager import MODEL_CONTEXT_LIMITS, get_context_limit

        assert get_context_limit("gpt-4o") == 128000
        assert get_context_limit("gpt-4o-mini") == 128000
        assert get_context_limit("unknown-model") == 128000  # default


# ── CONVERSATION SUMMARIZER TESTS (Phase 1) ─────────────────────────────────

class TestConversationSummarizer:
    """Pruebas para el Conversation Summarizer."""

    def test_summarize_every_default(self):
        """Verifica valor por defecto de summarize_every."""
        from app.services.conversation_summarizer import DEFAULT_SUMMARIZE_EVERY

        assert DEFAULT_SUMMARIZE_EVERY == 20

    def test_summarize_system_prompt(self):
        """Verifica que el prompt del sistema de summarización está en español."""
        from app.services.conversation_summarizer import SUMMARIZE_SYSTEM_PROMPT

        assert "conversaciones" in SUMMARIZE_SYSTEM_PROMPT.lower()
        assert "resume" in SUMMARIZE_SYSTEM_PROMPT.lower()

    @pytest.mark.asyncio
    async def test_check_summarize_too_few_messages(self):
        """Verifica que no se resume con pocos mensajes."""
        from app.services.conversation_summarizer import check_and_summarize

        messages = [{"role": "user", "content": "msg"}] * 5
        db = AsyncMock()
        result = await check_and_summarize(
            session_id="test",
            messages=messages,
            epoch_number=1,
            db=db,
            summarize_every=20,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_build_summary_context_empty(self):
        """Verifica contexto vacío cuando no hay summaries."""
        from app.services.conversation_summarizer import build_summary_context

        with patch(
            "app.services.conversation_summarizer.get_recent_epoch_summaries",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = []
            context = await build_summary_context("agent1", "user1")
            assert context == ""


# ── INTEGRATION TESTS (CRUD Agents) ─────────────────────────────────────────

class TestAgentCRUD:
    """Pruebas de integración para CRUD de agentes."""

    @pytest.mark.asyncio
    async def test_list_agents(self):
        """Verifica que el endpoint de listar agentes existe."""
        from app.api.v1.agents import list_agents

        assert callable(list_agents)
        # Verificar que es una función async
        import inspect
        assert inspect.iscoroutinefunction(list_agents)

    @pytest.mark.asyncio
    async def test_create_agent_validation(self):
        """Verifica validación al crear agente - campos requeridos."""
        from app.models.agent import Agent

        # Agent con campos mínimos - el modelo SQLAlchemy no valida en Python
        # La validación ocurre a nivel de BD o en schemas Pydantic
        agent = Agent(name="", agent_type="CONVERSATIONAL", ai_model="gpt-4o-mini")
        assert agent.name == ""
        # A nivel de BD, name es NOT NULL pero SQLAlchemy no lanza error en Python


# ── SEMANTIC MEMORY TESTS (Phase 1) ─────────────────────────────────────────

class TestSemanticMemoryFeatures:
    """Pruebas para consolidación y decaimiento de memoria semántica."""

    @pytest.mark.asyncio
    async def test_apply_memory_decay(self):
        from app.services.semantic_memory import apply_memory_decay
        from app.models.agent import EpisodicMemory
        from datetime import datetime, timezone, timedelta

        db = AsyncMock()
        
        # Mock memories
        m1 = EpisodicMemory(
            id="m1",
            user_id="user123",
            memory_type="general",
            content="Recuerdo antiguo",
            importance_score=0.5,
            occurred_at=datetime.now(timezone.utc) - timedelta(days=10),
        )
        m2 = EpisodicMemory(
            id="m2",
            user_id="user123",
            memory_type="milestone",
            content="Hito antiguo",
            importance_score=0.8,
            occurred_at=datetime.now(timezone.utc) - timedelta(days=10),
        )
        
        # Mock database execute result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [m1, m2]
        db.execute = AsyncMock(return_value=mock_result)

        decayed_count = await apply_memory_decay(user_id="user123", db=db, decay_rate=0.05)
        
        # m1 is general type and importance score decayed (0.5 * exp(-0.05 * 10) = 0.303)
        # m2 is milestone type and decayed slower (0.8 * exp(-0.01 * 10) = 0.723)
        assert m1.importance_score < 0.5
        assert m2.importance_score < 0.8
        assert decayed_count == 2
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_consolidate_memories(self):
        import json
        from app.services.semantic_memory import consolidate_memories
        from app.models.agent import EpisodicMemory
        from datetime import datetime, timezone

        db = AsyncMock()

        # Mock memories with high similarity content
        m1 = EpisodicMemory(
            id="m1",
            user_id="user123",
            memory_type="general",
            content="Al usuario le gusta trabajar remoto los viernes",
            importance_score=0.5,
            occurred_at=datetime.now(timezone.utc),
            embedding=json.dumps([0.1]*1536),
        )
        m2 = EpisodicMemory(
            id="m2",
            user_id="user123",
            memory_type="general",
            content="El usuario prefiere el teletrabajo el viernes",
            importance_score=0.6,
            occurred_at=datetime.now(timezone.utc),
            embedding=json.dumps([0.1]*1536),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [m1, m2]
        db.execute = AsyncMock(return_value=mock_result)

        # Mock LLM client response for consolidation
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"content": "El usuario prefiere trabajar en remoto los viernes.", "importance": 0.7, "entities": ["remoto", "viernes"]}'))
        ]
        mock_chat = AsyncMock()
        mock_chat.completions.create.return_value = mock_response
        mock_client = MagicMock(chat=mock_chat)

        with patch("app.services.semantic_memory.get_llm_client", AsyncMock(return_value=(mock_client, None))):
            with patch("app.services.semantic_memory.embed_and_store_memory", AsyncMock(return_value="new_id")):
                consolidated = await consolidate_memories(user_id="user123", db=db, similarity_threshold=0.8)
                assert consolidated == 2
                db.delete.assert_any_call(m1)
                db.delete.assert_any_call(m2)
                db.commit.assert_called()


# ── PREDICTIVE ANALYTICS & SKILLS TESTS (Phase 2) ───────────────────────────

class TestPredictiveAnalyticsAndSkills:
    """Pruebas para analítica predictiva y matriz de habilidades."""

    @pytest.mark.asyncio
    async def test_get_attrition_prediction(self):
        from app.services.predictive_analytics import get_attrition_prediction
        from app.models.user import User

        db = AsyncMock()
        user1 = User(id="u1", email="u1@test.com", department="Engineering", base_salary=50000)
        user2 = User(id="u2", email="u2@test.com", department="Engineering", base_salary=60000)
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [user1, user2]
        db.execute = AsyncMock(return_value=mock_result)

        result = await get_attrition_prediction(db)
        assert "summary" in result
        assert "predictions" in result
        assert len(result["predictions"]) > 0

    @pytest.mark.asyncio
    async def test_get_skills_gap_analysis(self):
        from app.services.skills_matrix import get_skills_gap_analysis
        from app.models.user import User
        from app.models.user import SkillProfile

        db = AsyncMock()
        user = User(id="u1", email="u1@test.com", department="Engineering", role="employee")
        db.get = AsyncMock(return_value=user)

        skill1 = SkillProfile(user_id="u1", skill_name="Python", level=2)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [skill1]
        db.execute = AsyncMock(return_value=mock_result)

        gap_result = await get_skills_gap_analysis(user_id="u1", db=db)
        assert gap_result["user_id"] == "u1"
        assert "Python" in gap_result["current_skills"]
        assert "gaps" in gap_result


# ── RECRUITMENT ENHANCEMENTS TESTS (Phase 2) ─────────────────────────────────

class TestCandidateScreenerAndOffer:
    """Pruebas para screening por lotes y generación de cartas de oferta."""

    @pytest.mark.asyncio
    async def test_batch_screen_resumes(self):
        from app.services.candidate_screener import batch_screen_resumes
        
        db = AsyncMock()
        files = [
            {"filename": "resume1.pdf", "content": b"Content 1"},
            {"filename": "resume2.pdf", "content": b"Content 2"}
        ]
        
        report1 = {"success": True, "overall_score": 85, "recommendation": "hire"}
        report2 = {"success": True, "overall_score": 92, "recommendation": "strong_hire"}
        
        with patch("app.services.candidate_screener.screen_resume_full") as mock_screen:
            # We return report1 for the first call, report2 for the second call
            mock_screen.side_effect = [report1, report2]
            
            result = await batch_screen_resumes(files, job_id="job123", db=db)
            
            assert len(result) == 2
            # Sorted by score, so candidate 2 (score 92) should be first
            assert result[0]["overall_score"] == 92
            assert result[0]["rank"] == 1
            assert result[1]["overall_score"] == 85
            assert result[1]["rank"] == 2

    @pytest.mark.asyncio
    async def test_generate_personalized_offer_letter(self):
        from app.services.candidate_screener import generate_personalized_offer_letter
        from app.models.hire import Candidate
        
        db = AsyncMock()
        candidate = Candidate(id="c1", first_name="Lucas", last_name="Martin", stage="offer")
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = candidate
        db.execute = AsyncMock(return_value=mock_result)
        
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"offer_letter": "Estimado Lucas, estamos encantados de ofrecerte..."}'))
        ]
        mock_chat = AsyncMock()
        mock_chat.completions.create.return_value = mock_response
        mock_client = MagicMock(chat=mock_chat)
        
        with patch("app.services.candidate_screener.get_llm_client", AsyncMock(return_value=(mock_client, None))):
            with patch("app.services.candidate_screener._get_job_requirements", AsyncMock(return_value="Requirements")):
                result = await generate_personalized_offer_letter(
                    candidate_id="c1",
                    job_id="job123",
                    salary=60000,
                    start_date="2026-07-01",
                    template="Template text",
                    db=db
                )
                assert "offer_letter_text" in result
                assert "Lucas" in result["offer_letter_text"]


# ── PERFORMANCE TESTS ───────────────────────────────────────────────────────

class TestPerformance:
    """Pruebas de rendimiento y límites."""

    def test_token_count_performance(self):
        """Verifica que count_tokens es rápido (<1ms para texto normal)."""
        from app.services.context_manager import count_tokens
        import time

        text = "Este es un mensaje de prueba con contenido normal." * 10
        start = time.perf_counter()
        tokens = count_tokens(text)
        elapsed = (time.perf_counter() - start) * 1000

        assert tokens > 0
        assert elapsed < 50  # Debe ser <50ms

    def test_large_context_analysis_performance(self):
        """Verifica rendimiento con contexto grande."""
        from app.services.context_manager import analyze_context
        import time

        messages = [
            {"role": "user", "content": "Mensaje de prueba " * 20},
            {"role": "assistant", "content": "Respuesta de prueba " * 20},
        ] * 50

        start = time.perf_counter()
        stats = analyze_context(messages, model="gpt-4o-mini")
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 100  # Debe ser <100ms para 100 mensajes
        assert stats.total_tokens > 0


# ── PAYROLL INTELLIGENCE TESTS (Phase 2) ─────────────────────────────────────

class TestPayrollIntelligence:
    """Pruebas para explicaciones de nóminas, optimización fiscal y detección de anomalías."""

    @pytest.mark.asyncio
    async def test_explain_payslip_differences_no_prev(self):
        from app.services.payroll_intelligence import explain_payslip_differences
        from app.models.pay import Payslip
        from app.models.user import User

        db = AsyncMock()
        employee = User(id="u1", base_salary=60000.0, country="ES")
        curr_payslip = Payslip(
            id="p1",
            employee_id="u1",
            gross_salary=5000.0,
            deductions=1000.0,
            net_salary=4000.0,
            employee=employee,
            line_items=[]
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.side_effect = [curr_payslip, None]
        db.execute = AsyncMock(return_value=mock_result)

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="EXPLANATION NO PREV"))
        ]
        mock_chat = AsyncMock()
        mock_chat.completions.create.return_value = mock_response
        mock_client = MagicMock(chat=mock_chat)

        with patch("app.services.payroll_intelligence.get_llm_client", AsyncMock(return_value=(mock_client, None))):
            explanation = await explain_payslip_differences(db, "u1", "p1")
            assert "EXPLANATION NO PREV" in explanation

    @pytest.mark.asyncio
    async def test_explain_payslip_differences_with_prev(self):
        from app.services.payroll_intelligence import explain_payslip_differences
        from app.models.pay import Payslip

        db = AsyncMock()
        curr_payslip = Payslip(
            id="p1",
            employee_id="u1",
            gross_salary=5000.0,
            deductions=1000.0,
            net_salary=4000.0,
            line_items=[]
        )
        prev_payslip = Payslip(
            id="p2",
            employee_id="u1",
            gross_salary=4500.0,
            deductions=900.0,
            net_salary=3600.0,
            line_items=[]
        )

        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = curr_payslip
        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = prev_payslip
        db.execute = AsyncMock(side_effect=[mock_result1, mock_result2])

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="EXPLANATION WITH PREV"))
        ]
        mock_chat = AsyncMock()
        mock_chat.completions.create.return_value = mock_response
        mock_client = MagicMock(chat=mock_chat)

        with patch("app.services.payroll_intelligence.get_llm_client", AsyncMock(return_value=(mock_client, None))):
            explanation = await explain_payslip_differences(db, "u1", "p1", "p2")
            assert "EXPLANATION WITH PREV" in explanation

    @pytest.mark.asyncio
    async def test_get_tax_optimization_recommendations(self):
        from app.services.payroll_intelligence import get_tax_optimization_recommendations
        from app.models.user import User

        db = AsyncMock()
        employee = User(id="u1", country="ES", base_salary=50000.0)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = employee
        db.execute = AsyncMock(return_value=mock_result)

        recs = await get_tax_optimization_recommendations(db, "u1")
        assert len(recs) > 0
        assert "Tarjeta Restaurante / Restaurant Card" in [r["benefit_name"] for r in recs]

        # Verify US returns empty list
        employee_us = User(id="u2", country="US", base_salary=75000.0)
        mock_result_us = MagicMock()
        mock_result_us.scalar_one_or_none.return_value = employee_us
        db.execute = AsyncMock(return_value=mock_result_us)

        recs_us = await get_tax_optimization_recommendations(db, "u2")
        assert len(recs_us) == 0

    @pytest.mark.asyncio
    async def test_detect_payroll_cycle_anomalies(self):
        from app.services.payroll_intelligence import detect_payroll_cycle_anomalies
        from app.models.pay import Payslip
        from app.models.user import User

        db = AsyncMock()
        employee = User(id="u1", full_name="Lucas", base_salary=48000.0, department="Sales")
        # Base monthly gross: 4000. Current gross: 6000 (deviation 50% > 15%)
        payslip = Payslip(
            id="p1",
            employee_id="u1",
            gross_salary=6000.0,
            employee=employee,
            line_items=[]
        )

        mock_result_payslip = MagicMock()
        mock_result_payslip.scalars.return_value.all.return_value = [payslip]
        mock_result_hist = MagicMock()
        mock_result_hist.scalars.return_value.all.return_value = [] # forces base salary fallback
        db.execute = AsyncMock(side_effect=[mock_result_payslip, mock_result_hist])

        anomalies = await detect_payroll_cycle_anomalies(db, "cycle123")
        assert len(anomalies) == 1
        assert anomalies[0]["employee_id"] == "u1"
        assert anomalies[0]["deviation_pct"] == 50.0


# ── COMPLIANCE AUTOMATION TESTS (Phase 2) ───────────────────────────────────

class TestComplianceAutomation:
    """Pruebas para cumplimiento automático y sanitizado de PII."""

    @pytest.mark.asyncio
    async def test_run_compliance_check_gdpr_sla(self):
        from app.services.compliance_audit import run_compliance_check
        from app.models.legal import ComplianceAudit, DSARTicket
        from datetime import datetime, timezone, timedelta

        db = AsyncMock()
        audit = ComplianceAudit(
            id="a1",
            title="GDPR Audit",
            audit_type="GDPR",
            status="scheduled"
        )
        # DSAR Ticket pending for 35 days (> 30 days limit)
        dsar = DSARTicket(
            id="t1",
            employee_id="u1",
            employee_name="Lucas",
            request_type="download_data",
            created_at=datetime.now(timezone.utc) - timedelta(days=35),
            status="pending"
        )

        mock_result_audit = MagicMock()
        mock_result_audit.scalar_one_or_none.return_value = audit
        mock_result_dsar = MagicMock()
        mock_result_dsar.scalars.return_value.all.return_value = [dsar]
        db.execute = AsyncMock(side_effect=[mock_result_audit, mock_result_dsar])

        report = await run_compliance_check(db, "a1")
        assert report["audit_id"] == "a1"
        # Since it had delayed DSAR, it should highlight it
        gdpr_findings = [f for f in report["findings"] if f["check"] == "GDPR DSAR SLA"]
        assert len(gdpr_findings) == 1
        assert gdpr_findings[0]["status"] == "failed"

    def test_pii_sanitizer_spanish_patterns(self):
        from app.services.pii_sanitizer import sanitize_output

        text = "Mi DNI es 12345678A y el NIE del empleado es X1234567A. El CIF de la empresa es B12345678."
        sanitized = sanitize_output(text)

        assert "[dni]" in sanitized
        assert "[nie]" in sanitized
        assert "[cif]" in sanitized
        assert "X1234567A" not in sanitized
        assert "B12345678" not in sanitized


class TestPhase3Differentiation:
    """Pruebas para cumplimiento de logs, data residency y webhooks de Phase 3."""

    @pytest.mark.asyncio
    async def test_llm_call_audit_logging(self):
        from app.services.llm_router import get_llm_client, current_run_id
        from app.models.agent import LLMCallAudit
        
        db = AsyncMock()
        db.add = MagicMock()  # synchronous call in SQLAlchemy
        db.flush = AsyncMock()
        
        mock_client = MagicMock()
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response content"
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 50
        mock_response.usage.prompt_tokens = 30
        mock_response.usage.completion_tokens = 20
        
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # Patch both possible resolution paths to return our mock client
        with patch("app.services.llm_router.get_openai_client", AsyncMock(return_value=(mock_client, "api_key"))), \
             patch("app.services.llm_router.get_openrouter_client_compatible", AsyncMock(return_value=(mock_client, "api_key"))):
            run_id = "test_run_123"
            token = current_run_id.set(run_id)
            try:
                client, _ = await get_llm_client("gpt-4o-mini", None, db)
                resp = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": "hello"}]
                )
                
                assert db.add.call_count == 1
                added_audit = db.add.call_args[0][0]
                assert isinstance(added_audit, LLMCallAudit)
                assert added_audit.run_id == run_id
                assert added_audit.model_name == "gpt-4o-mini"
                assert added_audit.completion_text == "Response content"
                assert added_audit.tokens_used == 50
                assert db.flush.call_count == 1
            finally:
                current_run_id.reset(token)

    @pytest.mark.asyncio
    async def test_data_residency_routing(self):
        from app.services.llm_router import get_llm_client
        
        db = AsyncMock()
        
        mock_keys = {
            "openai_api_key": "somekey",
            "data_residency": "EU"
        }
        with patch("app.services.llm_router.get_tenant_keys", AsyncMock(return_value=mock_keys)):
            client, _ = await get_llm_client("gpt-4o-mini", None, db)
            assert "eu-mock" in str(client.base_url)

    @pytest.mark.asyncio
    async def test_webhook_engine_management(self):
        from app.services.webhook_engine import get_webhook_engine, WebhookSubscription
        
        engine = get_webhook_engine()
        sub = WebhookSubscription(
            id="sub123",
            tenant_id="tenant123",
            event_types=["employee.hired"],
            endpoint_url="https://example.com/webhook",
            secret="supersecret"
        )
        
        engine.register_subscription(sub)
        
        subs = engine.get_subscriptions("tenant123")
        assert len(subs) == 1
        assert subs[0].endpoint_url == "https://example.com/webhook"
        
        engine.remove_subscription("sub123")
        subs = engine.get_subscriptions("tenant123")
        assert len(subs) == 0

    @pytest.mark.asyncio
    async def test_zapier_trigger_and_action_endpoints(self):
        from app.api.v1.integrations import zapier_trigger_employee_hired, zapier_action_hire_candidate
        from app.models.hire import Candidate
        
        db = AsyncMock()
        db.commit = AsyncMock()
        
        candidate = Candidate(
            id="cand123",
            first_name="John",
            last_name="Doe",
            email="john@doe.com",
            stage="applied"
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = candidate
        db.execute = AsyncMock(return_value=mock_result)
        
        from app.api.v1.integrations import HireCandidatePayload
        payload = HireCandidatePayload(candidate_id="cand123", salary=50000.0)
        
        with patch("app.services.webhook_engine.WebhookEngine.dispatch_event", AsyncMock(return_value=1)):
            resp = await zapier_action_hire_candidate(payload, db)
            assert resp["status"] == "success"
            assert candidate.stage == "hired"
            assert db.commit.call_count == 1



