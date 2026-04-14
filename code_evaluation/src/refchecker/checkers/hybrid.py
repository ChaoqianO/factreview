"""Hybrid checker – coordinates multiple API sources with intelligent fallback."""

from __future__ import annotations
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseChecker, VerifyResult
from ..errors import api_failure

logger = logging.getLogger(__name__)


class HybridChecker(BaseChecker):
    """Try multiple checkers in priority order with retry and fallback."""

    def __init__(
        self,
        *,
        semantic_scholar_api_key: Optional[str] = None,
        db_path: Optional[str] = None,
        contact_email: Optional[str] = None,
        enable_openalex: bool = True,
        enable_crossref: bool = True,
        enable_arxiv_citation: bool = True,
        debug_mode: bool = False,
    ):
        self.debug_mode = debug_mode
        self._checkers: Dict[str, Optional[BaseChecker]] = {}
        self.api_stats: Dict[str, Dict[str, int]] = {}

        # Initialise each checker; failures are non-fatal
        if enable_arxiv_citation:
            self._init("arxiv", lambda: _imp(".arxiv", "ArxivChecker")())
        if db_path:
            self._init("local_db", lambda: _imp(".local_db", "LocalDBChecker")(db_path))
        self._init("semantic_scholar",
                    lambda: _imp(".semantic_scholar", "SemanticScholarChecker")(semantic_scholar_api_key))
        if enable_openalex:
            self._init("openalex", lambda: _imp(".openalex", "OpenAlexChecker")(contact_email))
        if enable_crossref:
            self._init("crossref", lambda: _imp(".crossref", "CrossRefChecker")(contact_email))
        self._init("openreview", lambda: _imp(".openreview", "OpenReviewChecker")())

    # ------------------------------------------------------------------
    def verify_reference(self, ref: Dict[str, Any]) -> VerifyResult:
        url = ref.get("url", "")
        has_doi = bool(ref.get("doi") or ("doi.org" in url))
        is_arxiv = "arxiv" in url.lower() or ref.get("type") == "arxiv"

        # Build priority order
        order: List[str] = []
        if is_arxiv:
            order.append("arxiv")
        order.append("local_db")
        if has_doi:
            order.append("crossref")
        order.extend(["semantic_scholar", "openalex"])
        venue = (ref.get("venue") or ref.get("journal") or "").lower()
        if any(v in venue for v in ("iclr", "icml", "neurips", "nips", "aaai")):
            order.append("openreview")
        if not has_doi:
            order.append("crossref")

        # Deduplicate while preserving order
        seen = set()
        order = [n for n in order if not (n in seen or seen.add(n))]  # type: ignore[func-returns-value]

        # Phase 1: try each once
        incomplete: Optional[VerifyResult] = None
        for name in order:
            result = self._try(name, ref)
            if result is None:
                continue
            vd, errs, purl = result
            if vd is not None:
                if self._is_complete(vd):
                    return vd, errs, purl
                if incomplete is None:
                    incomplete = result

        # Phase 2: retry failed APIs once with short delay
        for name in order:
            stats = self.api_stats.get(name, {})
            if stats.get("last_fail"):
                time.sleep(min(1.5, 0.5))
                result = self._try(name, ref)
                if result and result[0] is not None:
                    return result

        # Phase 3: return incomplete data if available
        if incomplete:
            return incomplete
        return None, [], None

    # ------------------------------------------------------------------
    def _try(self, name: str, ref: Dict) -> Optional[VerifyResult]:
        checker = self._checkers.get(name)
        if checker is None:
            return None
        stats = self.api_stats.setdefault(name, {"success": 0, "failure": 0, "last_fail": False})
        t0 = time.time()
        try:
            vd, errs, url = checker.verify_reference(ref)
            # Treat api_failure errors as failures
            if any(e.get("error_type") == "api_failure" for e in errs):
                stats["failure"] += 1
                stats["last_fail"] = True
                return None
            success = vd is not None or len(errs) > 0
            if success:
                stats["success"] += 1
                stats["last_fail"] = False
                return vd, errs, url
            stats["failure"] += 1
            stats["last_fail"] = True
            return None
        except Exception as e:
            logger.debug("Hybrid: %s failed: %s", name, e)
            stats["failure"] += 1
            stats["last_fail"] = True
            return None

    @staticmethod
    def _is_complete(vd: Dict) -> bool:
        return bool(vd.get("authors")) and bool(vd.get("title"))

    def _init(self, name: str, factory):
        try:
            self._checkers[name] = factory()
            self.api_stats[name] = {"success": 0, "failure": 0, "last_fail": False}
        except Exception as e:
            logger.warning("HybridChecker: failed to init %s: %s", name, e)
            self._checkers[name] = None

    def get_performance_stats(self) -> Dict[str, Any]:
        return dict(self.api_stats)


def _imp(module: str, cls: str):
    """Lazy import a checker class from a sibling module."""
    import importlib
    mod = importlib.import_module(module, package=__name__.rsplit(".", 1)[0] + ".checkers")
    return getattr(mod, cls)
