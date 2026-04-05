# Git Commit Rules

- Only commit when explicitly asked.
- Stage specific files, never `git add -A` or `git add .`.
- Never commit .env, credentials, __pycache__, or .pyc files.
- Commit message format: imperative, 1-2 sentences on "why", not "what".
- Always end with: `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`
- Use HEREDOC for commit messages to preserve formatting.
- Never amend unless explicitly asked — always create new commits.
- Never force push. Never skip hooks.
- Before committing: run `git status`, `git diff --staged`, verify no secrets.
