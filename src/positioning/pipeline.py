from __future__ import annotations

import os
from typing import Any

import requests

from schemas.claim import Claim, ClaimType
from schemas.paper import Paper
from schemas.positioning import LiteratureContext, NeighborMethod, NoveltyType


def _infer_family_from_title(title: str) -> str:
    t = (title or "").lower()
    if "gcn" in t or "graph convolution" in t:
        return "graph-neural-network"
    if "knowledge graph" in t or "kg" in t:
        return "knowledge-graph-embedding"
    if "transformer" in t:
        return "transformer"
    return "other"


def _infer_design_axes_from_title(title: str) -> dict[str, str]:
    t = (title or "").lower()
    axes: dict[str, str] = {}
    axes["embedding"] = "yes" if any(k in t for k in ["embedding", "representation"]) else "unknown"
    axes["message_passing"] = "yes" if any(k in t for k in ["gcn", "graph", "message passing"]) else "unknown"
    axes["efficiency"] = "yes" if any(k in t for k in ["efficient", "scalable"]) else "unknown"
    return axes


def _search_semantic_scholar(*, title: str, max_neighbors: int) -> tuple[list[dict[str, Any]], str]:
    query = (title or "").strip()
    if not query:
        return [], "missing_title"

    base_url = os.getenv("SEMANTIC_SCHOLAR_BASE_URL", "https://api.semanticscholar.org/graph/v1").rstrip("/")
    url = f"{base_url}/paper/search"
    params = {
        "query": query,
        "limit": str(max(1, min(max_neighbors, 20))),
        "fields": "title,year,citationCount,venue,url,externalIds",
    }
    headers: dict[str, str] = {}
    api_key = (os.getenv("SEMANTIC_SCHOLAR_API_KEY") or "").strip()
    if api_key:
        headers["x-api-key"] = api_key

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=20)
        resp.raise_for_status()
        payload = resp.json() if resp.content else {}
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            return [], "invalid_payload"
        return [x for x in data if isinstance(x, dict)], "ok"
    except Exception as exc:
        return [], f"search_failed: {type(exc).__name__}"


def build_literature_context(
    *,
    paper: Paper,
    claims: list[Claim],
    max_neighbors: int = 12,
) -> LiteratureContext:
    neighbors_raw, retrieval_note = _search_semantic_scholar(
        title=paper.metadata.title or paper.metadata.paper_key,
        max_neighbors=max_neighbors,
    )

    neighbors: list[NeighborMethod] = []
    for row in neighbors_raw[:max_neighbors]:
        ext = row.get("externalIds") if isinstance(row.get("externalIds"), dict) else {}
        summary = []
        if row.get("venue"):
            summary.append(str(row.get("venue")))
        if row.get("year"):
            summary.append(str(row.get("year")))
        cc = int(row.get("citationCount") or 0)
        if cc:
            summary.append(f"citations={cc}")

        title = str(row.get("title") or "").strip()
        neighbors.append(
            NeighborMethod(
                name=title or "unknown",
                family=_infer_family_from_title(title),
                arxiv_id=str(ext.get("ArXiv") or "").strip() or None,
                doi=str(ext.get("DOI") or "").strip() or None,
                semantic_scholar_id=str(row.get("paperId") or "").strip() or None,
                short_summary=" | ".join(summary),
                design_axes=_infer_design_axes_from_title(title),
            )
        )

    claim_types = {c.type for c in claims}
    if ClaimType.METHODOLOGICAL in claim_types and ClaimType.EMPIRICAL in claim_types:
        novelty = NoveltyType.NEW_COMBINATION
        rationale = "Claims contain both methodological and empirical contributions."
    elif ClaimType.METHODOLOGICAL in claim_types or ClaimType.THEORETICAL in claim_types:
        novelty = NoveltyType.NEW_MECHANISM
        rationale = "Claims emphasize methodological/theoretical novelty."
    elif ClaimType.EMPIRICAL in claim_types:
        novelty = NoveltyType.EMPIRICAL_IMPROVEMENT
        rationale = "Claims are primarily empirical improvements."
    else:
        novelty = NoveltyType.UNCLEAR
        rationale = "Insufficient claim signal for novelty typing."

    if not neighbors:
        rationale = f"{rationale} Retrieval unavailable ({retrieval_note})."

    families = sorted({n.family for n in neighbors if n.family})
    design_axes = ["embedding", "message_passing", "efficiency"]

    return LiteratureContext(
        neighbors=neighbors,
        design_axes=design_axes,
        novelty=novelty,
        novelty_rationale=rationale,
        families=families,
    )
