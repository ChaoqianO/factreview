#!/usr/bin/env python3
"""Semantic Scholar: title -> BibTeX (with fuzzy fallback)

Requirements:
- Do NOT generate BibTeX with an LLM.
- Only output BibTeX derived from Semantic Scholar Graph API responses.

Modes:
- Exact match first (case/symbol tolerant normalization).
- If no exact match is found, fall back to the most similar title from search results.

Usage:
  # Single title
  SEMANTIC_SCHOLAR_API_KEY=... ./s2_title_to_bibtex.py "Paper Title Here"

  # Batch mode: one title per line via stdin
  printf "%s\n" "Title A" "Title B" | ./s2_title_to_bibtex.py --stdin

  # Batch mode: titles from a file (one per line)
  ./s2_title_to_bibtex.py --file titles.txt

Output:
- Prints BibTeX entries. If fuzzy fallback was used, a BibTeX comment line is printed
  right before the entry:
    % MATCHED_TITLE: <title>
- Entries are separated by a blank line.

Exit codes:
  0: success
  2: missing API key
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request
import time
from difflib import SequenceMatcher


def _norm_title(s: str) -> str:
    s = (s or "").strip().lower()
    # Drop common punctuation and collapse whitespace.
    # Note: keep alphanumerics; treat most punctuation (including unicode dashes) as spaces.
    s = re.sub(r"[\s\-‐‑‒–—―_:;,.!?()\[\]{}\"'`~]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _tokenize(s: str) -> list[str]:
    s = _norm_title(s)
    if not s:
        return []
    return [t for t in s.split(" ") if t]


def _similarity(a: str, b: str) -> float:
    """Return similarity in [0,1]. Mix char-level and token-level similarity."""
    a_n = _norm_title(a)
    b_n = _norm_title(b)
    if not a_n or not b_n:
        return 0.0

    # Char-level (handles small typos/hyphens)
    char = SequenceMatcher(None, a_n, b_n).ratio()

    # Token Jaccard (robust to re-ordering / extra venue tags)
    ta = set(_tokenize(a_n))
    tb = set(_tokenize(b_n))
    jac = (len(ta & tb) / len(ta | tb)) if (ta or tb) else 0.0

    # Weighted blend
    return 0.65 * char + 0.35 * jac


def _http_get_json(url: str, headers: dict[str, str], timeout_s: int = 20, retries: int = 4) -> dict:
    """GET JSON with basic retry/backoff (handles transient 429/5xx/network errors)."""
    last_err: Exception | None = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            return json.loads(body)
        except Exception as e:
            last_err = e
            # Exponential backoff with a small base delay.
            time.sleep(0.4 * (2**i))
    if last_err:
        raise last_err
    raise RuntimeError("request failed")


def _fetch_bibtex_by_paper_id(paper_id: str, headers: dict[str, str]) -> str:
    fields = urllib.parse.quote("citationStyles")
    paper_url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}?fields={fields}"
    try:
        paper = _http_get_json(paper_url, headers=headers)
    except Exception:
        return ""
    return (((paper.get("citationStyles") or {}).get("bibtex")) or "").strip()


def _get_bibtex_for_title(title_in: str, headers: dict[str, str]) -> tuple[str, str]:
    """Return (matched_title, bibtex). Empty strings if nothing usable."""
    title_in = (title_in or "").strip()
    if not title_in:
        return "", ""

    # Search by title
    q = urllib.parse.quote(title_in)
    fields = urllib.parse.quote("title,paperId")
    search_url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={q}&limit=25&fields={fields}"

    try:
        search = _http_get_json(search_url, headers=headers)
    except Exception:
        return "", ""

    candidates = search.get("data") or []
    if not isinstance(candidates, list) or not candidates:
        return "", ""

    target_norm = _norm_title(title_in)

    # 1) Exact normalized title match first
    for c in candidates:
        t = (c.get("title") or "").strip()
        pid = c.get("paperId")
        if pid and t and _norm_title(t) == target_norm:
            bib = _fetch_bibtex_by_paper_id(pid, headers=headers)
            if bib:
                return t, bib
            return "", ""

    # 2) Fuzzy fallback: choose most similar title
    best = None
    best_score = -1.0
    for c in candidates:
        t = (c.get("title") or "").strip()
        pid = c.get("paperId")
        if not (pid and t):
            continue
        s = _similarity(title_in, t)
        if s > best_score:
            best_score = s
            best = (t, pid)

    if not best:
        return "", ""

    matched_title, pid = best
    bib = _fetch_bibtex_by_paper_id(pid, headers=headers)
    if not bib:
        return "", ""

    return matched_title, bib


def main(argv: list[str]) -> int:
    # Modes:
    # - default: treat argv[1:] as a single title (joined)
    # - --stdin: read titles from stdin, one per line
    # - --file <path>: read titles from file, one per line

    mode = "single"
    file_path = None
    args = argv[1:]
    if args[:1] == ["--stdin"]:
        mode = "stdin"
        args = args[1:]
    elif args[:1] == ["--file"] and len(args) >= 2:
        mode = "file"
        file_path = args[1]
        args = args[2:]

    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY") or os.environ.get("S2_API_KEY")
    if not api_key:
        return 2

    headers = {
        "accept": "application/json",
        "user-agent": "openclaw-s2-bibtex/1.3",
        "x-api-key": api_key,
    }

    titles: list[str] = []
    if mode == "stdin":
        titles = [ln.strip() for ln in sys.stdin.read().splitlines() if ln.strip()]
    elif mode == "file":
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                titles = [ln.strip() for ln in f.read().splitlines() if ln.strip()]
        except Exception:
            return 0
    else:
        if len(argv) < 2:
            return 0
        title_in = " ".join(argv[1:]).strip()
        if not title_in:
            return 0
        titles = [title_in]

    emit_not_found = (mode != "single")

    first = True
    for t in titles:
        matched_title, bib = _get_bibtex_for_title(t, headers=headers)
        if not bib:
            if emit_not_found:
                if not first:
                    sys.stdout.write("\n")
                sys.stdout.write(f"% NOT_FOUND: {t}\n")
                first = False
            continue

        if not first:
            sys.stdout.write("\n")
        # If not an exact normalized match, emit a comment with the chosen title.
        if _norm_title(matched_title) != _norm_title(t):
            sys.stdout.write(f"% MATCHED_TITLE: {matched_title}\n")
        sys.stdout.write(bib)
        if not bib.endswith("\n"):
            sys.stdout.write("\n")
        first = False

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
