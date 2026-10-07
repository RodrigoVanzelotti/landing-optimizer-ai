# Data science handoff: Landing Optimizer AI

**Date:** 2026-10-06 · **Target repository:** `landing-optimizer-ai`

**Objective:** develop algorithms that diagnose landing-page friction, generate grounded optimization hypotheses and propose measurable experiments. Current data supports structural/copy analysis and aggregate behavioral diagnostics. Reliable treatment-effect learning requires collection and attribution fixes first.

This report describes checked-in and locally edited code, not a verified production dataset. No live schema, volumes, missingness or outcome distributions were inspected. Proposed features and evaluation procedures below are research requirements, not implemented functionality.

## 1. Available data

| Dataset / store | Grain and relevant types | Meaning and research use |
| --- | --- | --- |
| `site` / PostgreSQL | Website; `id`, `tenant_id`, domain: `TEXT`; `sampling_rate DECIMAL(4,3)`; `settings JSONB` | Scope, collection configuration and website metadata. Sampling history is not stored per event. |
| `page_map` / PostgreSQL | Latest `(site_id, url_path)`; `map JSONB`; `captured_at TIMESTAMP(3)` | Page roles, selectors, tags and short copy. Overwritten on recapture; no version history. |
| `page_snapshot` / PostgreSQL | Capture; `image BYTEA`; dimensions `INTEGER`; `nodes JSONB`; capture time `TIMESTAMP(3)` | WebP/PNG/JPEG screenshot and selector bounding boxes. Potential multimodal input; not currently sent to AI. |
| `brand_guardrail` / PostgreSQL | One site rule object; `rules JSONB` | Tone, banned words, maximum copy length and claims to preserve. |
| `conversion_goal` / PostgreSQL | Named site goal; `name TEXT`; `kind` native enum; `matcher JSONB` | Intended outcome definition: named event, URL or form submission. Not an observed outcome. |
| `events` / ClickHouse | Behavioral event; IDs `UUID`; session `String`; time `DateTime64(3)`; categories `LowCardinality(String)` | Page views, clicks, form lifecycle, visibility, attention, exposures, conversions and optional business context. |
| `mv_daily_funnel` / ClickHouse | Site/day/event category; `events UInt64` | Event totals; not an ordered session funnel. |
| `mv_section_performance` / ClickHouse | Site/day/section label; counters and duration totals `UInt64` | Section views, frustration counts and dwell. Missing path/element dimensions and incomplete event-to-section tagging. |
| `mv_experiment_stats` / ClickHouse | Site/day/experiment/variant; counters `UInt64`; value total `Float64` | Exposure and conversion totals. Current SDK conversion attribution is incomplete. |
| `experiment`, `variant`, `variant_change` / PostgreSQL | Experiment, arm, mutation; IDs/copy/selectors `TEXT`; split `DECIMAL(4,3)`; enums; targeting `JSONB` | Hypothesis, assignment configuration, control flag and proposed DOM changes. |
| `ai_suggestion`, `approval`, `audit_log` / PostgreSQL | Suggestion, review, action; text/enums/`JSONB`; times `TIMESTAMP(3)` | Generated recommendation, provider ID, review decision/reason and lifecycle provenance. No curated effectiveness labels. |

PostgreSQL IDs are UUID v7 strings stored as `TEXT`; timestamps have no SQL time-zone component. ClickHouse uses native UUIDs. Normalize IDs and UTC interpretation explicitly when joining stores. Child PostgreSQL tables often derive tenant scope through a parent. Redis contains operational caches/counters, not research data.

Operator accounts and credentials are outside the modeling feature set. The complete 16-table physical dictionary and discrepancies in `DATABASE_SCHEMA.md` are documented in [API_DATA_INVENTORY.md](../../landing-optimizer-infra/docs/API_DATA_INVENTORY.md).

### Page representation

