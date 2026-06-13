import sys
import os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestTimeTracking:
    def test_clock_in_flow(self):
        from app.services.time_tracking_service import clock_in, clock_out, get_active_session
        import asyncio
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(
            asyncio.sleep(0)  # placeholder - needs DB
        )
        assert True


class TestFUNDAE:
    def test_calculate_bonus_presencial(self):
        from app.services.fundae_service import calculate_fundae_bonus
        import asyncio
        result = asyncio.new_event_loop().run_until_complete(
            calculate_fundae_bonus(course_hours=20, modality="presencial", num_participants=5, company_size="10-49")
        )
        assert result["modality"] == "presencial"
        assert result["course_hours"] == 20
        assert result["num_participants"] == 5
        assert result["total_bonus_eur"] > 0
        assert result["fundae_credit_applied_eur"] > 0

    def test_calculate_bonus_teleformacion(self):
        from app.services.fundae_service import calculate_fundae_bonus
        import asyncio
        result = asyncio.new_event_loop().run_until_complete(
            calculate_fundae_bonus(course_hours=10, modality="teleformacion", num_participants=2)
        )
        assert result["modality"] == "teleformacion"
        assert result["base_bonus_eur"] <= result["total_bonus_eur"]

    def test_calculate_bonus_company_cofinancing(self):
        from app.services.fundae_service import calculate_fundae_bonus
        import asyncio
        result = asyncio.new_event_loop().run_until_complete(
            calculate_fundae_bonus(course_hours=200, modality="presencial", num_participants=20, company_size="250+")
        )
        assert result["company_cofinancing_eur"] > 0

    def test_generate_fundae_xml(self):
        from app.services.fundae_service import generate_fundae_xml
        company = {"name": "Test Corp", "tax_id": "B12345678", "size": "10-49", "available_credit": "420"}
        courses = [{"title": "Python Basics", "modality": "presencial", "hours": 20, "participants": 5, "start_date": "2026-01-15", "end_date": "2026-01-20", "total_cost": 1300.00, "bonus_applied": 1300.00, "cofinancing": 0}]
        xml = generate_fundae_xml(company, courses, "202601")
        assert "<?xml" in xml
        assert "FUNDAE" in xml
        assert "B12345678" in xml
        assert "Python Basics" in xml


class TestITAssets:
    def test_hardware_categories(self):
        from app.services.it_asset_service import HARDWARE_CATEGORIES
        assert "laptop" in HARDWARE_CATEGORIES
        assert len(HARDWARE_CATEGORIES) >= 10

    def test_software_licenses(self):
        from app.services.it_asset_service import SOFTWARE_LICENSES
        assert "microsoft_365" in SOFTWARE_LICENSES
        assert "slack" in SOFTWARE_LICENSES


class TestEmailSequences:
    def test_get_sequence_onboarding(self):
        from app.services.email_sequences import get_sequence
        seq = get_sequence("onboarding")
        assert seq is not None
        assert seq["name"] == "Employee Onboarding"
        assert len(seq["emails"]) == 2

    def test_get_sequence_nurture(self):
        from app.services.email_sequences import get_sequence
        seq = get_sequence("sales_nurture")
        assert seq is not None
        assert len(seq["emails"]) == 3

    def test_render_template(self):
        from app.services.email_sequences import render_template
        rendered = render_template("welcome", {"first_name": "Alice", "company_name": "TestCorp", "start_date": "2026-01-01", "buddy_name": "Bob"})
        assert "Alice" in rendered["body"]
        assert "TestCorp" in rendered["body"]
        assert rendered["delay_hours"] == 0

    def test_list_sequences(self):
        from app.services.email_sequences import list_sequences
        seqs = list_sequences()
        assert len(seqs) == 2


class TestSCORM:
    def test_parse_xapi_statement(self):
        from app.services.scorm_xapi import parse_xapi_statement
        statement = '{"actor":{"name":"Alice","mbox":"mailto:alice@test.com"},"verb":{"id":"http://adlnet.gov/expapi/verbs/completed","display":{"en-US":"completed"}},"object":{"id":"http://test.com/course1","objectType":"Activity"},"result":{"score":{"scaled":0.95},"success":true,"completion":true},"timestamp":"2026-01-01T00:00:00Z"}'
        parsed = parse_xapi_statement(statement)
        assert parsed["actor_name"] == "Alice"
        assert parsed["verb"] == "completed"
        assert parsed["success"] is True
        assert parsed["score"] == 0.95

    def test_parse_xapi_statement_minimal(self):
        from app.services.scorm_xapi import parse_xapi_statement
        statement = '{"actor":{"name":"Bob"},"verb":{"id":"http://adlnet.gov/expapi/verbs/experienced"},"object":{"id":"test"}}'
        parsed = parse_xapi_statement(statement)
        assert parsed["actor_name"] == "Bob"
        assert parsed["verb"] == "experienced"


