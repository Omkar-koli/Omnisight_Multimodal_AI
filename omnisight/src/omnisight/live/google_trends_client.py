from __future__ import annotations

import os
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")


def _get_env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def serpapi_configured() -> bool:
    return bool(_get_env("SERPAPI_API_KEY"))


def fetch_interest_over_time(keyword: str, geo: str | None = None, hl: str | None = None, date: str | None = None) -> Dict[str, Any]:
    api_key = _get_env("SERPAPI_API_KEY")
    if not api_key:
        raise ValueError("SERPAPI_API_KEY is missing in .env")

    params = {
        "engine": "google_trends",
        "q": keyword,
        "data_type": "TIMESERIES",
        "geo": geo or _get_env("SERPAPI_TRENDS_GEO", "US"),
        "hl": hl or _get_env("SERPAPI_TRENDS_HL", "en"),
        "date": date or _get_env("SERPAPI_TRENDS_TIMEFRAME", "today 3-m"),
        "api_key": api_key,
    }

    resp = requests.get("https://serpapi.com/search.json", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_related_queries(keyword: str, geo: str | None = None, hl: str | None = None, date: str | None = None) -> Dict[str, Any]:
    api_key = _get_env("SERPAPI_API_KEY")
    if not api_key:
        raise ValueError("SERPAPI_API_KEY is missing in .env")

    params = {
        "engine": "google_trends",
        "q": keyword,
        "data_type": "RELATED_QUERIES",
        "geo": geo or _get_env("SERPAPI_TRENDS_GEO", "US"),
        "hl": hl or _get_env("SERPAPI_TRENDS_HL", "en"),
        "date": date or _get_env("SERPAPI_TRENDS_TIMEFRAME", "today 3-m"),
        "api_key": api_key,
    }

    resp = requests.get("https://serpapi.com/search.json", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_trending_now(geo: str | None = None, hours: int = 24, hl: str | None = None) -> Dict[str, Any]:
    api_key = _get_env("SERPAPI_API_KEY")
    if not api_key:
        raise ValueError("SERPAPI_API_KEY is missing in .env")

    params = {
        "engine": "google_trends_trending_now",
        "geo": geo or _get_env("SERPAPI_TRENDS_GEO", "US"),
        "hours": hours,
        "hl": hl or _get_env("SERPAPI_TRENDS_HL", "en"),
        "api_key": api_key,
    }

    resp = requests.get("https://serpapi.com/search.json", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def normalize_interest_over_time(keyword: str, payload: Dict[str, Any], category_slug: str, product_id: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    timeline = (
        payload.get("interest_over_time", {}) or {}
    ).get("timeline_data", []) or []

    for point in timeline:
        captured_at = str(point.get("timestamp", "")).strip()
        values = point.get("values", []) or []

        extracted_value = 0
        if values:
            try:
                extracted_value = int(values[0].get("extracted_value", 0) or 0)
            except Exception:
                extracted_value = 0

        rows.append(
            {
                "product_id": product_id,
                "category_slug": category_slug,
                "trend_keyword": keyword,
                "captured_at": captured_at,
                "trend_index": float(extracted_value),
                "trend_change_pct": 0.0,
                "source_system": "serpapi_google_trends_timeseries",
            }
        )

    # compute pct change after timeline is built
    for i in range(1, len(rows)):
        prev = float(rows[i - 1]["trend_index"] or 0)
        curr = float(rows[i]["trend_index"] or 0)

        if prev > 0:
            rows[i]["trend_change_pct"] = round(((curr - prev) / prev) * 100, 2)
        else:
            rows[i]["trend_change_pct"] = 0.0

    return rows


def normalize_related_queries(keyword: str, payload: Dict[str, Any], category_slug: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    related = (payload.get("related_queries", {}) or {}).get("rising", []) or []
    for item in related:
        rows.append(
            {
                "category_slug": category_slug,
                "seed_keyword": keyword,
                "related_query": str(item.get("query", "")).strip(),
                "value_label": str(item.get("value", "")).strip(),
                "extracted_value": float(item.get("extracted_value", 0) or 0),
                "source_system": "serpapi_google_trends_related_queries",
            }
        )

    return rows


def normalize_trending_now(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for item in payload.get("trending_searches", []) or []:
        title = str(item.get("title", "")).strip()
        rows.append(
            {
                "title": title,
                "link": str(item.get("link", "")).strip(),
                "source_system": "serpapi_google_trends_trending_now",
            }
        )

    return rows