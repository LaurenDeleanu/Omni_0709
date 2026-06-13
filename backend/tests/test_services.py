import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestModelRouting:
    def test_classify_domain_greeting(self):
        from app.services.model_router import classify_domain
        domain, complexity = classify_domain("hola")
        assert domain == "greeting"
        assert complexity == 1

    def test_classify_domain_payroll(self):
        from app.services.model_router import classify_domain
        domain, complexity = classify_domain("muéstrame mi nómina de junio")
        assert domain == "payroll"
        assert complexity == 5

    def test_classify_domain_employee_lookup(self):
        from app.services.model_router import classify_domain
        domain, complexity = classify_domain("buscar empleado maria")
        assert domain == "employee_lookup"
        assert complexity == 2

    def test_fast_complexity_score_simple(self):
        from app.services.model_router_fast import fast_complexity_score
        score = fast_complexity_score("hola")
        assert score <= 2.0

    def test_fast_complexity_score_complex(self):
        from app.services.model_router_fast import fast_complexity_score
        score = fast_complexity_score("procesar nómina y generar contrato legal")
        assert score >= 6.0

    def test_fast_model_route(self):
        from app.services.model_router_fast import fast_model_route
        result = fast_model_route("buscar empleado juan")
        assert result is not None
        assert result["method"] == "keyword"
        assert "selected_model" in result
        assert "tier" in result


class TestDelegationClassifier:
    def test_keyword_prefilter_payroll(self):
        from app.services.delegation_classifier import keyword_prefilter
        result = keyword_prefilter("quiero ver mi payslip del mes pasado")
        assert result is not None
        assert result["should_delegate"] is True
        assert result["agent_type"] == "payroll_specialist"

    def test_keyword_prefilter_it(self):
        from app.services.delegation_classifier import keyword_prefilter
        result = keyword_prefilter("mi ordenador no enciende, crea un ticket de IT")
        assert result is not None
        assert result["should_delegate"] is True
        assert result["agent_type"] == "it_helpdesk"

    def test_keyword_prefilter_greeting(self):
        from app.services.delegation_classifier import keyword_prefilter
        result = keyword_prefilter("hola")
        assert result is not None
        assert result["should_delegate"] is False

    def test_keyword_prefilter_recruiter(self):
        from app.services.delegation_classifier import keyword_prefilter
        result = keyword_prefilter("quiero publicar una vacante para contratar un desarrollador")
        assert result is not None
        assert result["should_delegate"] is True
        assert result["agent_type"] == "recruiter"


class TestEUAIAct:
    def test_classify_agent_risk_high(self):
        from app.services.eu_ai_act import classify_agent_risk
        import asyncio
        result = asyncio.new_event_loop().run_until_complete(classify_agent_risk("payroll_specialist"))
        assert result["risk_category"] == "high"

    def test_classify_agent_risk_limited(self):
        from app.services.eu_ai_act import classify_agent_risk
        import asyncio
        result = asyncio.new_event_loop().run_until_complete(classify_agent_risk("hr_assistant"))
        assert result["risk_category"] == "limited"

    def test_get_risk_mitigations_high(self):
        from app.services.eu_ai_act import get_risk_mitigations
        import asyncio
        mitigations = asyncio.new_event_loop().run_until_complete(get_risk_mitigations("high"))
        assert len(mitigations) >= 5
        assert any("Human oversight" in m for m in mitigations)

    def test_get_eu_ai_act_compliance_summary(self):
        from app.services.eu_ai_act import get_eu_ai_act_compliance_summary
        import asyncio
        summary = asyncio.new_event_loop().run_until_complete(get_eu_ai_act_compliance_summary("test-tenant"))
        assert summary["framework"] == "EU AI Act 2024/1689"
        assert summary["total_agent_types"] > 0


class TestSpecialistRegistry:
    def test_get_all_specialist_types(self):
        from app.services.specialist_registry import get_all_specialist_types
        types = get_all_specialist_types()
        assert len(types) == 10
        assert "hr_assistant" in types
        assert "payroll_specialist" in types

    def test_get_specialist_info(self):
        from app.services.specialist_registry import get_specialist_info
        info = get_specialist_info("recruiter")
        assert info is not None
        assert info["display_name"] == "Recruiter"
        assert info["domain"] == "recruitment"

    def test_get_specialists_summary(self):
        from app.services.specialist_registry import get_specialists_summary
        summary = get_specialists_summary()
        assert len(summary) == 10
        assert all("agent_type" in s for s in summary)
        assert all("display_name" in s for s in summary)


