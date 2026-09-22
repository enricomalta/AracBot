"""Shared security and delivery helpers for Vercel Functions."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from urllib.parse import quote

import requests
import sentry_sdk
from fastapi import HTTPException, Request

from config.settings import settings


def init_sentry() -> None:
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, enable_logs=True, send_default_pii=False)


def require_bearer(request: Request, expected_secret: str) -> None:
    received = request.headers.get("authorization", "")
    expected = f"Bearer {expected_secret}"
    if not expected_secret or not hmac.compare_digest(received, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


def enqueue_hourly_cycle() -> str:
    """Durably enqueue work before responding to cron-job.org."""
    if not settings.QSTASH_TOKEN or not settings.PUBLIC_BASE_URL:
        raise RuntimeError("QSTASH_TOKEN and PUBLIC_BASE_URL must be configured")
    worker_url = f"{settings.PUBLIC_BASE_URL}/api/worker"
    response = requests.post(
        f"{settings.QSTASH_URL}/v2/publish/{quote(worker_url, safe='')}",
        headers={
            "Authorization": f"Bearer {settings.QSTASH_TOKEN}",
            "Content-Type": "application/json",
            "Upstash-Deduplication-Id": f"hourly-analysis-{time.strftime('%Y%m%d%H', time.gmtime())}",
            "Upstash-Retries": "3",
            "Upstash-Timeout": "300s",
        },
        json={"source": "cron-job.org", "requested_at": int(time.time())},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["messageId"]


def _b64url(value: bytes) -> bytes:
    return base64.urlsafe_b64encode(value).rstrip(b"=")


def verify_qstash(request: Request, raw_body: bytes) -> None:
    """Verifies QStash's signed JWT including URL and exact raw body hash."""
    signature = request.headers.get("upstash-signature", "")
    parts = signature.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="Missing QStash signature")
    signing_input = f"{parts[0]}.{parts[1]}".encode()
    valid_signature = any(
        key and hmac.compare_digest(_b64url(hmac.new(key.encode(), signing_input, hashlib.sha256).digest()).decode(), parts[2])
        for key in (settings.QSTASH_CURRENT_SIGNING_KEY, settings.QSTASH_NEXT_SIGNING_KEY)
    )
    if not valid_signature:
        raise HTTPException(status_code=401, detail="Invalid QStash signature")
    try:
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4)))
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid QStash payload") from exc
    now = time.time()
    expected_url = f"{settings.PUBLIC_BASE_URL}/api/worker"
    if payload.get("iss") != "Upstash" or payload.get("sub") != expected_url or payload.get("exp", 0) < now or payload.get("nbf", now) > now:
        raise HTTPException(status_code=401, detail="Expired or misaddressed QStash message")
    if not hmac.compare_digest(payload.get("body", ""), _b64url(hashlib.sha256(raw_body).digest()).decode()):
        raise HTTPException(status_code=401, detail="QStash body integrity check failed")


def require_authenticated_user(request: Request) -> dict:
    token = request.cookies.get(settings.AUTH_COOKIE_NAME)
    if not token or not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise HTTPException(status_code=401, detail="Authentication required")
    response = requests.get(
        f"{settings.SUPABASE_URL}/auth/v1/user",
        headers={"Authorization": f"Bearer {token}", "apikey": settings.SUPABASE_ANON_KEY}, timeout=8,
    )
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return response.json()


def require_csrf(request: Request) -> None:
    cookie = request.cookies.get(settings.CSRF_COOKIE_NAME, "")
    header = request.headers.get("x-csrf-token", "")
    if not cookie or not header or not hmac.compare_digest(cookie, header):
        raise HTTPException(status_code=403, detail="CSRF validation failed")
