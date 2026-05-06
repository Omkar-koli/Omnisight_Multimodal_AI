from __future__ import annotations

from typing import Any, Dict
import requests


class OmniSightAPIClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def health(self) -> Dict[str, Any]:
        url = f"{self.base_url}/health"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_decision(self, product_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/decision/{product_id}"
        response = requests.get(url, timeout=90)

        if response.status_code >= 400:
            try:
                detail = response.json()
            except Exception:
                detail = {"detail": response.text}
            raise RuntimeError(f"API error {response.status_code}: {detail}")

        return response.json()