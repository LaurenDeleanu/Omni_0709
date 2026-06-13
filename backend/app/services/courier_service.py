import base64
from trycourier import Courier
from app.core.config import settings
from app.core.logger import logger

client = None
if getattr(settings, "COURIER_AUTH_TOKEN", None):
    client = Courier(authorization_token=settings.COURIER_AUTH_TOKEN)

def send_email_with_attachment(to_email: str, subject: str, body: str, attachment_bytes: bytes, filename: str):
    """
    Envía un correo electrónico usando la API de Courier incluyendo un archivo adjunto.
    """
    if settings.COURIER_AUTH_TOKEN == "pk_test_replace_me_with_courier_key":
        logger.warning(f"Courier no configurado. Simulando envío de email a {to_email}")
        return {"message_id": "dummy_id"}
        
    try:
        # Convertir el adjunto (PDF) a Base64 según lo requiere la API
        attachment_b64 = base64.b64encode(attachment_bytes).decode('utf-8')
        
        resp = client.send_message(
            message={
                "to": {
                    "email": to_email
                },
                "content": {
                    "title": subject,
                    "body": body
                },
                "routing": {
                    "method": "single",
                    "channels": ["channel:email"]
                },
                "providers": {
                    # Generalizando el proveedor SMTP. Courier enrutará a Sendgrid, Mailgun o a la consola
                    "cahnnel:email": {
                        "override": {
                            "attachments": [
                                {
                                    "filename": filename,
                                    "contentType": "application/pdf",
                                    "data": attachment_b64
                                }
                            ]
                        }
                    }
                }
            }
        )
        logger.info(f"Correo mensual mandado a {to_email}. ID: {resp['requestId']}")
        return resp
    except Exception as e:
        logger.error(f"Error al enviar notificación con Courier: {e}")
        return None
