from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class TableBlock:
    headers: list[str]
    rows: list[list[str]]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return ''


def _parse_markdown_table(block: str) -> TableBlock | None:
    lines = [ln.rstrip() for ln in block.splitlines()]
    table_lines = [ln for ln in lines if ln.strip().startswith('|') and ln.strip().endswith('|')]
    if len(table_lines) < 2:
        return None
    headers = [x.strip() for x in table_lines[0].strip().strip('|').split('|')]
    rows: list[list[str]] = []
    for ln in table_lines[1:]:
        cells = [x.strip() for x in ln.strip().strip('|').split('|')]
        if all(re.fullmatch(r':?-{3,}:?', c or '') for c in cells):
            continue
        if len(cells) < len(headers):
            cells = cells + [''] * (len(headers) - len(cells))
        rows.append(cells[: len(headers)])
    return TableBlock(headers=headers, rows=rows)


def extract_experiment_tables_from_report(md_text: str) -> dict[str, Any]:
    text = str(md_text or '')
    sec = re.search(r'(?ims)^##\s+5\.\s+Experiment\s*$\n(?P<body>.*?)(?=^##\s+|\Z)', text)
    if not sec:
        return {'main': None, 'ablation': None}
    body = sec.group('body')

    main_match = re.search(
        r'(?ims)(?:^###?\s*Main Result\s*$\n)?(?P<table>\|.*?)(?=^\s*###?\s*Ablation Result\s*$|^\s*Note\s*:|\Z)',
        body,
    )
    abl_match = re.search(
        r'(?ims)^###?\s*Ablation Result\s*$\n(?P<table>\|.*?)(?=^\s*Note\s*:|\Z)',
        body,
    )

    main_table = _parse_markdown_table(main_match.group('table')) if main_match else None
    abl_table = _parse_markdown_table(abl_match.group('table')) if abl_match else None
    return {
        'main': None
        if main_table is None
        else {'headers': main_table.headers, 'rows': main_table.rows, 'row_count': len(main_table.rows)},
        'ablation': None
        if abl_table is None
        else {'headers': abl_table.headers, 'rows': abl_table.rows, 'row_count': len(abl_table.rows)},
    }


def find_latest_code_eval_run(code_eval_root: Path, paper_key: str) -> Path | None:
    run_root = code_eval_root / 'run' / paper_key
    if not run_root.exists():
        return None
    candidates = [p for p in run_root.iterdir() if p.is_dir()]
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.name)
    return candidates[-1]


def load_code_eval_summary(run_dir: Path) -> dict[str, Any]:
    summary = run_dir / 'summary.json'
    if not summary.exists():
        return {}
    try:
        data = json.loads(_read_text(summary))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_code_eval_alignment(run_dir: Path) -> dict[str, Any]:
    path = run_dir / 'artifacts' / 'alignment' / 'alignment.json'
    if not path.exists():
        return {}
    try:
        data = json.loads(_read_text(path))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def build_reasonability_judgement(*, code_eval_summary: dict[str, Any], alignment: dict[str, Any]) -> dict[str, Any]:
    status = str(code_eval_summary.get('status') or '').strip() or 'unknown'
    matched = int(alignment.get('matched') or 0)
    failed = int(alignment.get('failed') or 0)
    extracted_targets = int(alignment.get('extracted_targets') or 0)

    if matched > 0 and failed == 0:
        verdict = 'supported_by_execution'
        rationale = 'Execution alignment matched extracted targets without reported failures.'
    elif status == 'inconclusive':
        verdict = 'inconclusive'
        rationale = 'Execution finished but baseline/alignment evidence is insufficient for a deterministic conclusion.'
    elif status in {'failed', 'error'}:
        verdict = 'not_supported'
        rationale = 'Execution pipeline failed; experimental claims cannot be validated from run outputs.'
    elif extracted_targets > 0 and matched == 0:
        verdict = 'weakly_supported'
        rationale = 'Targets were extracted but no alignment match was recorded; manual verification is recommended.'
    else:
        verdict = 'inconclusive'
        rationale = 'Insufficient structured evidence for deterministic judgement.'
    return {'verdict': verdict, 'rationale': rationale}


def generate_compare_report(
    *,
    fact_extraction_md_path: Path,
    code_eval_root: Path,
    paper_key: str,
    out_dir: Path,
) -> dict[str, Any]:
    fact_extraction_text = _read_text(fact_extraction_md_path)
    experiments = extract_experiment_tables_from_report(fact_extraction_text)

    latest_run = find_latest_code_eval_run(code_eval_root=code_eval_root, paper_key=paper_key)
    if latest_run is None:
        payload = {
            'paper_key': paper_key,
            'fact_extraction_markdown': str(fact_extraction_md_path),
            'code_eval_latest_run': None,
            'error': f'No code_evaluation run found under {code_eval_root / "run" / paper_key}',
            'fact_extraction_experiment': experiments,
        }
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / 'latest_compare.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        (out_dir / 'latest_compare.md').write_text(
            '# Code Eval Compare\n\n'
            f'- paper_key: `{paper_key}`\n'
            f'- fact_extraction_markdown: `{fact_extraction_md_path}`\n'
            f'- error: {payload["error"]}\n',
            encoding='utf-8',
        )
        return payload

    summary = load_code_eval_summary(latest_run)
    alignment = load_code_eval_alignment(latest_run)
    judge = build_reasonability_judgement(code_eval_summary=summary, alignment=alignment)

    payload = {
        'paper_key': paper_key,
        'fact_extraction_markdown': str(fact_extraction_md_path),
        'code_eval_latest_run': str(latest_run),
        'fact_extraction_experiment': experiments,
        'code_eval_summary': {
            'status': summary.get('status'),
            'attempts': summary.get('attempts'),
            'run_result_success': (summary.get('run_result') or {}).get('success') if isinstance(summary, dict) else None,
        },
        'alignment': {
            'extracted_targets': alignment.get('extracted_targets'),
            'matched': alignment.get('matched'),
            'failed': alignment.get('failed'),
            'unmatched_run_metrics': alignment.get('unmatched_run_metrics'),
        },
        'reasonability': judge,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'latest_compare.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    main_rows = ((experiments.get('main') or {}).get('row_count')) if isinstance(experiments.get('main'), dict) else None
    abl_rows = ((experiments.get('ablation') or {}).get('row_count')) if isinstance(experiments.get('ablation'), dict) else None
    md = [
        '# Code Eval Compare',
        '',
        f'- paper_key: `{paper_key}`',
        f'- fact_extraction_markdown: `{fact_extraction_md_path}`',
        f'- code_eval_latest_run: `{latest_run}`',
        '',
        '## FactExtraction Experiment Extraction',
        '',
        f'- main_result_rows: `{main_rows}`',
        f'- ablation_rows: `{abl_rows}`',
        '',
        '## Code Evaluation Execution',
        '',
        f"- status: `{(summary.get('status') if isinstance(summary, dict) else None)}`",
        f"- run_result_success: `{((summary.get('run_result') or {}).get('success') if isinstance(summary, dict) else None)}`",
        f"- alignment_extracted_targets: `{alignment.get('extracted_targets')}`",
        f"- alignment_matched: `{alignment.get('matched')}`",
        f"- alignment_failed: `{alignment.get('failed')}`",
        '',
        '## Reasonability Verdict',
        '',
        f"- verdict: `{judge['verdict']}`",
        f"- rationale: {judge['rationale']}",
        '',
    ]
    (out_dir / 'latest_compare.md').write_text('\n'.join(md), encoding='utf-8')
    return payload

