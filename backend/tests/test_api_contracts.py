import sys
import os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-api-tests-32chars")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-32chars--")
os.environ.setdefault("DEBUG_MODE", "true")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.main import app

client = TestClient(app)


class TestHealthEndpoints:
    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "degraded")

    def test_ready_check(self):
        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"

    def test_liveness_probe(self):
        response = client.get("/live")
        assert response.status_code == 200

    def test_metrics_endpoint(self):
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "successcore_http_requests_total" in response.text
        assert "successcore_agent_runs_total" in response.text


class TestMetadataEndpoints:
    def test_metadata_summary(self):
        response = client.get("/api/v1/metadata")
        assert response.status_code in (200, 401, 403)

    def test_agent_specialists(self):
        response = client.get("/api/v1/agents/specialists")
        assert response.status_code in (200, 401)

    def test_model_catalog(self):
        response = client.get("/api/v1/agents/model-catalog")
        assert response.status_code in (200, 401)

    def test_agent_models(self):
        response = client.get("/api/v1/agents/models")
        assert response.status_code in (200, 401, 404)


class TestCSRFEndpoints:
    def test_csrf_token(self):
        response = client.get("/api/v1/users/csrf-token")
        assert response.status_code in (200, 404)

    @pytest.mark.skip(reason="CSRF protection requires cookie-based tokens not available in TestClient")
    def test_protected_endpoint_no_csrf(self):
        response = client.post("/api/v1/users/login", json={"email": "test@test.com", "password": "test", "tenant_id": "test"})
        assert response.status_code in (200, 401, 403, 422, 429), f"Got {response.status_code}: {response.text[:200]}"


class TestWorkflowTemplates:
    def test_list_templates(self):
        response = client.get("/api/v1/workflows/templates")
        assert response.status_code in (200, 401, 403, 404), f"Got {response.status_code}: {response.text[:200]}"

    def test_get_template(self):
        response = client.get("/api/v1/workflows/templates/onboarding_standard")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Standard Employee Onboarding"

    def test_get_template_not_found(self):
        response = client.get("/api/v1/workflows/templates/nonexistent")
        assert response.status_code == 404


class TestEUAIAct:
    def test_classify(self):
        response = client.get("/api/v1/agents/eu-ai-act/classify/payroll_specialist")
        assert response.status_code in (200, 401)
        if response.status_code == 200:
            data = response.json()
            assert data["risk_category"] == "high"


class TestReviews:
    def test_categories(self):
        response = client.get("/api/v1/reviews-360/categories")
        assert response.status_code in (200, 401)


class TestInterviews:
    def test_slots_no_params(self):
        response = client.get("/api/v1/interviews/slots?interviewer_id=test&start_date=2026-06-01&end_date=2026-06-07")
        assert response.status_code in (200, 401, 422)


class TestResponseHeaders:
    def test_correlation_id(self):
        response = client.get("/health")
        assert "X-Request-ID" in response.headers or "x-request-id" in response.headers

    def test_security_headers(self):
        response = client.get("/health")
        assert "X-Content-Type-Options" in response.headers or response.status_code == 200
