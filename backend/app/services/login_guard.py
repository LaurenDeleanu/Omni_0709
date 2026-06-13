import logging
import asyncio
from app.core.redis import get_redis

logger = logging.getLogger("successcore.login_guard")

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 900
ATTEMPT_WINDOW_SECONDS = 300


async def check_login_allowed(email: str, ip: str) -> tuple[bool, str]:
    r = await get_redis()
    if r is None:
        return True, ""

    email_key = f"login_attempts:email:{email}"
    ip_key = f"login_attempts:ip:{ip}"
    lock_key = f"login_locked:email:{email}"

    locked = await r.get(lock_key)
    if locked:
        ttl = await r.ttl(lock_key)
        return False, f"Demasiados intentos. Intenta de nuevo en {ttl} segundos."

    email_attempts = await r.get(email_key)
    ip_attempts = await r.get(ip_key)

    email_count = int(email_attempts) if email_attempts else 0
    ip_count = int(ip_attempts) if ip_attempts else 0

    if email_count >= MAX_ATTEMPTS:
        await r.setex(lock_key, LOCKOUT_SECONDS, "1")
        return False, f"Cuenta bloqueada temporalmente por {LOCKOUT_SECONDS // 60} minutos."

    if ip_count >= MAX_ATTEMPTS * 3:
        await r.setex(f"login_locked:ip:{ip}", LOCKOUT_SECONDS, "1")
        return False, f"Demasiados intentos desde esta IP. Intenta de nuevo en {LOCKOUT_SECONDS // 60} minutos."

    return True, ""


async def record_login_attempt(email: str, ip: str):
    r = await get_redis()
    if r is None:
        return

    email_key = f"login_attempts:email:{email}"
    ip_key = f"login_attempts:ip:{ip}"

    pipe = r.pipeline()
    pipe.incr(email_key)
    pipe.expire(email_key, ATTEMPT_WINDOW_SECONDS)
    pipe.incr(ip_key)
    pipe.expire(ip_key, ATTEMPT_WINDOW_SECONDS)
    await pipe.execute()


async def clear_login_attempts(email: str, ip: str):
    r = await get_redis()
    if r is None:
        return

    await r.delete(
        f"login_attempts:email:{email}",
        f"login_attempts:ip:{ip}",
        f"login_locked:email:{email}",
        f"login_locked:ip:{ip}",
    )