```text
page_map.map = {
  path: string,
  counts: Record<string, integer>,
  nodes: [{role: string, selector: string, tag: string,
           text?: string, textHash?: integer}]
}
brand_guardrail.rules = {
  tone?: string, bannedWords?: string[],
  maxLength?: integer, mustKeepClaims?: string[]
}
page_snapshot.nodes = [{selector: string, role: string,
                        rect: [x, y, width, height]}]
```

SDK map roles include `hero`, `heading`, `cta`, `form`, `pricing`, `testimonials`, `faq`, `navigation`, `footer`, `section`. These are heuristic labels, not human annotations. Maps contain ≤60 transmitted nodes and ≤80 characters of text per node from the current SDK; API accepts text up to 120 characters. Text hashes indicate change; they cannot reconstruct copy. Counts may summarize more nodes than the transmitted list.

Snapshot geometry uses integer document coordinates in CSS pixels. Images are ≤3 MiB; retention pruning attempts to keep the newest 3 captures per path and 20 per site. Maps and images are not a complete HTML/CSS or historical page dataset.

### Behavioral representation

| Fields | Types | Interpretation |
| --- | --- | --- |
| `tenant_id`, `site_id`, `experiment_id`, `variant_id` | `UUID` | Scope and optional assignment; absent experiment/variant uses the nil UUID. |
| `session_id`, `page_path`, `selector` | `String` | Daily/site-scoped pseudonym, query-free path, sanitized element selector. Empty selector means unavailable. |
| `event_name`, `section_id`, `goal` | `LowCardinality(String)` | Event category, optional semantic section label, optional conversion goal name. |
| `device_category`, `browser_category`, `referrer_host` | `LowCardinality(String)` | Coarse visitor/traffic dimensions. |
| `event_time`, `event_date` | `DateTime64(3)`, `Date` | Ingestion timestamp and derived date; not original client event time. |
| `scroll_depth`, `dwell_ms`, `value` | `UInt8`, `UInt32`, `Float64` | Reached percent bucket; event-specific milliseconds; generic numeric conversion value without currency/unit. |
| `props` | `String` | Serialized sanitized JSON: capped primitives/arrays, object-valued properties discarded. Optional `company_context` payloads have no fixed business taxonomy. |

Accepted behavioral categories: `page_view`, `scroll_depth`, `cta_click`, `dead_click`, `rage_click`, `form_start`, `form_submit`, `section_view`, `hover`, `dwell`, `dropoff`, `exposure`, `conversion`, `company_context`. Arbitrary custom event names are rejected by API validation. Structural `page_map` events go to PostgreSQL.

Raw events expire after 180 days; aggregate views have no declared TTL. Aggregate queries must sum by dimensions because `SummingMergeTree` merges are asynchronous.

## 2. Current AI execution contract

FastAPI exposes service-token-protected `/internal/analyze` and `/internal/score`. The API gathers data; the AI service has no implemented database retrieval path.

| `/internal/analyze` input | Python type | Actual API scope |
| --- | --- | --- |
| `siteId` | `str` | Single website. |
| `pageMap` | `dict[str, Any]` | Most recent map across the site; empty nodes fallback. |
| `metrics.overview` | JSON object of numbers | Site-wide last 30 days: `pageViews`, `conversions`, `conversionRate`, `ctaClicks`, `formSubmits`. |
| `metrics.sections` | List of metric objects | Site-wide retained section rollups: `section`, `views`, `deadClicks`, `rageClicks`, `dwellMs`; no matching 30-day filter. |
| `guardrails` | `dict[str, Any]` | Site rules or empty object. |

The latest map may describe one path while metrics describe every path and different time windows. Screenshots, element heatmaps, raw sessions, goal definitions, cohorts, experiment results and prior reviews are not supplied by the existing analysis call.

Output: `{model: string, score: integer, suggestions: [...]}`. Each suggestion contains `kind`, `title`, `detail`, `riskLevel` and optional `selector`, `proposedValue`, `originalValue`, `expectedImpact`. Kinds: `hypothesis`, `headline`, `cta`, `friction`, `section`, `score`, `plan`; risk: `low`, `medium`, `high`. The intended score scale is 0–100, but the Pydantic integer field has no range constraint.

