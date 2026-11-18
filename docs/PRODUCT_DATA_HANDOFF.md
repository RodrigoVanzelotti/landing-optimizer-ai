# Landing Optimizer AI: product data handoff

## Product overview

**Install script → collect page structure and visitor interactions → API aggregates data → AI suggests improvements → team reviews → selected copy changes become draft experiments.**

The product helps teams identify landing-page friction and improve headlines, calls to action (CTAs) and messaging. Recommendations are hypotheses to test; publication requires human approval.

## What the website script ingests

| Data | Examples |
| --- | --- |
| Page structure and copy | Page path; detected hero, headings, CTAs, forms, pricing, testimonials and FAQs; element selectors and short text snippets. |
| Visits and engagement | Page views, scroll depth, section visibility, hover, dwell time and dropoff events. |
| Clicks and friction signals | CTA clicks, clicks on unresponsive elements and repeated rapid clicks. |
| Forms and outcomes | Form starts, submissions and instrumented conversion events. Business goals require configuration. |
| Visit context | Broad device/browser category, referring website, language, bucketed viewport and a random session identifier scoped to the browser tab and origin. |
| Experiment activity | Exposure events and experiment/variant identifiers where attached. Conversion attribution is currently incomplete. |

The page map contains up to **60 elements**, with up to **80 characters of text per element**. Roles come from explicit client labels when present, with heuristic discovery only on unlabeled pages; this is not a complete HTML/CSS capture.

### Manual client labeling (preferred)

Use dedicated **attributes**, not class names. Any `data-lo-role` anywhere in the
document switches the whole page to manual mapping, even if the value is invalid.
Only valid labeled elements enter the map, in DOM order; missing roles are not
filled by heuristics. Each element needs both `data-lo-role` and `data-lo-id`.

`data-lo-id` must be unique across the entire document, including unmarked/hidden
elements. It starts with a lowercase ASCII letter, contains only lowercase
letters, digits and hyphens, and is at most 64 characters. PII-shaped values,
whitespace, invalid IDs, duplicate IDs and unknown roles are rejected. Use stable,
descriptive IDs, never customer/visitor identifiers. Role `form` requires a native
`<form>`. One role per element; multiple elements may share a role.

| `data-lo-role` | Apply to | Example `data-lo-id` |
| --- | --- | --- |
| `navigation` | Main navigation container; optionally separate secondary navigation. | `main-navigation` |
| `hero` | Introductory section container, rather than the headline itself. | `main-hero` |
| `heading` | Each headline/subheadline whose copy should be analyzed or tested. Prefer the smallest text-only element; native h1–h3 tags are not required. | `hero-headline`, `hero-subheadline`, `pricing-headline` |
| `cta` | Each actual action link/button, including repeated hero, navigation, plan and footer CTAs. Mark the clickable element, not its section or inner icon. Use native links/buttons for accessibility. Submit inputs are supported. | `hero-signup`, `nav-demo`, `pro-plan-signup` |
| `form` | The actual `<form>` element. A div labeled as a form is rejected. Do not label individual fields. | `lead-form` |
| `pricing` | Each pricing section/table or plan card you want separately measured. Use separate IDs if labeling both a container and its cards. | `main-pricing`, `pro-plan` |
| `testimonials` | Social-proof section, review strip, customer-logo strip, or individual testimonial card to analyze separately. | `customer-proof`, `review-acme` |
| `faq` | FAQ section or individual question/answer block to analyze separately. | `main-faq`, `faq-cancellation` |
| `section` | Other relevant content: benefits, features, process, guarantees, or a small copy block that needs its own identity. | `benefits`, `how-it-works`, `guarantee-copy` |
| `footer` | Footer container. Label its CTA separately if applicable. | `main-footer` |


```html
<section data-lo-role="hero" data-lo-id="main-hero">
  <h1 data-lo-role="heading" data-lo-id="hero-headline">Seu próximo passo</h1>
  <a href="/cadastro" data-lo-role="cta" data-lo-id="hero-signup">Começar</a>
</section>
```