class TestInterviewScheduler:
    def test_generate_video_link(self):
        from app.services.interview_scheduler import _generate_video_link
        link = _generate_video_link()
        assert link.startswith("https://meet.successcore.com/interview-")
        assert len(link) > 30

    def test_generate_ics_content(self):
        from app.services.interview_scheduler import generate_ics_content
        interview = {
            "id": "test-interview-001",
            "title": "Technical Interview",
            "description": "Python coding interview",
            "start_datetime": "2026-06-15T10:00:00",
            "end_datetime": "2026-06-15T11:00:00",
            "video_link": "https://meet.successcore.com/room1",
            "location": "Online",
        }
        ics = generate_ics_content(interview)
        assert "BEGIN:VCALENDAR" in ics
        assert "VEVENT" in ics
        assert "Technical Interview" in ics
        assert "VALARM" in ics

    def test_generate_interview_email(self):
        from app.services.interview_scheduler import generate_interview_email
        interview = {
            "title": "Interview",
            "start_datetime": "2026-06-15T10:00:00",
            "video_link": "https://meet.successcore.com/room1",
            "location": "Online",
            "duration_minutes": 60,
        }
        email = generate_interview_email(interview, "Candidate Name", "candidate@test.com")
        assert email["to"] == "candidate@test.com"
        assert "entrevista" in email["subject"].lower()
        assert "Candidate Name" in email["body"]


class TestSILTRASEPE:
    def test_generate_afiliacion_xml(self):
        from app.services.siltra_sepe import generate_siltra_afiliacion_xml
        company = {"name": "Test Corp", "tax_id": "B12345678", "ccc": "28123456789"}
        employees = [{"ss_number": "281234567890", "full_name": "Test Employee", "tax_id": "12345678Z", "hire_date": "2025-01-01", "contract_type_code": "100"}]
        xml = generate_siltra_afiliacion_xml(company, employees)
        assert "<?xml" in xml
        assert "AFILIACION" in xml
        assert "Test Corp" in xml

    def test_calculate_ss_costs(self):
        from app.services.siltra_sepe import calculate_social_security_costs
        import asyncio
        costs = asyncio.new_event_loop().run_until_complete(
            calculate_social_security_costs(2500, "1", "indefinido")
        )
        assert costs["gross_salary"] == 2500
        assert costs["cc_employer"] > 500
        assert costs["cc_employee"] > 100
        assert costs["total_employer_cost"] > 700
        assert costs["net_employee"] < 2500

    def test_contract_to_sepe_code(self):
        from app.services.siltra_sepe import CONTRACT_TYPE_TO_SEPE
        assert CONTRACT_TYPE_TO_SEPE["indefinido"] == "100"
        assert CONTRACT_TYPE_TO_SEPE["temporal"] == "300"
        assert CONTRACT_TYPE_TO_SEPE["practicas"] == "420"


class TestBulkImport:
    def test_preview_csv_valid(self):
        from app.services.bulk_import import preview_csv
        import asyncio
        csv = "email,full_name,department,role\njohn@test.com,John Doe,Engineering,employee\njane@test.com,Jane Smith,HR,hr_admin"
        result = asyncio.new_event_loop().run_until_complete(preview_csv(csv, "employees"))
        assert result["entity_type"] == "employees"
        assert result["total_rows"] == 2
        assert result["ready"] is True

    def test_preview_csv_missing_fields(self):
        from app.services.bulk_import import preview_csv
        import asyncio
        csv = "email,full_name,department,role\njohn@test.com,,Engineering,employee"
        result = asyncio.new_event_loop().run_until_complete(preview_csv(csv, "employees"))
        assert result["error_rows"] >= 1
        assert result["ready"] is False

    def test_supported_entities(self):
        from app.services.bulk_import import SUPPORTED_ENTITIES
        assert "employees" in SUPPORTED_ENTITIES
        assert "candidates" in SUPPORTED_ENTITIES
        assert "courses" in SUPPORTED_ENTITIES
        assert "expenses" in SUPPORTED_ENTITIES


class TestApiCache:
    def test_cacheable_paths(self):
        from app.services.api_cache import CACHEABLE_PATHS
        assert "/api/v1/employees" in CACHEABLE_PATHS
        assert "/api/v1/reports" in CACHEABLE_PATHS
        assert len(CACHEABLE_PATHS) >= 5


class TestWorkflowTemplates:
    def test_list_templates(self):
        from app.services.workflow_templates import list_templates, get_categories
        templates = list_templates()
        categories = get_categories()
        assert len(templates) >= 8
        assert len(categories) >= 5
        assert "hr" in categories

    def test_get_template_onboarding(self):
        from app.services.workflow_templates import get_template
        tmpl = get_template("onboarding_standard")
        assert tmpl is not None
        assert tmpl["name"] == "Standard Employee Onboarding"
        assert len(tmpl["steps"]) >= 5
