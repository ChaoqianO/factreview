# Debug Workflow

When a task or run fails:

1. Read the stderr/stdout log first. Do not guess.
2. Identify the exact error line and traceback.
3. Grep the codebase for the failing function/module.
4. Read only the relevant source file(s), not the whole project.
5. Propose a minimal fix. Do not refactor surrounding code.
6. Apply the fix with Edit (not Write).
7. Re-run the failing command to verify.
8. If it still fails, report what changed and what didn't — do not loop silently.

Do not:
- Add broad try/except to suppress errors.
- "Fix" by rewriting the entire module.
- Attempt more than 2 fix iterations without reporting status.
