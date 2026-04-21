import s2_title_to_bibtex.cli as cli


def test_norm_title_basic():
    assert cli._norm_title("  Attention-Is All You Need! ") == "attention is all you need"


def test_similarity_prefers_close_match():
    a = "Attention Is All You Need"
    b1 = "Attention Is All You Need"
    b2 = "Some Other Paper"
    assert cli._similarity(a, b1) > cli._similarity(a, b2)


def test_exact_match_path(monkeypatch):
    # Make search return exact normalized title and paperId, then paper returns bibtex.
    def fake_http_get_json(url, headers, timeout_s=20, retries=4):
        if "/paper/search" in url:
            return {
                "data": [
                    {"title": "Attention Is All You Need", "paperId": "PID1"},
                    {"title": "Other", "paperId": "PID2"},
                ]
            }
        if "/paper/PID1" in url:
            return {"citationStyles": {"bibtex": "@article{a}\n"}}
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr(cli, "_http_get_json", fake_http_get_json)

    matched, bib = cli._get_bibtex_for_title("attention is all you need", headers={"x-api-key": "k"})
    assert matched == "Attention Is All You Need"
    assert bib.startswith("@article")


def test_fuzzy_fallback_path(monkeypatch):
    def fake_http_get_json(url, headers, timeout_s=20, retries=4):
        if "/paper/search" in url:
            return {
                "data": [
                    {"title": "Attention Is All You Need", "paperId": "PID1"},
                    {"title": "Attn Is All You Need (Workshop)", "paperId": "PID2"},
                ]
            }
        # Fuzzy chooses one of them; return bibtex for both to make test robust.
        if "/paper/PID1" in url:
            return {"citationStyles": {"bibtex": "@article{p1}\n"}}
        if "/paper/PID2" in url:
            return {"citationStyles": {"bibtex": "@article{p2}\n"}}
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr(cli, "_http_get_json", fake_http_get_json)

    matched, bib = cli._get_bibtex_for_title("Attention Is All U Need", headers={"x-api-key": "k"})
    assert matched
    assert bib.startswith("@article")
