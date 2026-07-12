# LinkedIn adapter

Turns LinkedIn job page captures from `mitm_http_captures` into append-only rows in the `linkedin_jobs` schema.

Each **observation** is what a job looked like at a point in time: description, header fields when we can extract them, optional company section, plus lineage back to the MITM captures used.

## Pipeline

```text
mitm_http_captures
    → select LinkedIn job endpoints
    → bundle related captures per job (time window)
    → extract fields (pure functions in extract/)
    → insert linkedin_jobs.* (one observation = one transaction)
```

Run the loader:

```bash
python -m adapters.linkedin.load_observations_from_captures
python -m adapters.linkedin.load_observations_from_captures --today
python -m adapters.linkedin.load_observations_from_captures --since-ms 1710000000000
python -m adapters.linkedin.load_observations_from_captures --rewrite
```

## Captures used

| Endpoint | Role | Required? |
|----------|------|-----------|
| `/flagship-web/rsc-action/actions/component` with `aboutTheJob` | Job description | Yes (bundle dropped without it) |
| Same path with `aboutTheCompanyForJobDetails` | Company profile on the job page | Yes for bundling today; LinkedIn sometimes omits it |
| `/flagship-web/jobs/search-results/` | Job header (title, company, location, …) | Not required for insert — every job has a header in the UI, but we only extract it when this capture is in the bundle |

Raw captures stay immutable in `mitm_http_captures`. Reverse-engineering notes and notebooks live under [`discovery/`](discovery/).

## Layout

| Path | Responsibility |
|------|----------------|
| `rsc.py` | Parse LinkedIn RSC / Flight response streams |
| `extract/` | Pure extractors (response body → fields); no DB I/O |
| `captures.py` | Helpers to filter component captures |
| `models.py` | `linkedin_jobs` ORM (`job_observation`, company side-table, `observation_capture`) |
| `load_observations_from_captures.py` | Select → bundle → extract → insert |
| `discovery/` | Notebooks and notes from SDUI reverse engineering |

## Data model

- **`job_observation`** — append-only fact: we saw job `job_id` at `observed_at_ms`, with description and whatever header fields we could extract.
- **`about_the_company_for_job_details_observation`** — company section for that observation (when present).
- **`observation_capture`** — lineage: which MITM capture ids backed which section.

Inserts for one observation are a single transaction so you never leave a half-written observation.

## Known limitations and follow-ups

Intentional gaps for this MVP — come back later rather than blocking the next feature.

- **Header fields often null in the DB** when the bundle has no `search-results` capture — the job always has a header on LinkedIn; our pipeline just cannot extract it without that response (title, company name, location, listed-at, apply count, promoted, hiring insights).
- **Search-results without `currentJobId`** are skipped (`no job id found` in loader output). Those are list/pagination requests, not a focused job card.
- **`aboutTheCompanyForJobDetails` is optional on LinkedIn** — some jobs never emit that component; bundling currently requires both `aboutTheJob` and company, so those jobs are dropped as incomplete bundles.
- **Extra / unusual sections** on some jobs are not handled yet (examples: `4417568462`, `4426203955`).
- **Tests** cover `about_the_job` and `job_header` extractors only — no fixtures yet for `about_the_company` or the bundler/loader.
- **Logging** is ad-hoc `print` warnings, not structured logging.
- **Schema changes** still mean recreate tables by hand, then re-run the loader (no migrations yet).