The API persists suggestions and records analysis score/count in audit metadata. A suggestion with selector and proposed copy can become a draft control/treatment experiment using `set_text`; current materialization selects `cta` or `headline`. Other operations are supported by experiment storage but are not expressed by the current suggestion contract. Human approval precedes publication.

### Existing algorithm behavior

- `StubProvider` supplies deterministic generic copy and rules. Its score starts at 40, adds points for hero/CTA/social-proof/FAQ presence and conversion rate >3%. Its fixed impact ranges are placeholders, not learned estimates or validated benchmarks.
- `OpenAIProvider` generates text/JSON suggestions, falling back to the stub on failure. Its prompt slices page-map/metrics/guardrail JSON to 6000/3000/2000 characters; trailing data can be lost and JSON fragments can be truncated. `/internal/score` still uses the deterministic stub.
- `apply_guardrails()` drops proposed copy containing banned-word substrings and trims length. Tone and required claims are not independently hard-validated.
- Existing API experiment reporting uses a two-proportion z-test, a 30-exposure-per-arm floor and a 0.05 threshold. These settings do not establish adequate power, valid Bernoulli outcomes or correction for repeated testing.

## 3. Measurement and label limitations

| Issue | Consequence for algorithms |
| --- | --- |
| Current local ingestion edits authorize `envelope.sid` as site ID; edge origin header is not consumed by current controllers | Normal event batches / forwarded uploads can be rejected. Confirm collection health before interpreting zero activity. These are observed working-tree issues, not confirmed deployed behavior. |
| SDK `conversion()` does not attach experiment/variant IDs; API does not enrich attribution | Default conversions are excluded from experiment rollups. Do not train lift models or trust winner labels until attribution is validated. |
| Counts are events, not unique users or deduplicated outcomes | `conversionRate = conversions / pageViews` is an event ratio and can exceed 1. A binomial model requires a defined unit and ≤1 binary outcome per unit. |
| All events in a batch share ingestion time; client `t` and `sentAt` are discarded | Exact order and latency cannot be reconstructed for tied events. Session funnels require explicit handling of ambiguous sequences. |
| Section views carry semantic roles; clicks/hover/dwell generally omit section ID | Section aggregates merge equivalent roles across paths and cannot reliably attribute frustration to individual sections. |
| No event ID, deduplication guarantee or durable retry; sampling history absent | Missing/duplicate events and sampling changes can bias counts and trends. Acknowledged collection is not evidence of complete persistence. |
| No stable cross-day identity, currency, order/customer ledger or churn labels | Longitudinal personalization, customer LTV, revenue forecasting and churn prediction need additional data. |
| `country = ''`, `is_bot = 0`; viewport/language/query are discarded | These are unavailable features, not observed geography/bot/language classifications. |
| Maps overwritten; sparse screenshots; no analysis input version/run ID | Historical feature reconstruction and exact reproduction of a recommendation are currently limited. |
| Approval, risk score, AI score and `expectedImpact` are judgment/model output | Approval can label reviewer acceptance; none of these fields proves conversion effectiveness. |

## 4. Candidate research tracks

These are candidate baselines derived from available data, not commitments to a particular model family.

