import pytest


@pytest.mark.asyncio
async def test_get_templates(async_client, auth_headers):
    response = await async_client.get(
        "/api/v1/documents/templates",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "templates" in data
    assert len(data["templates"]) == 3
    template_ids = {t["id"] for t in data["templates"]}
    assert template_ids == {"offer_letter", "employment_contract", "nda"}


@pytest.mark.asyncio
async def test_preview_document(async_client, auth_headers):
    response = await async_client.post(
        "/api/v1/documents/preview",
        json={
            "template_type": "offer_letter",
            "variables": {
                "employee_name": "John Doe",
                "company_name": "Acme Inc",
                "position": "Software Engineer",
                "start_date": "2026-07-01",
                "salary": "$120,000",
            },
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "html" in data
    assert "John Doe" in data["html"]
    assert "Acme Inc" in data["html"]
