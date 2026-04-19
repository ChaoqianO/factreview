"""Allow ``python -m factreview ...`` to invoke the CLI."""

from __future__ import annotations

from factreview.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
