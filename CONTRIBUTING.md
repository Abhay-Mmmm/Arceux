# Contributing to Arceux

## Running the Project Locally

See the [README](README.md) for full installation instructions. In short:

```bash
# Terminal 1 — backend
cd server && pip install -r requirements.txt && cp .env.example .env
# Add your GROQ_API_KEY to .env, then:
python main.py

# Terminal 2 — frontend
cd client && npm install && npm run dev
```

The frontend will be available at http://localhost:5173. The API docs are at http://localhost:8000/docs.

---

## Branch Naming

| Type | Pattern | Example |
|------|---------|---------|
| New feature | `feature/<name>` | `feature/alert-export-pdf` |
| Bug fix | `fix/<name>` | `fix/compliance-countdown-timer` |
| Documentation | `docs/<name>` | `docs/api-reference` |

Branch off `main`. Keep branches short-lived and focused on one thing.

---

## Submitting a Pull Request

1. Describe **what changed and why** in the PR description — not just what files were touched.
2. Include **screenshots or screen recordings** for any UI changes. The Dashboard, Alerts page, and Agent Insights page all have interactive states that are hard to reason about from a diff alone.
3. If your change affects alert detection behavior, note which signal types and rules are affected.
4. If your change touches the agent pipeline, note which agents and which signal-type routing paths are affected.

---

## Code Style

**Python (server/):**
- Follow the existing module structure — one class or responsibility per file.
- Do not add new third-party dependencies without discussion; the dependency list is already substantial and Groq rate limits make testing expensive.
- Use type hints throughout. Pydantic models are the canonical data contracts — do not pass raw dicts across module boundaries where a model exists.

**TypeScript (client/):**
- No `any` types. If you are working with backend data, extend the relevant interface in `types.ts`.
- Follow the existing component patterns — `Badge`, `Button`, `Card`, `Modal` are the UI primitives; do not introduce a new component library.
- Keep WebSocket subscriptions in `useWebSocket` hooks, not inside component `useEffect` blocks.
- New pages go in `src/pages/`, new shared components go in `src/components/ui/`.

---

## Reporting Bugs

Open a GitHub issue with:

1. **Steps to reproduce** — exactly what you did, in order.
2. **Expected behavior** — what should have happened.
3. **Actual behavior** — what happened instead (include screenshots if UI-related).
4. **Server startup logs** — copy the terminal output from when you ran `python main.py` through to the point the bug appeared. Key things to include: whether Groq keys are configured, which agents started, and any `[WARN]` or `[ERROR]` lines.
5. **Environment** — Python version, Node version, OS.
