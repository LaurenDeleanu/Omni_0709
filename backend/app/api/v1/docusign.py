import logging
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from app.services import docusign_service

logger = logging.getLogger("successcore.docusign_api")

router = APIRouter()


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
async def send_for_signature(req: SendEnvelopeRequest):
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
async def docusign_webhook(event: dict):
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
async def get_envelope_status(envelope_id: str):
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
