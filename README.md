# Landing Optimizer — AI Service

Python FastAPI service that generates CRO suggestions from a sanitized page map
and aggregate metrics. Provider-agnostic (OpenAI-compatible or a deterministic
stub). **Never auto-publishes** — output is reviewed in the dashboard.

## Endpoints
- `POST /internal/analyze` → `{ model, score, suggestions[] }` (bearer-token gated)
- `POST /internal/score` → `{ score, factors }`
- `GET /health`

## Providers
| Provider | When | Notes |
| --- | --- | --- |
| `stub` | default / dev / tests | Deterministic heuristics, no network, no key. |
| `openai` | `LLM_PROVIDER=openai` + key | Any OpenAI-compatible endpoint; strict JSON; falls back to stub on error. |

## Brand guardrails
`apply_guardrails` drops suggestions containing banned words and truncates
proposed copy to `maxLength`, keeping AI output brand-safe.

## Setup
```bash
python -m venv .venv && . .venv/Scripts/activate   # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
pytest
ruff check .
```
