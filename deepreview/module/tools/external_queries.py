"""
External query helpers (search, retrieval, figure critic, etc.).
"""

from typing import Dict, List

import requests


class OpenScholarClient:
    """
    Simple client wrapper for the OpenScholar API.
    Can be swapped out to decouple retrieval from model calls.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:38015/batch_ask", timeout: int = 600):
        self.base_url = base_url
        self.timeout = timeout

    def fetch(self, questions: List[str]) -> List[Dict]:
        if not questions:
            return []
        try:
            response = requests.post(self.base_url, json={"questions": questions}, timeout=self.timeout)
            if response.status_code == 200:
                return response.json().get("results", [])
            return [{"error": f"API Error {response.status_code}", "output": "", "final_passages": ""} for _ in questions]
        except requests.RequestException as exc:  # noqa: BLE001
            return [{"error": f"RequestException: {exc}", "output": "", "final_passages": ""} for _ in questions]