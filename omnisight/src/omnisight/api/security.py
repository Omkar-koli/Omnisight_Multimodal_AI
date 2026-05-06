from __future__ import annotations

import os
from fastapi import Header, HTTPException
from dotenv import load_dotenv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")

INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN", "")


def require_internal_token(x_internal_api_token: str | None = Header(default=None)) -> None:
    if not INTERNAL_API_TOKEN:
        raise HTTPException(status_code=500, detail="INTERNAL_API_TOKEN not configured on backend.")

    if x_internal_api_token != INTERNAL_API_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized internal API request.")