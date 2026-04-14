"""GitHub repository checker."""

from __future__ import annotations
import logging
import os
import re
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

from .base import BaseChecker, VerifyResult

logger = logging.getLogger(__name__)


class GitHubChecker(BaseChecker):
    """Verify references that point to GitHub repositories."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.headers: Dict[str, str] = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    def verify_reference(self, ref: Dict[str, Any]) -> VerifyResult:
        import requests

        url = ref.get("url", "")
        info = self.extract_repo_info(url)
        if not info:
            return None, [], None

        owner, repo = info
        try:
            r = requests.get(
                f"https://api.github.com/repos/{owner}/{repo}",
                headers=self.headers, timeout=15,
            )
            if r.status_code != 200:
                return None, [], None

            data = r.json()
            verified = {
                "title": data.get("name", ""),
                "description": data.get("description", ""),
                "authors": [data.get("owner", {}).get("login", "")],
                "url": data.get("html_url", ""),
                "year": (data.get("created_at") or "")[:4],
            }
            return verified, [], data.get("html_url")

        except Exception as e:
            logger.debug("GitHub API error: %s", e)
            return None, [], None

    @staticmethod
    def extract_repo_info(url: str) -> Optional[Tuple[str, str]]:
        if "github.com" not in url:
            return None
        parsed = urlparse(url)
        parts = [p for p in parsed.path.strip("/").split("/") if p]
        if len(parts) >= 2:
            return parts[0], parts[1]
        return None

    @staticmethod
    def is_github_url(url: str) -> bool:
        return "github.com" in url