All mapped elements supply copy/hash, visibility and hover signals, plus geometry
during optional capture. Labels on a section and its nested copy/CTA are separate
nodes, so label each target needed for analysis or experiments. Manual CTAs have
no English-text requirement or 25-CTA cap. Only marked valid CTAs/forms produce
CTA/form events in manual mode. Generic page behavior and dead/rage clicks still
run; labeling is not an exclusive collection allowlist. `data-lo-ignore` excludes
subtrees from mapping/handlers/hover and snapshot images; ignored descendant copy
is also removed before computing a mapped ancestor's text and hash.

Selectors prefer the exact standalone form `[data-lo-id="hero-signup"]` over
legacy DOM IDs/classes/paths. These selectors work for events, page maps, hover,
snapshots and experiments. `section_view` now includes `sel` as well as `sec`
(role), allowing repeated roles to be distinguished in stored events; existing
role-based reports may still aggregate them. All existing event/node fields,
role names and schema version 1 are retained. No database migration is needed.
The API now narrowly accepts this ID-selector format in ingestion, snapshots
and experiment creation; arbitrary attribute selectors remain blocked.

Deploy the API update before the snippet. Existing APIs drop these selectors or
reject their use in experiment creation. Labels must exist at initialization:
there is no late-content or SPA remapping. Keep pages at 60 mapped elements or
fewer to transmit every node (internal cap remains 120). Existing selector-based
goals, reports and experiments may need retargeting when adopting the new IDs;
historical selectors are not automatically merged. Conversions still require
explicit success instrumentation or configured goals, not labels alone.

Full client instructions, complete markup and rollout checklist:
[`CLIENT_LABELING.md`](../../landing-optimizer-snippet/docs/CLIENT_LABELING.md).

### Complete list of automatically mapped page elements (unlabeled pages only)

With no `data-lo-role` attributes, the script builds the map once at tracker initialization in the following heuristic order. An element receives only its first matching role; the map is not a list of every DOM element. Ignored/password elements are excluded in both modes.

- **Navigation (`navigation`):** the first match for `nav`, `[role="navigation"]` or `header nav`.
- **Footer (`footer`):** the first match for `footer` or `[role="contentinfo"]`.
- **Hero (`hero`):** the first `h1`'s closest `section`, `header`, `div` whose class contains `hero`, or direct child of `main`; otherwise its parent. Without an `h1`, the first match for `header`, `section` or `main > *`.
- **Headings (`heading`):** all `h1`, `h2` and `h3` elements, subject to the map limit.
- **Calls to action (`cta`):** up to 25 detected elements from these candidate selectors:
  - `a[class*="btn" i]`.
  - `button`.
  - `a[role="button"]`.
  - `input[type="submit"]`.
  - `a[href*="signup" i]`.
  - `a[href*="sign-up" i]`.
  - `a[href*="get-started" i]`.
  - `a[href*="demo" i]`.
  - `a[href*="trial" i]`.
- **Forms (`form`):** all `form` elements, subject to the map limit; input values are not read.
- **Pricing (`pricing`):** the first `section`, `div[id]` or `div[class]` whose ID, classes or first descendant `h1`/`h2`/`h3` contains `pricing`, `plans` or `price`.
- **Testimonials (`testimonials`):** the same search using `testimonial`, `review`, `customers` or `trusted`.
- **Frequently asked questions (`faq`):** the same search using `faq`, `questions` or `frequently`.

CTA candidates must additionally be a `BUTTON` or have text matching `start`, `sign up`, `sign-up`, `signup`, `get`, `try`, `demo`, `buy`, `subscribe`, `join`, `book` or `contact`. Candidate selectors alone do not guarantee inclusion; an input's `value` is not used for this check. Keyword matching is case-insensitive and uses English substrings.

For each mapped element, the script captures:

