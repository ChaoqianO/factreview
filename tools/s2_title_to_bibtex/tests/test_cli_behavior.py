import os
import sys
import types

import pytest

import s2_title_to_bibtex.cli as cli


def test_missing_api_key_exits_2(monkeypatch):
    monkeypatch.delenv("SEMANTIC_SCHOLAR_API_KEY", raising=False)
    monkeypatch.delenv("S2_API_KEY", raising=False)
    rc = cli.main(["s2-title-to-bibtex", "Some Title"])
    assert rc == 2


def test_single_title_no_args_is_ok(monkeypatch, capsys):
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "k")
    rc = cli.main(["s2-title-to-bibtex"])
    out = capsys.readouterr().out
    assert rc == 0
    assert out == ""


def test_batch_emits_not_found(monkeypatch, capsys):
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "k")

    def fake_get_bibtex_for_title(title, headers):
        return "", ""

    monkeypatch.setattr(cli, "_get_bibtex_for_title", fake_get_bibtex_for_title)

    # stdin mode
    monkeypatch.setattr(sys, "stdin", types.SimpleNamespace(read=lambda: "A\nB\n"))
    rc = cli.main(["s2-title-to-bibtex", "--stdin"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "% NOT_FOUND: A" in out
    assert "% NOT_FOUND: B" in out


def test_emits_matched_title_when_fuzzy(monkeypatch, capsys):
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "k")

    def fake_get_bibtex_for_title(title, headers):
        return "Different Title", "@article{key,\n  title={X}\n}\n"

    monkeypatch.setattr(cli, "_get_bibtex_for_title", fake_get_bibtex_for_title)
    rc = cli.main(["s2-title-to-bibtex", "Original Title"])
    out = capsys.readouterr().out
    assert rc == 0
    assert out.startswith("% MATCHED_TITLE: Different Title\n")
    assert "@article{key" in out
