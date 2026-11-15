"""Server-only administrative gate; never provision this token to a browser."""
import os
import secrets
from pipeline import config  # Load server .env before reading administrative settings.
from fastapi import Header, HTTPException


def require_admin(authorization: str | None = Header(default=None)):
    if os.environ.get('EXPLORER_HTTP_INGEST_ENABLED', '').lower() != 'true':
        raise HTTPException(403, 'HTTP ingestion is disabled; use pipeline.ingest')
    token = os.environ.get('EXPLORER_ADMIN_TOKEN', '')
    if not token or not secrets.compare_digest(authorization or '', 'Bearer ' + token):
        raise HTTPException(403, 'Administrator authorization required')
