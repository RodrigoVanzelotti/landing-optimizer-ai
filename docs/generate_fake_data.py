"""Synthetic research CSVs for DATA_SCIENCE_HANDOFF.md (standard library only).

Run: python generate_fake_data.py
Check: python generate_fake_data.py --self-check
JSON columns contain serialized JSON; nullable SQL fields are empty CSV cells.
All timestamps represent UTC. IDs are deterministic UUID v7 strings.
Snapshots encode real, schematic PNG bytes in image_base64 (not real websites).
These are research exports, not SQL import files. Accounts/credentials are omitted.
No generated score, approval, or impact text is an effectiveness label.
"""

# EDIT THESE PARAMETERS. Defaults produce roughly 200,000 behavioral events.
OUTPUT_DIR = "fake_data"                 # Relative to this script, or absolute.
SEED = 42
START_DATE = "2026-08-01"                # UTC, YYYY-MM-DD.
DAYS = 60
TENANTS = 3
SITES_PER_TENANT = 2
PAGE_PATHS = ("/", "/pricing", "/demo")
SESSIONS_PER_SITE_PER_DAY = 50
EXPERIMENTS_PER_SITE = 3
BASE_CONVERSION_RATE = 0.08              # Synthetic session probability.
TREATMENT_LIFT = 0.15                    # Relative synthetic change, not learned.
ATTRIBUTED_CONVERSION_RATE = 0.0         # 0 reproduces the current SDK gap.
MISSING_SELECTOR_RATE = 0.10
SECTION_TAG_RATE = 0.0                   # Click/dwell tagging gap; views have tags.
DUPLICATE_EVENT_RATE = 0.01
SNAPSHOTS_PER_PATH = 3                   # <=3/path and <=20/site retention.
OVERWRITE = False                       # Refuse existing generated CSVs by default.

import base64
import csv
import hashlib
import json
import random
import struct
import sys
import tempfile
import zlib
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID


NIL = str(UUID(int=0))
ROLES = ("hero", "heading", "cta", "form", "pricing", "testimonials", "faq",
         "navigation", "footer", "section")
KINDS = ("hypothesis", "headline", "cta", "friction", "section", "score", "plan")
EVENT_FIELDS = ("event_date", "event_time", "tenant_id", "site_id", "session_id",
                "event_name", "page_path", "referrer_host", "device_category",
                "browser_category", "country", "is_bot", "experiment_id",
                "variant_id", "section_id", "selector", "goal", "scroll_depth",
                "dwell_ms", "value", "props")


