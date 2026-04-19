## RefChecker

RefChecker validates reference accuracy in academic papers (ArXiv IDs/URLs, PDFs, LaTeX, or text). It can optionally use an LLM for more reliable reference extraction, then verifies metadata against authoritative sources.

### Install

- **From source (repo root)**:

```bash
pip install -e ".[llm,webui]"
```

### CLI usage

```bash
python run_refchecker.py --paper 1706.03762
```

Enable LLM (example):

```bash
python run_refchecker.py --paper 1706.03762 --llm-provider openai --llm-model gpt-4o
```

### Web UI usage

- **Backend only**:

```bash
refchecker-webui
```

Open `http://localhost:8000`.

- **Dev mode (frontend + backend)**:

```bash
cd web-ui
npm install
npm start
```

Open `http://localhost:5173`.

### `.env` (recommended for local dev)

This repo includes `env.example`. Copy/rename it to `.env` in the repo root and fill in your values locally.

- **Never commit real keys**. If a key is pasted into chat/logs, rotate it immediately.
- If you use `npm start`, `.env` changes only apply after restart:

```bash
npm start -- --restart
```

Example `.env` (placeholders):

```bash
REFCHECKER_USE_LLM=true
REFCHECKER_LLM_PROVIDER=openai
REFCHECKER_LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-REPLACE_WITH_YOUR_KEY
OPENAI_BASE_URL=https://YOUR_OPENAI_COMPATIBLE_ENDPOINT/v1
SEMANTIC_SCHOLAR_API_KEY=REPLACE_WITH_YOUR_KEY
```

### Web UI + LLM note

The Web UI enables LLM only when an **LLM config exists** (via `GET /api/llm-configs`). If the DB has none, the backend will seed a default config from `.env` on startup (dev convenience).

### Windows (PowerShell)

PowerShell uses `$env:NAME="value"` (not `export`). If you’re using `npm start`, use `npm start -- --restart` to reload `.env`.

### License

MIT (see `LICENSE`).