- `role`: one of the ten roles listed above; `section` is assigned only through explicit labels.
- `selector`: a unique validated `data-lo-id` selector when available, otherwise an ID when suitable or a tag/class/`:nth-of-type()` path of up to five levels. Legacy selectors are heuristic and not guaranteed unique.
- `tag`: lowercase HTML tag name.
- `text` (when nonempty): whitespace-normalized `textContent` after excluding ignored/password descendants, truncated to 80 characters; it can include other descendant or hidden text.
- `textHash` (when text is nonempty): a non-cryptographic 32-bit hash of the element's full, unnormalized text after excluding ignored/password descendants, used for change detection.

The `page_map` event includes `p.path`, `p.counts` (counts by role) and `p.nodes`. Internally the builder retains up to **120 unique elements**, but this event sends only the first **60**. Counts describe the internal map, so they can exceed the transmitted node counts. Section visibility and hover use the internal map.

### Complete list of behavioral and application events

Every event includes `n` (event name) and `t` (milliseconds since the tracker instance was created). Additional fields depend on the event:

- **`page_view`:** emitted once when the tracker initializes; no event-specific fields.
- **`page_map`:** the structural map described above; omitted when the map has no nodes.
- **`scroll_depth`:** `sd` is 25, 50, 75 or 100. Each threshold fires at most once per tracker instance, on scroll. The percentage uses the viewport bottom relative to document height; scroll handling is throttled to 250 ms.
- **`cta_click`:** `sel` identifies a valid labeled CTA in manual mode; on unlabeled pages it identifies a detected CTA or a `BUTTON`. Detection uses the nearest `a`, `button`, `[role="button"]`, `input` or `[data-lo-role="cta"]`; the CTA set is built at initialization. Nested clicks resolve to the clickable target. Label the actual action, not a wrapping section.
- **`dead_click`:** `sel` identifies a clicked element with no ancestor matching that interactive-element list (including labeled CTA elements). This is a heuristic, not proof that the click had no effect.
- **`rage_click`:** emitted after three eligible clicks within 800 ms; includes `sel` for the interactive ancestor when present. Clicks need not hit the same element; the counter resets after emission.
- **`form_start`:** `sel` identifies the closest form on its first observed focus event, marked with `data-lo-started`. In manual mode only valid mapped forms qualify.
- **`form_submit`:** `sel` identifies the form receiving a DOM `submit` event. In manual mode only valid mapped forms qualify. This does not prove successful server submission or conversion.
- **`section_view`:** `sec` is the mapped role, falling back to `section`, and `sel` identifies the observed element; emitted once per observed element when intersecting at the configured 40% threshold. Despite its name, the observer covers mapped headings, CTAs and forms as well as sections. Requires `IntersectionObserver`.
- **`hover`:** `sel` identifies the nearest mapped ancestor and `dw` is accumulated attention time in milliseconds. Pointer position is sampled locally every second while the document is visible. Aggregates flush every 15 seconds and on `pagehide`, with a two-second minimum and at most 20 selectors per flush. Raw coordinates are not transmitted; time at a stationary last-known pointer position can continue accumulating.
- **`dwell`:** `dw` is 10,000 ms, emitted every ten seconds while the document is visible. This is a visibility-based engagement proxy, not exact active attention.
- **`dropoff`:** `dw` is elapsed wall-clock time since tracker creation, emitted on `pagehide`; it can include time spent in a hidden tab.
- **`exposure`:** `exp` and `var` identify the selected experiment and variant. The current engine can emit on timeout without successful DOM application, and its observer/timer path can emit duplicates; this is not guaranteed proof of a rendered exposure.
- **`conversion` (customer-instrumented):** `LandingOptimizer.conversion(goalName, payload)` sends `goal` (up to 64 characters), `val` (numeric `payload.value`, otherwise 1) and optional sanitized properties in `p`. Experiment/variant IDs are not automatically attached by this method.
- **`company_context` (customer-instrumented):** `LandingOptimizer.identifyCompanyContext(payload)` sends sanitized business metadata in `p`; no company attributes are inferred automatically.
- **Custom event names (customer-instrumented):** `LandingOptimizer.track(eventName, payload)` sends the name truncated to 64 characters and optional sanitized `p`. The browser permits arbitrary names; acceptance by ingestion is a separate contract.