| Track | Minimum input / candidate method | Evaluation target / dependency |
| --- | --- | --- |
| Structural diagnosis | Role presence/counts, short copy, brand rules; explicit rules with evidence references | Human-rated factual correctness, actionable suggestions, selector validity and claim preservation. Feasible with current payload. |
| Grounded copy generation | Original snippet, element role, verified product context, tone/claims; constrained generation | Unsupported-claim rate, semantic preservation and reviewer preference. Current payload needs business context for product-specific promises. |
| Friction prioritization | Path/window-specific clicks, views, scroll and hover; normalized event rates and evidence-based ranking | Stability across windows and expert relevance. Requires API to supply consistent element-level aggregates and denominators. |
| Behavior anomaly detection | Daily path/cohort counts with collection coverage; robust historical baseline | Alert precision and detection delay on reviewed incidents. Requires time series, seasonality handling and separation of collection failures from behavior changes. |
| Visual layout diagnosis | Screenshot, rectangles, path and capture timestamp; multimodal analysis | Human-rated layout findings grounded in the image. Requires image retrieval and capture-time alignment; no current AI image input. |
| Experiment evaluation | Verified assignment, deduplicated exposure unit, selected goal/outcome window | Treatment-effect estimate with uncertainty and predeclared decision rule. Blocked by current attribution gaps. |
| Recommendation effectiveness/ranking | Versioned suggestion inputs plus subsequent attributed experiments | Held-out uplift/decision utility. Requires reliable outcome labels and enough independently evaluated experiments. |

Do not express heuristic scores or generated impact strings as calibrated conversion probabilities. Abstain from numerical effectiveness claims when outcome evidence is absent.

## 5. Proposed analytical dataset and validation

For behavior-driven algorithms, request one feature row per **tenant × site × page path × analysis window**, with optional device/browser/referrer cohort. Add selector grain for element analysis. Preserve explicit window bounds, map/snapshot capture timestamps, goal identity and collection coverage. This is a proposed export, not the current endpoint schema.

Candidate features: role indicators/counts; snippet lengths and CTA wording; page-view counts; CTA/form/conversion event ratios; reached scroll-bucket counts; per-selector frustration counts and hover duration. Ratios must identify their denominator and unit. Page dwell, dropoff duration and hover duration measure different concepts and must not be summed as interchangeable attention.

Join rules: always retain tenant/site; normalize text/native UUIDs; map events to structure using site + path + selector; flag capture-time/content mismatch. Do not join on selector or semantic role alone. For experiments, retain control/arm, assignment unit, goal, exposure/outcome windows and repeated-exposure rules.

Before using measured outcomes:

1. Confirm live migrations and non-demo collection; profile volume, timestamp lag, missing selectors, nil assignments and goal coverage.
2. Separate unavailable measurements from observed zeros; verify attributed conversion coverage and one chosen outcome per experimental unit.
3. Align paths and time windows; inspect assignment balance, bot contamination, sampling changes and collection outages.
4. Use chronological holdouts; group related records by site/experiment to avoid leakage. Use held-out sites when claiming cross-site generalization.
5. Evaluate generation with a reviewed benchmark; evaluate experimental decisions using power, uncertainty, practical effect size and a predefined repeated-testing policy. Keep stub/fallback results distinguishable through `model` provenance.

The first deliverable should include a feature dictionary, reproducible cohort/window extraction, a simple baseline, abstention criteria and an evaluation report. Start with structural and copy quality; move to measured optimization after attribution and data-quality checks pass.

## 6. Implementation references

| File | Responsibility |
| --- | --- |
| [app/schemas.py](../app/schemas.py) | Input/output contracts and wire aliases. |
| [app/analyzer.py](../app/analyzer.py) | Provider selection and post-generation guardrails. |
| [app/providers/stub.py](../app/providers/stub.py) | Existing deterministic baseline and score. |
| [app/providers/openai_provider.py](../app/providers/openai_provider.py) | Generation prompt, truncation and fallback. |
| [API ai.service.ts](../../landing-optimizer-api/src/modules/ai/ai.service.ts) | Input assembly, persistence and experiment materialization. |
| [API analytics.service.ts](../../landing-optimizer-api/src/modules/analytics/analytics.service.ts) | Current metric queries and heatmap aggregation. |
| [API_DATA_INVENTORY.md](../../landing-optimizer-infra/docs/API_DATA_INVENTORY.md) | Full storage types, retention, ingestion evidence and schema-document discrepancies. |
