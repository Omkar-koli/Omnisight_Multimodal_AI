from __future__ import annotations

import base64
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass
class EbayTokenCache:
    access_token: str = ""
    expires_at: float = 0.0


_TOKEN_CACHE = EbayTokenCache()


def _get_env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _get_ebay_base_url() -> str:
    env = _get_env("EBAY_ENV", "production").lower()
    if env == "sandbox":
        return "https://api.sandbox.ebay.com"
    return "https://api.ebay.com"


def _get_basic_auth_header(client_id: str, client_secret: str) -> str:
    raw = f"{client_id}:{client_secret}".encode("utf-8")
    encoded = base64.b64encode(raw).decode("utf-8")
    return f"Basic {encoded}"


def get_ebay_access_token(force_refresh: bool = False) -> str:
    global _TOKEN_CACHE

    if (
        not force_refresh
        and _TOKEN_CACHE.access_token
        and time.time() < (_TOKEN_CACHE.expires_at - 60)
    ):
        return _TOKEN_CACHE.access_token

    client_id = _get_env("EBAY_CLIENT_ID")
    client_secret = _get_env("EBAY_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError("EBAY_CLIENT_ID / EBAY_CLIENT_SECRET missing in .env")

    base_url = _get_ebay_base_url()
    token_url = f"{base_url}/identity/v1/oauth2/token"

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": _get_basic_auth_header(client_id, client_secret),
    }
    data = {
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope",
    }

    resp = requests.post(token_url, headers=headers, data=data, timeout=30)

    if not resp.ok:
        raise RuntimeError(
            f"eBay token failed: status={resp.status_code}, "
            f"env={_get_env('EBAY_ENV', 'production')}, "
            f"body={resp.text}"
        )

    payload = resp.json()
    access_token = payload["access_token"]
    expires_in = int(payload.get("expires_in", 7200))

    _TOKEN_CACHE.access_token = access_token
    _TOKEN_CACHE.expires_at = time.time() + expires_in
    return access_token


def search_ebay_items(
    query: str,
    limit: int = 10,
    marketplace_id: str | None = None,
) -> Dict[str, Any]:
    access_token = get_ebay_access_token()
    marketplace = marketplace_id or _get_env("EBAY_MARKETPLACE_ID", "EBAY_US")

    base_url = _get_ebay_base_url()
    url = f"{base_url}/buy/browse/v1/item_summary/search"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-EBAY-C-MARKETPLACE-ID": marketplace,
    }
    params = {
        "q": query,
        "limit": min(max(limit, 1), 50),
    }

    resp = requests.get(url, headers=headers, params=params, timeout=30)

    if not resp.ok:
        raise RuntimeError(
            f"eBay search failed: status={resp.status_code}, "
            f"query={query}, body={resp.text}"
        )

    return resp.json()


def normalize_ebay_results(
    query: str,
    payload: Dict[str, Any],
    category_slug: str,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for item in payload.get("itemSummaries", []) or []:
        price_value = None
        if isinstance(item.get("price"), dict):
            try:
                price_value = float(item["price"].get("value"))
            except Exception:
                price_value = None

        image_url = ""
        if isinstance(item.get("image"), dict):
            image_url = str(item["image"].get("imageUrl", "")).strip()

        title = str(item.get("title", "")).strip()
        item_id = str(item.get("itemId", "")).strip()

        rows.append(
            {
                "source_system": "ebay_browse_api",
                "external_item_id": item_id,
                "query": query,
                "category_slug": category_slug,
                "title": title,
                "price": price_value,
                "item_web_url": str(item.get("itemWebUrl", "")).strip(),
                "image_url": image_url,
                "condition": str(item.get("condition", "")).strip(),
                "buying_options": ",".join(item.get("buyingOptions", []) or []),
            }
        )

    return rows