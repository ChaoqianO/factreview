import os

import pytest

import s2_title_to_bibtex.cli as cli


pytestmark = pytest.mark.integration


def _has_key() -> bool:
    return bool(os.environ.get("SEMANTIC_SCHOLAR_API_KEY") or os.environ.get("S2_API_KEY"))


@pytest.mark.skipif(not _has_key(), reason="SEMANTIC_SCHOLAR_API_KEY (or S2_API_KEY) not set")
def test_real_api_single_title_returns_bibtex():
    headers = {
        "accept": "application/json",
        "user-agent": "s2-title-to-bibtex-tests",
        "x-api-key": os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
        or os.environ.get("S2_API_KEY"),
    }

    matched, bib = cli._get_bibtex_for_title("Attention Is All You Need", headers=headers)
    assert matched
    assert bib
    assert bib.lstrip().startswith("@")


@pytest.mark.skipif(not _has_key(), reason="SEMANTIC_SCHOLAR_API_KEY (or S2_API_KEY) not set")
def test_real_api_cli_emits_matched_title_on_fuzzy(capsys):
    # Deliberate typo to trigger fuzzy match.
    rc = cli.main(["s2-title-to-bibtex", "Attention Is All You Ned"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "@" in out
    assert "% MATCHED_TITLE:" in out
