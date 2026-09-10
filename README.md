# Landing Optimizer — AI Service

Python FastAPI service that generates CRO (Conversion Rate Optimizer) suggestions from a sanitized page map
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

## Production logs
- Every line is a JSON object with `timestamp`, `level`, `service`, `logger`,
	and either `event` plus queryable fields or a `message` for framework logs.
- `analyze_succeeded` / `score_succeeded`: provider/model, result counts or
	score, duration, and request ID.
- `request_failed`: HTTP status, safe reason, path, and request ID. Validation
	logs field locations only; request bodies are never logged.
- `provider_fallback`: provider/fallback names and a capped, single-line reason.
- Send `X-Request-ID` to preserve an upstream correlation ID; malformed values
	are replaced. The same ID is returned in the response header.
- Set `LOG_LEVEL` (default `INFO`). Uvicorn access logs are disabled to avoid
	duplicate/noisy health-check lines; startup and error logs remain enabled.

Prompts, page maps, metrics, bearer tokens, API keys, and generated copy are not
logged.

Use the cached module logger at the beginning of each file:

```python
from app.logging_utils import Logger

logger = Logger(__name__)

logger.info("analysis_succeeded", site_id=site_id, duration_ms=duration_ms)
logger.warn("provider_fallback", provider=provider, reason=reason)
logger.error("analysis_failed", reason=reason)
```

`Logger(name)` is thread-safe and returns the same instance for repeated calls
with that module name. Supported methods are `debug`, `info`, `warn`/`warning`,
`error`, and `exception`.

## Setup
```bash
python -m venv .venv && . .venv/Scripts/activate   # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000 --no-access-log --log-config logging.json
pytest
ruff check .
```

### Docker watch mode
From the sibling `landing-optimizer-infra` repo (Docker Compose 2.23+):

```bash
make watch
# Windows PowerShell / without make:
docker compose -f docker/docker-compose.yml -f docker/docker-compose.watch.yml up --build --watch
```

The AI service uses the Dockerfile `development` target and Uvicorn `--reload`.
Changes under `app/` synchronize immediately; logging configuration changes
restart the service; requirements and Dockerfile changes rebuild the image.
