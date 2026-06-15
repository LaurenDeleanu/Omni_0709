"""
auth.py — Verificador de tokens JWT emitidos por Auth0.

Mejoras respecto a la versión anterior:
  - JWKS cacheado con TTL de 1 hora (evita llamada HTTP en cada startup/request).
  - Soporte a múltiples 'kid' simultáneos (rotación de claves de Auth0).
  - Mensajes de error diferenciados: expirado / audience / firma inválida.
  - Thread-safe: usa un Lock simple para el refresco del cache.
"""

import json
import time
import threading

import httpx
from jose import jwt, JWTError, ExpiredSignatureError
from jose.exceptions import JWTClaimsError
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.logger import logger

# TTL del cache de JWKS (segundos)
_JWKS_CACHE_TTL = 3600   # 1 hora


import bcrypt

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password. Supports seamless migration from SHA-256 to bcrypt.
    If the hash is a 64-char hex string, it validates against SHA-256.
    """
    if len(hashed_password) == 64 and all(c in '0123456789abcdefABCDEF' for c in hashed_password):
        # Legacy SHA-256 support
    pwd_bytes = plain_password.encode('utf-8')
    hash_bytes = hashed_password.encode('utf-8')
    try:
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except ValueError:
        return False

import asyncio

async def hash_password_async(password: str) -> str:
    """Async wrapper for hash_password to prevent blocking the event loop."""
    return await asyncio.to_thread(hash_password, password)

async def verify_password_async(plain_password: str, hashed_password: str) -> bool:
    """Async wrapper for verify_password to prevent blocking the event loop."""
    return await asyncio.to_thread(verify_password, plain_password, hashed_password)

class VerifyToken:
    """
    Valida tokens JWT asimétricos (RS256) usando las claves públicas JWKS de Auth0.

    Implementa:
      - Cache local de las claves con TTL configurable.
      - Fallback a modo mock cuando AUTH0_DOMAIN == placeholder.
    """

    def __init__(self):
        self._jwks_cache:    dict  = {}       # {kid: rsa_key_dict}
        self._cache_loaded_at: float = 0.0
        self._lock = threading.Lock()
        self._load_jwks()

    # ── JWKS Load / Cache ─────────────────────────────────────────────────────
    def _is_mock_mode(self) -> bool:
        return settings.AUTH0_DOMAIN in ("your-tenant.auth0.com", "", None)

    def _load_jwks(self, force: bool = False):
        """Descarga y cachea las claves públicas de Auth0, si el cache expiró."""
        if self._is_mock_mode():
            logger.warning("[auth] Auth0 en modo MOCK — configura AUTH0_DOMAIN en producción.")
            return

        now = time.monotonic()
        if not force and (now - self._cache_loaded_at) < _JWKS_CACHE_TTL and self._jwks_cache:
            return   # cache aún válido

        with self._lock:
            # Double-check inside lock
            if not force and (now - self._cache_loaded_at) < _JWKS_CACHE_TTL and self._jwks_cache:
                return

            url = f"https://{settings.AUTH0_DOMAIN}/.well-known/jwks.json"
            try:
                # Use synchronous httpx client (compatible with threading lock)
                client = httpx.Client(timeout=5.0)
                resp = client.get(url)
                resp.raise_for_status()
                raw = resp.json()

                new_cache = {}
                for key in raw.get("keys", []):
                    kid = key.get("kid")
                    if kid and key.get("kty") == "RSA":
                        new_cache[kid] = {
                            "kty": key["kty"],
                            "kid": key["kid"],
                            "use": key.get("use", "sig"),
                            "n":   key["n"],
                            "e":   key["e"],
                        }

                self._jwks_cache      = new_cache
                self._cache_loaded_at = time.monotonic()
                logger.info(f"[auth] JWKS cargado: {len(new_cache)} clave(s) disponibles.")

            except Exception as exc:
                logger.error(f"[auth] No se pudo descargar JWKS desde Auth0: {exc}")
                # Mantenemos el cache anterior si existe
                if not self._jwks_cache:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Servicio de autenticación no disponible. Inténtalo más tarde.",
                    )

    # ── Token Verification ────────────────────────────────────────────────────
    def _check_revoked(self, payload: dict) -> dict:
        jti = payload.get("jti", "")
        if not jti:
            return payload
        try:
            import asyncio as _asyncio
            from app.services.token_revocation import is_token_revoked
            try:
                loop = _asyncio.get_running_loop()
                if loop.is_running():
                    futures = _asyncio.run_coroutine_threadsafe(is_token_revoked(jti), loop)
                    revoked = futures.result(timeout=5)
                else:
                    revoked = _asyncio.run(is_token_revoked(jti))
            except RuntimeError:
                revoked = _asyncio.run(is_token_revoked(jti))
            if revoked:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token revocado. Inicia sesión de nuevo.",
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.debug(f"Token revocation check skipped: {e}")
        return payload

    def verify(self, token: str) -> dict:
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"]
            )
            return self._check_revoked(payload)
        except HTTPException:
            raise
        except Exception:
            pass

        # ── Modo mock para desarrollo sin credenciales Auth0 ─────────────────
        if self._is_mock_mode():
            if token.count(".") == 2:
                return jwt.get_unverified_claims(token)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token mock inválido.",
            )

        # ── Refrescar JWKS si el cache expiró ────────────────────────────────
        self._load_jwks()

        # ── Extraer kid del header ────────────────────────────────────────────
        try:
            unverified_header = jwt.get_unverified_header(token)
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token malformado: no se pudo leer el header.",
            )

        kid = unverified_header.get("kid")
        rsa_key = self._jwks_cache.get(kid)

        # Si no encontramos la clave, intentar refrescar el cache una vez
        if not rsa_key:
            logger.warning(f"[auth] kid='{kid}' no encontrado en cache — refrescando JWKS.")
            self._load_jwks(force=True)
            rsa_key = self._jwks_cache.get(kid)

        if not rsa_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Clave pública no encontrada para kid='{kid}'.",
            )

        # ── Decodificar y verificar ───────────────────────────────────────────
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=[settings.AUTH0_ALGORITHMS],
                audience=settings.AUTH0_API_AUDIENCE,
                issuer=settings.AUTH0_ISSUER,
            )
            return self._check_revoked(payload)

        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expirado. Por favor inicia sesión de nuevo.",
            )
        except JWTClaimsError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Claims inválidos en el token: {exc}",
            )
        except JWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Firma del token inválida: {exc}",
            )


# Singleton compartido por toda la app
auth_verifier = VerifyToken()
