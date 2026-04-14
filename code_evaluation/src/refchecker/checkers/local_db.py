"""Local SQLite database checker (offline Semantic Scholar data)."""

from __future__ import annotations
import json
import logging
import sqlite3
from typing import Any, Dict, List, Optional

from .base import BaseChecker, VerifyResult
from ..utils.titles import normalize_paper_title
from ..utils.authors import compare_authors
from ..utils.doi import extract_doi
from ..errors import validate_year, unverified

logger = logging.getLogger(__name__)


class LocalDBChecker(BaseChecker):
    """Verify references against a local Semantic Scholar SQLite database."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    # ------------------------------------------------------------------
    def verify_reference(self, reference: Dict[str, Any]) -> VerifyResult:
        title = reference.get("title", "").strip()
        authors = reference.get("authors", [])
        url = reference.get("url", "")

        # Try ArXiv ID lookup
        from ..utils.arxiv import extract_arxiv_id
        aid = extract_arxiv_id(url) if url else None
        if aid:
            row = self._query_one(
                "SELECT * FROM papers WHERE externalIds_ArXiv = ?", [aid]
            )
            if row:
                return self._validate(row, reference)

        # Try DOI lookup
        doi = extract_doi(url or "")
        if doi:
            row = self._query_one(
                "SELECT * FROM papers WHERE externalIds_DOI = ?", [doi]
            )
            if row:
                return self._validate(row, reference)

        # Try normalized title
        if title and len(title) >= 3:
            norm = normalize_paper_title(title)
            if norm and len(norm) >= 3:
                row = self._query_one(
                    "SELECT * FROM papers WHERE normalized_paper_title = ?", [norm]
                )
                if row:
                    return self._validate(row, reference)

        return None, [unverified("Not found in local database")], None

    # ------------------------------------------------------------------
    def _query_one(self, sql: str, params: list) -> Optional[sqlite3.Row]:
        try:
            cur = self.conn.cursor()
            cur.execute(sql, params)
            return cur.fetchone()
        except Exception as e:
            logger.debug("DB query failed: %s", e)
            return None

    def _validate(self, row: sqlite3.Row, ref: Dict) -> VerifyResult:
        data = dict(row)
        try:
            data["authors"] = json.loads(data.get("authors", "[]"))
        except (json.JSONDecodeError, TypeError):
            data["authors"] = []

        errors: List[Dict[str, Any]] = []
        db_authors = [a.get("name", "") for a in data["authors"] if isinstance(a, dict)]
        cited_authors = ref.get("authors", [])
        if cited_authors and db_authors:
            ok, msg = compare_authors(cited_authors, db_authors)
            if not ok:
                errors.append({"error_type": "author", "error_details": msg,
                               "ref_authors_correct": ", ".join(db_authors)})

        yw = validate_year(ref.get("year"), data.get("year"))
        if yw:
            errors.append(yw)

        s2_id = data.get("corpusid") or data.get("CorpusId")
        paper_url = f"https://api.semanticscholar.org/CorpusID:{s2_id}" if s2_id else None
        return data, errors, paper_url

    def close(self):
        self.conn.close()
