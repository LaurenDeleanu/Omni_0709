import logging
import os
import base64
import httpx
from app.core.config import settings

logger = logging.getLogger("successcore.docusign")

DOCUSIGN_ACCOUNT_ID = getattr(settings, "DOCUSIGN_ACCOUNT_ID", "") or os.getenv("DOCUSIGN_ACCOUNT_ID", "")
DOCUSIGN_INTEGRATION_KEY = getattr(settings, "DOCUSIGN_INTEGRATION_KEY", "") or os.getenv("DOCUSIGN_INTEGRATION_KEY", "")
DOCUSIGN_USER_ID = getattr(settings, "DOCUSIGN_USER_ID", "") or os.getenv("DOCUSIGN_USER_ID", "")
DOCUSIGN_PRIVATE_KEY_PATH = getattr(settings, "DOCUSIGN_PRIVATE_KEY_PATH", "") or os.getenv("DOCUSIGN_PRIVATE_KEY_PATH", "")
DOCUSIGN_BASE_URL = getattr(settings, "DOCUSIGN_BASE_URL", "") or os.getenv("DOCUSIGN_BASE_URL", "https://demo.docusign.net/restapi")

_configured = bool(DOCUSIGN_ACCOUNT_ID and DOCUSIGN_INTEGRATION_KEY and DOCUSIGN_USER_ID and DOCUSIGN_PRIVATE_KEY_PATH)


def _is_configured():
    if not _configured:
        raise RuntimeError(
            "DocuSign is not configured. Set DOCUSIGN_ACCOUNT_ID, DOCUSIGN_INTEGRATION_KEY, "
            "DOCUSIGN_USER_ID, DOCUSIGN_PRIVATE_KEY_PATH, and DOCUSIGN_BASE_URL env vars."
        )


def _load_private_key() -> str:
    path = DOCUSIGN_PRIVATE_KEY_PATH
    if not os.path.isabs(path):
        path = os.path.join(os.path.dirname(__file__), "..", "..", path)
    with open(path, "r") as f:
        return f.read()


def _jwt_assertion() -> str:
    import jwt as pyjwt
    import time

    private_key = _load_private_key()
    now = int(time.time())
    payload = {
        "iss": DOCUSIGN_INTEGRATION_KEY,
        "sub": DOCUSIGN_USER_ID,
        "aud": "account-d.docusign.com" if "demo" in DOCUSIGN_BASE_URL else "account.docusign.com",
        "iat": now,
        "exp": now + 3600,
        "scope": "signature impersonation",
    }
    return pyjwt.encode(payload, private_key, algorithm="RS256")


async def _get_access_token() -> str:
    assertion = _jwt_assertion()
    auth_url = (
        "https://account-d.docusign.com/oauth/token"
        if "demo" in DOCUSIGN_BASE_URL
        else "https://account.docusign.com/oauth/token"
    )
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            auth_url,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["access_token"]


async def create_envelope(signer_email: str, signer_name: str, document_title: str, file_path: str) -> dict:
    _is_configured()
    token = await _get_access_token()

    if not os.path.isabs(file_path):
        file_path = os.path.join(os.path.dirname(__file__), "..", "..", file_path)

    with open(file_path, "rb") as f:
        doc_bytes = base64.b64encode(f.read()).decode("utf-8")

    filename = os.path.basename(file_path)
    envelope = {
        "emailSubject": f"Please sign: {document_title}",
        "documents": [
            {
                "documentBase64": doc_bytes,
                "name": filename,
                "fileExtension": os.path.splitext(filename)[1].lstrip("."),
                "documentId": "1",
            }
        ],
        "recipients": {
            "signers": [
                {
                    "email": signer_email,
                    "name": signer_name,
                    "recipientId": "1",
                    "routingOrder": "1",
                    "tabs": {
                        "signHereTabs": [{"documentId": "1", "pageNumber": "1", "xPosition": "100", "yPosition": "100"}],
                        "dateSignedTabs": [{"documentId": "1", "pageNumber": "1", "xPosition": "200", "yPosition": "100"}],
                    },
                }
            ]
        },
        "status": "sent",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{DOCUSIGN_BASE_URL}/v2.1/accounts/{DOCUSIGN_ACCOUNT_ID}/envelopes",
            json=envelope,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"DocuSign envelope created: {data.get('envelopeId')}")
        return {"envelope_id": data["envelopeId"], "status": data.get("status", "sent")}


async def get_signing_url(envelope_id: str, return_url: str) -> str:
    _is_configured()
    token = await _get_access_token()

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{DOCUSIGN_BASE_URL}/v2.1/accounts/{DOCUSIGN_ACCOUNT_ID}/envelopes/{envelope_id}/views/recipient",
            json={
                "returnUrl": return_url,
                "authenticationMethod": "none",
                "email": "signer@example.com",
                "userName": "Signer",
                "recipientId": "1",
                "clientUserId": "1",
            },
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        signing_url = data.get("url", "")
        logger.info(f"Signing URL obtained for envelope {envelope_id}")
        return signing_url


async def check_envelope_status(envelope_id: str) -> str:
    _is_configured()
    token = await _get_access_token()

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{DOCUSIGN_BASE_URL}/v2.1/accounts/{DOCUSIGN_ACCOUNT_ID}/envelopes/{envelope_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status", "unknown")
        logger.info(f"Envelope {envelope_id} status: {status}")
        return status


async def download_signed_document(envelope_id: str, output_path: str) -> str:
    _is_configured()
    token = await _get_access_token()

    async with httpx.AsyncClient(timeout=60.0) as client:
        list_resp = await client.get(
            f"{DOCUSIGN_BASE_URL}/v2.1/accounts/{DOCUSIGN_ACCOUNT_ID}/envelopes/{envelope_id}/documents",
            headers={"Authorization": f"Bearer {token}"},
        )
        list_resp.raise_for_status()
        docs = list_resp.json()
        documents = docs.get("envelopeDocuments", []) if isinstance(docs, dict) else []

        if not documents:
            raise ValueError(f"No documents found in envelope {envelope_id}")

        for doc in documents:
            doc_id = doc.get("documentId", "1")
            doc_resp = await client.get(
                f"{DOCUSIGN_BASE_URL}/v2.1/accounts/{DOCUSIGN_ACCOUNT_ID}/envelopes/{envelope_id}/documents/{doc_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            doc_resp.raise_for_status()

            file_name = doc.get("name", f"signed_{envelope_id}.pdf")
            if not os.path.isabs(output_path):
                output_path = os.path.join(output_path, file_name)

            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(doc_resp.content)
            logger.info(f"Signed document saved to {output_path}")
            return output_path

    return ""