class TestPayslipPDF:
    def test_generate_payslip_html(self, sample_payslip_data):
        from app.services.payslip_pdf import generate_payslip_html
        html = generate_payslip_html(sample_payslip_data)
        assert "<!DOCTYPE html>" in html
        assert "María García López" in html
        assert "Salario Base" in html
        assert "RECIBO DE NÓMINA" in html
        assert "LÍQUIDO A PERCIBIR" in html

    def test_generate_payslip_html_empty(self):
        from app.services.payslip_pdf import generate_payslip_html
        empty_data = {
            "employee": {}, "company": {}, "period": {},
            "earnings": [], "deductions": [], "totals": {},
            "language": "es", "currency": "EUR",
            "issue_date": "", "generated_at": "", "payslip_id": "",
            "irpf_rate": 0, "doc_type": "NÓMINA",
        }
        html = generate_payslip_html(empty_data)
        assert "<!DOCTYPE html>" in html


class TestSEPAExport:
    def test_generate_sepa_xml(self):
        from app.services.sepa_export import generate_sepa_xml
        payments = [
            {"name": "Employee One", "iban": "ES9121000418450200051332", "bic": "CAIXESBBXXX", "amount": 2500.00, "currency": "EUR", "reference": "Salary June"},
            {"name": "Employee Two", "iban": "ES6821000418450200051333", "bic": "BBVAESMMXXX", "amount": 1800.00, "currency": "EUR", "reference": "Salary June"},
        ]
        company = {"name": "Test Corp", "tax_id": "B12345678", "iban": "ES7521000418450200051331", "bic": "SANTESMMXXX", "country": "ES", "address": "Calle Test 1"}
        xml = generate_sepa_xml(payments, company)
        assert "<?xml" in xml
        assert "pain.001.001.03" in xml
        assert "Employee One" in xml
        assert "2500.00" in xml
        assert "SEPA" in xml

    def test_generate_salary_sepa_xml(self):
        from app.services.sepa_export import generate_salary_sepa_xml
        employees = [
            {"full_name": "Ana Ruiz", "iban": "ES9121000418450200051332", "bic": "CAIXESBBXXX", "net_pay": 2000.00, "currency": "EUR"},
        ]
        company = {"name": "Test Corp", "tax_id": "B12345678", "iban": "ES7521000418450200051331", "bic": "SANTESMMXXX"}
        xml = generate_salary_sepa_xml(employees, company)
        assert "<?xml" in xml
        assert "Ana Ruiz" in xml


class TestToolTimeout:
    def test_get_tool_timeout_default(self):
        from app.services.tool_timeout import get_tool_timeout
        timeout = get_tool_timeout("unknown_tool")
        assert timeout == 15.0

    def test_get_tool_timeout_specific(self):
        from app.services.tool_timeout import get_tool_timeout
        timeout = get_tool_timeout("process_payroll")
        assert timeout == 60.0

    def test_get_tool_timeout_negotiation(self):
        from app.services.tool_timeout import get_tool_timeout
        timeout = get_tool_timeout("negotiate_with_agents")
        assert timeout == 120.0


class TestAgentSLA:
    def test_get_sla_thresholds_high_risk(self):
        from app.services.agent_sla import get_sla_thresholds
        thresholds = get_sla_thresholds("payroll_specialist")
        assert thresholds["max_latency_ms"] == 10000
        assert thresholds["min_success_rate_pct"] == 95.0

    def test_check_sla_compliance_ok(self):
        from app.services.agent_sla import check_sla_compliance
        metrics = {"avg_latency_ms": 2000, "success_rate_pct": 95.0, "total_runs": 100, "total_cost_usd": 2.00}
        breaches = check_sla_compliance("test-id", "Test Agent", "hr_assistant", metrics)
        assert len(breaches) == 0

    def test_check_sla_compliance_breach(self):
        from app.services.agent_sla import check_sla_compliance
        metrics = {"avg_latency_ms": 6000, "success_rate_pct": 70.0, "total_runs": 100, "total_cost_usd": 10.00}
        breaches = check_sla_compliance("test-id", "Slow Agent", "hr_assistant", metrics)
        assert len(breaches) >= 2