### Complete list of event-envelope and visit-context fields

- `v`: event schema version, currently 1.
- `siteId`: configured website ID.
- `ik`: configured ingestion key, not visitor information.
- `sid`: random opaque session ID stored in `sessionStorage`, scoped to the tab and origin. On initialization, an existing ID is reused if its last initialization timestamp is less than 30 minutes old; otherwise a new ID is created. With storage unavailable, the fallback is in-memory for the page. This is not a daily or permanent visitor ID.
- `sentAt`: batch-send timestamp in Unix epoch milliseconds.
- `ctx.path`: current pathname, excluding query string and fragment.
- `ctx.ref`: referrer host, including port if present; empty for same-host or unavailable referrers.
- `ctx.dev`: `mobile`, `tablet` or `desktop`, inferred from user agent and viewport width.
- `ctx.br`: `chromium`, `firefox`, `safari`, `edge` or `other`, inferred from user agent.
- `ctx.vp`: viewport width and height, each rounded to the nearest 40 pixels.
- `ctx.lang`: first two lowercase characters of the browser language.
- `events`: the event objects listed above, up to 50 per batch; normal flush interval is four seconds, with additional hide/unload flushes. Delivery is best-effort, without a retry queue.

Context is assembled when a batch is sent; device category is determined at bootstrap. A `detectBot()` helper exists but is not called by the current bootstrap and no bot flag is included in the event envelope. Raw user-agent strings are read locally for classification, not included as explicit JSON fields; browser/network headers remain separate from this payload inventory.

### Optional page snapshot capture

The separate `lo-capture.js` bundle is loaded only when the page URL contains `lo_capture=1`, after the normal bootstrap and sampling checks. It is intended for operator-triggered capture; the query flag itself is not an operator authentication check. Normal visitor tracking does not automatically take screenshots.

The snapshot sent to `/v1/snapshots` contains:

- `v`: snapshot schema version, currently 1.
- `siteId` and `ik`: configured website ID and ingestion key.
- `path`: current pathname.
- `width`: document width clamped to 320–2,000 CSS pixels.
- `height`: document height clamped to 200–15,000 CSS pixels.
- `contentType`: image MIME type; the renderer prefers WebP and falls back to PNG. The contract also permits JPEG.
- `image`: base64-encoded raster image, limited to 4,000,000 base64 characters. Rendering tries smaller scales when necessary; encoded image dimensions can differ from the document dimensions above.
- `nodes`: visible mapped elements, each with `selector`, `role` and `rect`.
- `nodes[].rect`: document-space `[x, y, width, height]`, rounded in CSS pixels; coordinates are nonnegative and sizes at least one pixel. The collector caps at 150 nodes, but the upstream page map caps at 120.

To build the image, the module clones the DOM, copies computed styles for up to 4,000 elements and attempts to inline images. It removes scripts, noscript, iframes, video, audio, canvas and `[data-lo-ignore]` subtrees from the image clone. It removes password/hidden inputs, input value/checked attributes, textarea text and option selected attributes. Unreadable images become placeholders. The cloned HTML and computed-style list are intermediate browser data, not separate uploaded fields; their rendered appearance is included in the image. Rendering is best-effort and is not a guaranteed pixel-perfect screenshot.

### Collection boundaries and privacy limitations

