import logging
import os
from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Request
from pydantic import BaseModel
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.services import docusign_service
from app.core.config import settings
import hmac
import hashlib
import base64

from app.api.dependencies import get_current_user
from fastapi import Depends

logger = logging.getLogger("successcore.docusign_api")

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

WEBHOOK_SECRET = os.getenv("DOCUSIGN_WEBHOOK_SECRET", settings.SECRET_KEY)


async def _verify_webhook(request: Request):
    signature = request.headers.get("X-Docusign-Signature-1")
    if not signature:
        token = request.headers.get("X-Docusign-Signature") or request.headers.get("X-Webhook-Secret")
        if not token or token != WEBHOOK_SECRET:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook secret")
        return True

    body = await request.body()
    key = WEBHOOK_SECRET.encode("utf-8")
    computed_hash = hmac.new(key, body, hashlib.sha256).digest()
    computed_signature = base64.b64encode(computed_hash).decode("utf-8")
    
    if not hmac.compare_digest(computed_signature, signature):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid HMAC signature")
    return True


class SendEnvelopeRequest(BaseModel):
    signer_email: str
    signer_name: str
    document_title: str
    file_path: str
    return_url: Optional[str] = "https://app.successcore.com/docusign/callback"


class WebhookEvent(BaseModel):
    event: str
    data: Optional[dict] = None
    envelopeId: Optional[str] = None
    status: Optional[str] = None


@router.post("/send", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def send_for_signature(request: Request, req: SendEnvelopeRequest, current_user: dict = Depends(get_current_user)):
    if not docusign_service._configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DocuSign integration is not configured. Set DOCUSIGN_ACCOUNT_ID, DOCUSIGN_INTEGRATION_KEY, DOCUSIGN_USER_ID, DOCUSIGN_PRIVATE_KEY_PATH env vars.",
        )
    try:
        envelope = await docusign_service.create_envelope(
            signer_email=req.signer_email,
            signer_name=req.signer_name,
            document_title=req.document_title,
            file_path=req.file_path,
        )
        envelope_id = envelope["envelope_id"]
    except Exception as e:
        logger.error(f"Failed to create DocuSign envelope: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    try:
        signing_url = await docusign_service.get_signing_url(envelope_id, req.return_url)
    except Exception as e:
        logger.error(f"Failed to get signing URL: {e}")
        signing_url = None

    return {
        "envelope_id": envelope_id,
        "status": envelope.get("status", "sent"),
        "signing_url": signing_url,
    }


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def docusign_webhook(event: dict, request: Request):
    await _verify_webhook(request)
    envelope_id = event.get("envelopeId") or event.get("envelope_id", "unknown")
    envelope_status = event.get("status") or event.get("event", "unknown")

    logger.info(f"DocuSign webhook received: envelope={envelope_id}, status={envelope_status}")

    if envelope_status in ("completed", "signed", "declined", "voided"):
        logger.info(f"Envelope {envelope_id} transitioned to: {envelope_status}")

    return {
        "received": True,
        "envelope_id": envelope_id,
        "status": envelope_status,
    }


@router.get("/status/{envelope_id}", status_code=status.HTTP_200_OK)
async def get_envelope_status(envelope_id: str, current_user: dict = Depends(get_current_user)):
    if not docusign_service._configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DocuSign integration is not configured.",
        )
    try:
        status_value = await docusign_service.check_envelope_status(envelope_id)
        return {"envelope_id": envelope_id, "status": status_value}
    except Exception as e:
        logger.error(f"Failed to check envelope status {envelope_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
