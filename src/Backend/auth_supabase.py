"""Supabase Auth: verify JWT from Authorization: Bearer <access_token>.

Supports HS256 (legacy SUPABASE_JWT_SECRET) and ES256 (JWKS from SUPABASE_URL or SUPABASE_JWKS_URL).
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional, Tuple

import jwt
from fastapi import Header, HTTPException
from jwt import PyJWKClient

_AUDIENCE = "authenticated"
logger = logging.getLogger(__name__)

_jwks_cache: Optional[Tuple[str, PyJWKClient]] = None


def supabase_jwt_secret() -> Optional[str]:
    s = (os.getenv("SUPABASE_JWT_SECRET") or "").strip()
    return s or None


def supabase_project_url() -> Optional[str]:
    return (os.getenv("SUPABASE_URL") or os.getenv("supabase-url") or "").strip().rstrip("/") or None


def _jwks_uri() -> Optional[str]:
    u = (os.getenv("SUPABASE_JWKS_URL") or "").strip()
    if u:
        return u
    base = supabase_project_url()
    if not base:
        return None
    return f"{base}/auth/v1/.well-known/jwks.json"


def auth_verification_enabled() -> bool:
    """True when API should require a valid Supabase access token (HS256 and/or ES256)."""
    return bool(supabase_jwt_secret()) or bool(supabase_project_url())


def _jwks_client() -> PyJWKClient:
    global _jwks_cache
    uri = _jwks_uri()
    if not uri:
        raise HTTPException(
            500,
            detail="ES256 token: set SUPABASE_URL or SUPABASE_JWKS_URL so the API can load Supabase JWKS.",
        )
    if _jwks_cache is None or _jwks_cache[0] != uri:
        _jwks_cache = (uri, PyJWKClient(uri))
        logger.info("JWKS client initialized for %s", uri)
    return _jwks_cache[1]


def _decode_payload_hs256(token: str, secret: str) -> Dict[str, Any]:
    try:
        return jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience=_AUDIENCE,
            options={"verify_signature": True, "verify_exp": True, "verify_aud": True},
        )
    except jwt.InvalidAudienceError:
        return jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"verify_signature": True, "verify_exp": True, "verify_aud": False},
        )


def _decode_payload_es256(token: str) -> Dict[str, Any]:
    client = _jwks_client()
    signing_key = client.get_signing_key_from_jwt(token)
    try:
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience=_AUDIENCE,
            options={"verify_signature": True, "verify_exp": True, "verify_aud": True},
        )
    except jwt.InvalidAudienceError:
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            options={"verify_signature": True, "verify_exp": True, "verify_aud": False},
        )


def decode_supabase_jwt(token: str) -> str:
    secret = supabase_jwt_secret()
    try:
        hdr = jwt.get_unverified_header(token)
    except jwt.PyJWTError as e:
        logger.warning("JWT unreadable header: %s", e)
        raise HTTPException(401, detail=f"Invalid token: {e}") from e

    alg = (hdr.get("alg") or "").upper()
    try:
        if alg == "HS256":
            if not secret:
                raise HTTPException(
                    500,
                    detail="HS256 token received but SUPABASE_JWT_SECRET is not set.",
                )
            payload = _decode_payload_hs256(token, secret)
        elif alg == "ES256":
            payload = _decode_payload_es256(token)
        else:
            logger.warning("Unsupported JWT alg=%s", alg)
            raise HTTPException(401, detail=f"Unsupported token algorithm: {alg}")
    except HTTPException:
        raise
    except jwt.PyJWTError as e:
        logger.warning(
            "JWT verification failed: %s | alg=%s kid=%s",
            e,
            hdr.get("alg"),
            hdr.get("kid"),
        )
        raise HTTPException(401, detail=f"Invalid or expired session: {e}") from e

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(401, detail="Token missing sub")
    return str(sub)


def get_supabase_user_sub_optional(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """
    If auth is not configured: no auth (returns None).
    If configured: require Authorization: Bearer <access_token> and return JWT sub.
    """
    if not auth_verification_enabled():
        return None
    if not authorization or not authorization.lower().startswith("bearer "):
        logger.warning(
            "Auth 401: missing or non-Bearer Authorization header (frontend must send Bearer access_token from Supabase session)"
        )
        raise HTTPException(
            401,
            detail="Authorization: Bearer <access_token> required. Sign in on the dashboard when Supabase is configured.",
        )
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        logger.warning("Auth 401: Bearer header present but token string is empty")
        raise HTTPException(401, detail="Empty Bearer token")
    sub = decode_supabase_jwt(token)
    logger.debug("Auth OK user_sub=%s", sub)
    return sub