- Click/form handlers skip targets inside `[data-lo-ignore]` and password inputs; hover skips ignored subtrees. The page-map builder now also excludes those elements and removes ignored/password descendant text before hashing/snippet generation. Snapshot node metadata uses the resulting map.
- Form field values and keystrokes are not read by the normal behavior tracker. Page-map text uses DOM `textContent`, however, so sensitive text already rendered on the page can appear in snippets. Selectors and pathnames can also contain identifying strings; they are not automatically redacted here.
- Customer-supplied `p` properties are limited to 20 entries, keys of 64 characters and strings of 256 characters. The sanitizer keeps finite numbers, booleans, strings and recursively sanitized arrays of up to ten entries per level; nested objects and null values are dropped. String values resembling email addresses, phone numbers, payment-card numbers or US SSNs are dropped by heuristics. This filter does not cover all personal data and is not applied to page-map text.
- Routine event payloads contain no raw mouse coordinates, typed form values, full HTML/CSS dumps, screenshot, full referrer URL, browser-version field or persistent cross-site identifier. DOM images, styles and geometry are handled only by the optional snapshot path described above.
- Query strings are excluded from the event context, but the experiment engine can read configured query parameters locally for targeting. The snapshot flag is also read locally.
- Configured sampling can skip the entire bootstrap. Automatic page views and maps run once per initialization; there is no built-in SPA route-change tracking or continuous page-map rebuild.
- This inventory describes what the browser constructs and attempts to send. API validation, sanitization, storage and AI forwarding may retain a smaller subset.

Manual-label compatibility also checked against the API selector scrubber, page-map/event schemas, snapshot sanitization and experiment DTO. Source files: [`tracker.ts`](../../landing-optimizer-snippet/src/tracker.ts), [`pagemap.ts`](../../landing-optimizer-snippet/src/pagemap.ts), [`hover.ts`](../../landing-optimizer-snippet/src/hover.ts), [`detect.ts`](../../landing-optimizer-snippet/src/detect.ts), [`session.ts`](../../landing-optimizer-snippet/src/session.ts), [`transport.ts`](../../landing-optimizer-snippet/src/transport.ts), [`capture.ts`](../../landing-optimizer-snippet/src/capture.ts), [`types.ts`](../../landing-optimizer-snippet/src/types.ts), [`sanitize.ts`](../../landing-optimizer-snippet/src/sanitize.ts), [`config.ts`](../../landing-optimizer-snippet/src/config.ts), [`index.ts`](../../landing-optimizer-snippet/src/index.ts) and [`experiments.ts`](../../landing-optimizer-snippet/src/experiments.ts). Paths refer to sibling repositories in the workspace; source reviewed November 4, 2026.

## What the API sends to the AI module

The API prepares an analysis request; the AI module does not retrieve website data directly from the databases.

| Input | Contents |
| --- | --- |
| Website ID | Identifies the website being analyzed. |
| Latest page map | Detected elements, selectors, roles and short copy from the most recent map across the site. |
| Overview metrics | Site-wide last 30 days: page views, conversions, conversion event ratio, CTA clicks and form submissions. |
| Section metrics | Section views, dead clicks, rage clicks and accumulated dwell time from retained aggregates. These do not use the same 30-day filter. |
| Brand rules | Configured tone, banned words, maximum copy length and claims to preserve. |

**Not currently sent:** screenshots, heatmaps, raw visitor sessions, goal definitions, device/traffic cohorts, experiment results or previous reviews. The AI therefore receives a smaller dataset than the script collects.

## What comes back

- A page assessment score, intended for a 0–100 scale.
- Optimization hypotheses, friction findings and copy suggestions, with explanations and risk labels.
- Optional target selectors, replacement text and expected-impact statements. Eligible headline/CTA changes can become draft experiments.

**Interpretation limits:** one page map may be combined with site-wide metrics from different time windows. Scores and impact statements do not prove conversion gains. Generation can fall back to rule-based output; the standalone scoring endpoint currently uses rules.

*The API-to-AI and output summaries above retain the October 6, 2026 data science handoff scope and were not reverified for this update. The script collection inventory was checked against the local snippet source on November 4, 2026; deployed production behavior was not verified.*
