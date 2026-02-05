from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str], cwd: Path | None = None, timeout_sec: int = 3600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_sec,
    )


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper-key", default="verify_paper_image")
    ap.add_argument("--python", dest="python_tag", default="3.7", help="python docker image tag, used as python:<tag>")
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()

    root = repo_root()
    verify_root = root / "run" / "_paper_image_verify"
    repo_dir = verify_root / "repo"
    run_dir = verify_root / "run"

    if verify_root.exists() and not args.keep:
        shutil.rmtree(verify_root, ignore_errors=True)
    repo_dir.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)

    # Minimal repo with pinned deps similar to old-paper scenarios.
    (repo_dir / "requirements.txt").write_text("torch==1.4.0\nnumpy==1.16.2\n", encoding="utf-8", errors="ignore")
    (repo_dir / "smoke.py").write_text("import torch\nprint(torch.__version__)\n", encoding="utf-8", errors="ignore")

    # mcp-repo-output style Dockerfile
    deployment = repo_dir / "deployment"
    deployment.mkdir(parents=True, exist_ok=True)
    dockerfile = deployment / "Dockerfile"
    dockerfile.write_text(
        f"FROM python:{args.python_tag}\n\n"
        "RUN useradd -m -u 1000 user && python -m pip install --upgrade pip\n"
        "USER user\n"
        "ENV PATH=\"/home/user/.local/bin:$PATH\"\n\n"
        "WORKDIR /app\n\n"
        "COPY --chown=user ./requirements.txt requirements.txt\n"
        "RUN pip install --no-cache-dir --upgrade -r requirements.txt\n\n"
        "COPY --chown=user . /app\n",
        encoding="utf-8",
        errors="ignore",
    )

    image = f"code-eval-paper-verify:{args.paper_key}"
    if args.rebuild:
        _run(["docker", "rmi", image], cwd=root, timeout_sec=600)

    print(f"[verify_paper_image] build image={image} python=python:{args.python_tag}")
    b = _run(["docker", "build", "-t", image, "-f", str(dockerfile), "."], cwd=repo_dir, timeout_sec=7200)
    sys.stdout.write(b.stdout)
    sys.stderr.write(b.stderr)
    if b.returncode != 0:
        return b.returncode

    print("[verify_paper_image] run import torch")
    r = _run(["docker", "run", "--rm", "-v", f"{run_dir}:/workspace/run_dir", image, "python", "smoke.py"], cwd=root, timeout_sec=1200)
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    if r.returncode != 0:
        return r.returncode

    if not args.keep:
        shutil.rmtree(verify_root, ignore_errors=True)
    print("VERIFY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


