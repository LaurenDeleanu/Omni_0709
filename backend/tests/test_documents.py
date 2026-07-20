import pytest


@pytest.mark.asyncio
async def test_list_documents_empty_for_unknown_user(async_client, auth_headers):
    response = await async_client.get(
        "/api/v1/documents?user_id=does-not-exist",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == {"documents": []}


@pytest.mark.asyncio
async def test_list_documents_returns_user_contracts(async_client, auth_headers, test_db):
    from app.models.user import User
    from app.models.legal import Contract

    user = User(email="docs-owner@test.com", full_name="Docs Owner")
    contract = Contract(title="NDA 2026", party_name="Docs Owner", status="active")
    test_db.add_all([user, contract])
    await test_db.commit()
    await test_db.refresh(user)

    response = await async_client.get(
        f"/api/v1/documents?user_id={user.id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    docs = response.json()["documents"]
    assert len(docs) == 1
    assert docs[0]["name"] == "NDA 2026"
    assert docs[0]["type"] == "contract"
    assert docs[0]["status"] == "active"


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