def stamp(value):
    return value.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def png(width, height, rectangles):
    """Small schematic screenshot with colored page blocks and matching geometry."""
    colors = ((40, 80, 130), (80, 160, 180), (220, 170, 60), (170, 180, 190))
    pixels = bytearray(b"\xf5\xf5\xf5" * width * height)
    for index, (x, y, w, h) in enumerate(rectangles):
        for row in range(y, min(y + h, height)):
            offset = (row * width + x) * 3
            pixels[offset:offset + w * 3] = bytes(colors[index % 4]) * w
    raw = b"".join(b"\0" + pixels[y * width * 3:(y + 1) * width * 3]
                   for y in range(height))

    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data)))

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def generate(output, *, seed=SEED, days=DAYS, tenants=TENANTS,
             sites_per_tenant=SITES_PER_TENANT, sessions=SESSIONS_PER_SITE_PER_DAY,
             overwrite=OVERWRITE, attribution=ATTRIBUTED_CONVERSION_RATE):
    """Write related source tables, exact event rollups, and daily feature exports."""
    for name, value in (("days", days), ("tenants", tenants),
                        ("sites_per_tenant", sites_per_tenant), ("sessions", sessions),
                        ("EXPERIMENTS_PER_SITE", EXPERIMENTS_PER_SITE)):
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    if not PAGE_PATHS or len(set(PAGE_PATHS)) != len(PAGE_PATHS):
        raise ValueError("PAGE_PATHS must contain distinct query-free paths")
    if any(not path.startswith("/") or "?" in path or "#" in path for path in PAGE_PATHS):
        raise ValueError("PAGE_PATHS must start with / and omit query/hash")
    if not 0 <= SNAPSHOTS_PER_PATH <= 3 or SNAPSHOTS_PER_PATH * len(PAGE_PATHS) > 20:
        raise ValueError("Snapshot count exceeds handoff retention limits")
    for rate in (BASE_CONVERSION_RATE, attribution, MISSING_SELECTOR_RATE,
                 SECTION_TAG_RATE, DUPLICATE_EVENT_RATE):
        if not 0 <= rate <= 1:
            raise ValueError("Probabilities must be between 0 and 1")
    if not 0 <= BASE_CONVERSION_RATE * (1 + TREATMENT_LIFT) <= 1:
        raise ValueError("Treatment conversion probability must be between 0 and 1")
    start = datetime.strptime(START_DATE, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end = start + timedelta(days=days)
    output = Path(output)
    tables = ("tenant", "site", "page_map", "page_snapshot", "brand_guardrail",
              "conversion_goal", "experiment", "variant", "variant_change",
              "ai_suggestion", "approval", "audit_log", "events", "mv_daily_funnel",
              "mv_section_performance", "mv_experiment_stats", "analyze_input", "analyze_result",
              "analytical_features")
    if not overwrite and any((output / f"{name}.csv").exists() for name in tables):
        raise FileExistsError(f"Generated CSVs exist in {output}; change OUTPUT_DIR or OVERWRITE")
    output.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    handles, writers, counts = {}, {}, Counter()

    def uid():
        milliseconds = int(start.timestamp() * 1000)
        return str(UUID(int=(milliseconds << 80) | (7 << 76)
                        | (rng.getrandbits(12) << 64) | (2 << 62) | rng.getrandbits(62)))

    def write(table, row):
        if table not in writers:
            handles[table] = (output / f"{table}.csv").open("w", newline="", encoding="utf-8")
            writers[table] = csv.DictWriter(handles[table], fieldnames=list(row))
            writers[table].writeheader()
        writers[table].writerow({key: json.dumps(value, ensure_ascii=False, separators=(",", ":"))
                                if isinstance(value, (dict, list)) else value
                                for key, value in row.items()})
        counts[table] += 1

    funnel = Counter()
    sections = defaultdict(Counter)
    experiment_stats = defaultdict(Counter)
    features = defaultdict(Counter)
    site_data = []
    try:
        for tenant_index in range(tenants):
            tenant = uid()
            write("tenant", dict(id=tenant, name=f"Synthetic tenant {tenant_index + 1}",
                                 slug=f"synthetic-{tenant_index + 1}", plan="pro", data_region="test",
                                 created_at=stamp(start), updated_at=stamp(start)))
            for site_index in range(sites_per_tenant):
                site = uid()
                domain = f"site-{tenant_index + 1}-{site_index + 1}.example.test"
                write("site", dict(id=site, tenant_id=tenant, name=domain, primary_domain=domain,
                                   sampling_rate=1.0, status="active", settings={"synthetic": True},
                                   config_version=1, created_at=stamp(start), updated_at=stamp(start)))
                rules = dict(tone=rng.choice(("friendly", "professional", "concise")),
                             bannedWords=["guaranteed", "miracle"], maxLength=80,
                             mustKeepClaims=["No credit card required"])
                write("brand_guardrail", dict(id=uid(), site_id=site, rules=rules,
                                               created_at=stamp(start), updated_at=stamp(start)))
                goal_ids = {}
                for kind, matcher in (("event", {}), ("url", {"op": "exact", "path": "/thanks"}),
                                      ("form_submit", {"selector": "#form"})):
                    goal_ids[kind] = uid()
                    write("conversion_goal", dict(id=goal_ids[kind], site_id=site, name=kind,
                                                   kind=kind, matcher=matcher, created_at=stamp(start)))
                maps = {}
                captures = {}
                for path_index, path in enumerate(PAGE_PATHS):
                    selected = [role for role in ROLES if role in ("hero", "heading", "cta", "form")
                                or rng.random() < 0.7]
                    nodes = [dict(role=role, selector=f"#{role}", tag="button" if role == "cta"
                                  else "form" if role == "form" else "section",
                                  text={"heading": "Make your work simpler", "cta": "Get started",
                                        "form": "No credit card required"}.get(role, role.title()))
                             for role in selected]
                    maps[path] = dict(path=path, counts=dict(Counter(selected)), nodes=nodes)
                    captures[path] = end - timedelta(hours=path_index + 1)
                    write("page_map", dict(id=uid(), site_id=site, url_path=path, map=maps[path],
                                           captured_at=stamp(captures[path])))
                    geometry = [dict(selector=node["selector"], role=node["role"],
                                     rect=[20, 20 + index * 90, 600, 70])
                                for index, node in enumerate(nodes)]
                    height = 40 + len(nodes) * 90
                    image = base64.b64encode(png(640, height, [n["rect"] for n in geometry])).decode()
                    for capture in range(SNAPSHOTS_PER_PATH):
                        write("page_snapshot", dict(id=uid(), site_id=site, url_path=path, width=640,
                                                    height=height, content_type="image/png",
                                                    image_base64=image, nodes=geometry,
                                                    captured_at=stamp(captures[path] - timedelta(days=capture))))
                experiments = []
                for index in range(EXPERIMENTS_PER_SITE):
                    experiment, control, treatment = uid(), uid(), uid()
                    experiments.append((experiment, control, treatment))
                    write("experiment", dict(id=experiment, tenant_id=tenant, site_id=site,
                                             name=f"Synthetic CTA test {index + 1}",
                                             hypothesis="Clearer CTA may reduce friction", status="running",
                                             type="cta", targeting={}, allocation=1.0,
                                             primary_goal_id=goal_ids["event"], risk_score=20,
                                             winner_variant_id=None, created_by=None,
                                             created_at=stamp(start), updated_at=stamp(start),
                                             started_at=stamp(start), ended_at=None))
                    for arm, is_control in ((control, True), (treatment, False)):
                        write("variant", dict(id=arm, experiment_id=experiment,
                                              name="Control" if is_control else "Treatment",
                                              is_control=is_control, weight=0.5, created_at=stamp(start)))
                    write("variant_change", dict(id=uid(), variant_id=treatment, selector="#cta",
                                                 op="set_text", original_value="Get started",
                                                 proposed_value="Start your free trial", attr_name=None,
                                                 created_at=stamp(start)))
                    write("approval", dict(id=uid(), experiment_id=experiment, status="approved",
                                           reason="Synthetic reviewer accepted the copy",
                                           risk_score=20, checklist={"claims_preserved": True},
                                           screenshot_url=None, approver_user_id=None,
                                           decided_at=stamp(start), created_at=stamp(start)))
                suggestions = []
                for kind in KINDS:
                    payload = dict(kind=kind, title=f"Synthetic {kind} suggestion",
                                   detail="Illustrative recommendation; no measured effectiveness.", riskLevel="low")
                    if kind in ("headline", "cta"):
                        payload.update(selector="#heading" if kind == "headline" else "#cta",
                                       originalValue="Make your work simpler" if kind == "headline" else "Get started",
                                       proposedValue="Simplify your daily work" if kind == "headline" else "Start your free trial")
                    suggestions.append(payload)
                    write("ai_suggestion", dict(id=uid(), tenant_id=tenant, site_id=site, kind=kind,
                                                payload=payload, model="synthetic-generator",
                                                expected_impact=None, risk_level="low",
                                                experiment_id=experiments[0][0] if kind == "cta" else None,
                                                created_at=stamp(end)))
                score = rng.randint(40, 90)
                write("analyze_result", dict(siteId=site, model="synthetic-generator", score=score,
                                             suggestions=suggestions))
                write("audit_log", dict(id=uid(), tenant_id=tenant, actor_user_id=None,
                                        action="ai.analyzed", target_type="site", target_id=site,
                                        metadata={"score": score, "suggestionCount": len(KINDS),
                                                  "synthetic": True}, ip_hash=None, created_at=stamp(end)))
                site_data.append((tenant, site, maps, captures, rules))
                # ponytail: illustrative session probabilities, replace with calibrated simulation if needed.
                for day in range(days):
                    for session_index in range(sessions):
                        time = start + timedelta(days=day, seconds=rng.randrange(86400))
                        path = rng.choice(PAGE_PATHS)
                        experiment, control, treatment = experiments[(day + session_index) % len(experiments)]
                        arm = rng.choice((control, treatment))
                        session = hashlib.sha256(f"{seed}:{site}:{day}:{session_index}".encode()).hexdigest()[:32]
                        base = dict(event_date=time.date().isoformat(), event_time=stamp(time),
                                    tenant_id=tenant, site_id=site, session_id=session, page_path=path,
                                    referrer_host=rng.choice(("", "search.example.test", "social.example.test")),
                                    device_category=rng.choices(("mobile", "desktop", "tablet"), (55, 40, 5))[0],
                                    browser_category=rng.choice(("chromium", "firefox", "safari", "edge", "other")),
                                    country="", is_bot=0, experiment_id=NIL, variant_id=NIL,
                                    section_id="", selector="", goal="", scroll_depth=0,
                                    dwell_ms=0, value=0.0, props={})

                        def emit(name, **values):
                            row = {**base, "event_name": name, **values}
                            if row["selector"] and rng.random() < MISSING_SELECTOR_RATE:
                                row["selector"] = ""
                            for _ in range(1 + (rng.random() < DUPLICATE_EVENT_RATE)):
                                write("events", {field: row[field] for field in EVENT_FIELDS})
                                key = (row["event_date"], tenant, site)
                                funnel[(*key, name)] += 1
                                feature = features[(*key, path)]
                                feature[name] += 1
                                feature["missing_selectors"] += int(not row["selector"])
                                if name == "scroll_depth":
                                    feature[f"scroll_{row['scroll_depth']}"] += 1
                                if name in ("dwell", "dropoff", "hover"):
                                    feature[f"{name}_ms"] += row["dwell_ms"]
                                if row["section_id"]:
                                    metric = sections[(*key, row["section_id"])]
                                    metric["views"] += int(name == "section_view")
                                    metric["dead_clicks"] += int(name == "dead_click")
                                    metric["rage_clicks"] += int(name == "rage_click")
                                    metric["dwell_ms_total"] += row["dwell_ms"]
                                if row["experiment_id"] != NIL:
                                    metric = experiment_stats[(*key, row["experiment_id"], row["variant_id"])]
                                    metric["exposures"] += int(name == "exposure")
                                    metric["conversions"] += int(name == "conversion")
                                    metric["conversion_value"] += row["value"] if name == "conversion" else 0

                        emit("page_view")
                        emit("exposure", experiment_id=experiment, variant_id=arm)
                        for node in maps[path]["nodes"][:rng.randint(2, len(maps[path]["nodes"]))]:
                            emit("section_view", section_id=node["role"], selector=node["selector"])
                        for bucket in (25, 50, 75, 100):
                            if rng.random() > 0.8:
                                break
                            emit("scroll_depth", scroll_depth=bucket)
                        emit("dwell", dwell_ms=rng.randint(1000, 90000),
                             section_id="hero" if rng.random() < SECTION_TAG_RATE else "")
                        if rng.random() < 0.3:
                            emit("hover", selector="#cta", dwell_ms=rng.randint(200, 8000),
                                 section_id="cta" if rng.random() < SECTION_TAG_RATE else "")
                        for name, probability in (("dead_click", 0.08), ("rage_click", 0.03)):
                            if rng.random() < probability:
                                emit(name, selector="#hero", section_id="hero" if rng.random() < SECTION_TAG_RATE else "")
                        converted = rng.random() < BASE_CONVERSION_RATE * (1 + TREATMENT_LIFT * (arm == treatment))
                        if converted or rng.random() < 0.25:
                            emit("cta_click", selector="#cta",
                                 section_id="cta" if rng.random() < SECTION_TAG_RATE else "")
                            emit("form_start", selector="#form")
                            if converted or rng.random() < 0.4:
                                emit("form_submit", selector="#form")
                        if converted:
                            attributed = rng.random() < attribution
                            emit("conversion", goal="event", value=1.0,
                                 experiment_id=experiment if attributed else NIL,
                                 variant_id=arm if attributed else NIL)
                        else:
                            emit("dropoff", dwell_ms=rng.randint(1000, 90000))
                        if rng.random() < 0.1:
                            emit("company_context", props={"industry": rng.choice(("software", "retail", "services")),
                                                           "size_band": rng.choice(("small", "medium", "large"))})
        for key, total in sorted(funnel.items()):
            write("mv_daily_funnel", dict(zip(("event_date", "tenant_id", "site_id", "event_name", "events"), (*key, total))))
        for table, metrics, dimensions, fields in (
            ("mv_section_performance", sections, ("event_date", "tenant_id", "site_id", "section_id"),
             ("views", "dead_clicks", "rage_clicks", "dwell_ms_total")),
            ("mv_experiment_stats", experiment_stats,
             ("event_date", "tenant_id", "site_id", "experiment_id", "variant_id"),
             ("exposures", "conversions", "conversion_value"))):
            for key, metric in sorted(metrics.items()):
                write(table, {**dict(zip(dimensions, key)), **{field: metric[field] for field in fields}})
        for tenant, site, maps, captures, rules in site_data:
            for (date, tenant_id, site_id, path), metric in sorted(features.items()):
                if site_id != site:
                    continue
                window = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                row = dict(tenant_id=tenant, site_id=site, page_path=path,
                           window_start=stamp(window), window_end=stamp(window + timedelta(days=1)),
                           map_captured_at=stamp(captures[path]),
                           snapshot_captured_at=stamp(captures[path]) if SNAPSHOTS_PER_PATH else None,
                           capture_time_mismatch=int(captures[path] >= window + timedelta(days=1)),
                           goal="event", collection_coverage=None, sampling_history_available=False,
                           role_counts=maps[path]["counts"],
                           snippet_lengths={n["selector"]: len(n["text"]) for n in maps[path]["nodes"]})
                for name in ("page_view", "cta_click", "form_start", "form_submit", "conversion",
                             "dead_click", "rage_click", "section_view", "missing_selectors",
                             "scroll_25", "scroll_50", "scroll_75", "scroll_100", "dwell_ms", "dropoff_ms", "hover_ms"):
                    row[name + "_events" if name in ("page_view", "cta_click", "form_start", "form_submit", "conversion") else name] = metric[name]
                row.update(ratio_denominator="page_view_events", ratio_unit="events / events",
                           cta_event_ratio=metric["cta_click"] / metric["page_view"],
                           form_event_ratio=metric["form_submit"] / metric["page_view"],
                           conversion_event_ratio=metric["conversion"] / metric["page_view"])
                write("analytical_features", row)
            overview = Counter()
            section_totals = defaultdict(Counter)
            for (date, _, site_id, name), total in funnel.items():
                if site_id == site and date >= (end - timedelta(days=30)).date().isoformat():
                    overview[name] += total
            for (_, _, site_id, section), metric in sections.items():
                if site_id == site:
                    section_totals[section].update(metric)
            latest_path = max(captures, key=captures.get)
            write("analyze_input", dict(siteId=site, pageMap=maps[latest_path], guardrails=rules,
                                        metrics={"overview": {"pageViews": overview["page_view"],
                                                 "conversions": overview["conversion"],
                                                 "conversionRate": overview["conversion"] / overview["page_view"] if overview["page_view"] else 0,
                                                 "ctaClicks": overview["cta_click"], "formSubmits": overview["form_submit"]},
                                                 "sections": [dict(section=section, views=m["views"],
                                                                   deadClicks=m["dead_clicks"], rageClicks=m["rage_clicks"],
                                                                   dwellMs=m["dwell_ms_total"])
                                                              for section, m in sorted(section_totals.items())]}))
    finally:
        for handle in handles.values():
            handle.close()
    return dict(counts)


def self_check():
    """One runnable check of joins, rollups, JSON/binary round-trip and determinism."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        counts = generate(root / "a", days=2, tenants=1, sites_per_tenant=1, sessions=100, attribution=1.0)
        generate(root / "b", days=2, tenants=1, sites_per_tenant=1, sessions=100, attribution=1.0)

        def rows(name):
            with (root / "a" / f"{name}.csv").open(encoding="utf-8", newline="") as handle:
                return list(csv.DictReader(handle))

        for file in (root / "a").glob("*.csv"):
            assert file.read_bytes() == (root / "b" / file.name).read_bytes(), file.name
        events = rows("events")
        assert len(events) == counts["events"]
        assert sum(int(row["events"]) for row in rows("mv_daily_funnel")) == len(events)
        sites = {row["id"]: row["tenant_id"] for row in rows("site")}
        arms = {row["id"]: row["experiment_id"] for row in rows("variant")}
        expected = defaultdict(Counter)
        expected_sections = defaultdict(Counter)
        for event in events:
            assert sites[event["site_id"]] == event["tenant_id"]
            assert event["event_date"] == event["event_time"][:10]
            assert len(event["session_id"]) == 32
            assert event["country"] == "" and event["is_bot"] == "0"
            json.loads(event["props"])
            key = tuple(event[field] for field in ("event_date", "tenant_id", "site_id"))
            if event["section_id"]:
                metric = expected_sections[(*key, event["section_id"])]
                metric["views"] += event["event_name"] == "section_view"
                metric["dead_clicks"] += event["event_name"] == "dead_click"
                metric["rage_clicks"] += event["event_name"] == "rage_click"
                metric["dwell_ms_total"] += int(event["dwell_ms"])
            if event["experiment_id"] != NIL:
                assert arms[event["variant_id"]] == event["experiment_id"]
                metric = expected[(*key, event["experiment_id"], event["variant_id"])]
                metric["exposures"] += event["event_name"] == "exposure"
                metric["conversions"] += event["event_name"] == "conversion"
                metric["conversion_value"] += float(event["value"]) if event["event_name"] == "conversion" else 0
        assert sum(m["conversions"] for m in expected.values()) > 0
        for table, metrics, dimensions in (
            ("mv_experiment_stats", expected, ("event_date", "tenant_id", "site_id", "experiment_id", "variant_id")),
            ("mv_section_performance", expected_sections, ("event_date", "tenant_id", "site_id", "section_id"))):
            for row in rows(table):
                metric = metrics[tuple(row[field] for field in dimensions)]
                assert all(float(row[field]) == metric[field] for field in row if field not in dimensions)
        for row in rows("page_snapshot"):
            image = base64.b64decode(row["image_base64"])
            assert image.startswith(b"\x89PNG\r\n\x1a\n")
            assert struct.unpack(">II", image[16:24]) == (int(row["width"]), int(row["height"]))
        for row in rows("analytical_features"):
            assert float(row["conversion_event_ratio"]) == int(row["conversion_events"]) / int(row["page_view_events"])
        generate(root / "gap", days=1, tenants=1, sites_per_tenant=1, sessions=100, attribution=0)
        with (root / "gap" / "events.csv").open(encoding="utf-8", newline="") as handle:
            assert all(row["experiment_id"] == NIL for row in csv.DictReader(handle) if row["event_name"] == "conversion")
    print("Self-check passed.")


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-check"]:
        self_check()
    elif sys.argv[1:]:
        raise SystemExit("Usage: python generate_fake_data.py [--self-check]; edit parameters at the top.")
    else:
        destination = Path(__file__).resolve().parent / OUTPUT_DIR
        result = generate(destination)
        print(f"Synthetic CSVs written to {destination}")
        for table, count in sorted(result.items()):
            print(f"  {table}.csv: {count:,} rows")
