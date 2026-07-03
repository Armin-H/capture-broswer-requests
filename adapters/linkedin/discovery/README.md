# LinkedIn SDUI discovery

Reverse-engineering notes and notebooks for LinkedIn job pages captured in `mitm_http_captures`.


## Notebooks

| # | Topic | Notebook |
|---|--------|----------|
| 01 | Request URL | [01_request_url.ipynb](01_request_url.ipynb) |
| 02 | Request body | [02_request_body.ipynb](02_request_body.ipynb) |
| 03 | Response / RSC wire format | [03_rsc_wire_format.ipynb](03_rsc_wire_format.ipynb) |
| 04 | aboutTheJob | [04_about_the_job.ipynb](04_about_the_job.ipynb) |
| 05 | job header | [05_job_header.ipynb](05_job_header.ipynb) |
| 06 | embedded chunk 6 (aboutTheJob) | [06_missing_job_description.ipynb](06_missing_job_description.ipynb) |
| 07 | missing job header | [07_missing_job_header.ipynb](07_missing_job_header.ipynb) |


---

## 01 — Request URL

Source: `mitm_http_captures.request_url`  
Verified by: [01_request_url.ipynb](01_request_url.ipynb)

### Host

- `hostname` and `netloc` are always `www.linkedin.com` (not useful for grouping captures).

### Path

- Job SDUI component requests use:
  ```
  /flagship-web/rsc-action/actions/component
  ```
- Other LinkedIn paths appear in captures (e.g. `server-stream-request`); filter to the path above for per-section job UI.

### Query parameters

On component URLs, every request has exactly these query keys:

| Key | Notes |
|-----|--------|
| `componentId` | Full SDUI component id (see below) |
| `sduiid` | Always the same value as `componentId` |
| `parentSpanId` | Trace/id string, e.g. `4ruJnbTMxW0=` |

Each key has a single value (`parse_qs` returns a one-element list per key).

### `componentId`

All values share this prefix:

```
com.linkedin.sdui.generated.jobseeker.dsl.impl.
```

The suffix is the part after that prefix. Observed suffix values:

- `aboutTheJob`
- `aboutTheCompanyForJobDetails` — optional; may be absent for some jobs
- `premiumApplicantInsightsForJobDetails`
- `premiumCompanyInsightsForJobDetails`
- `peopleWhoCanHelp`
- `jobMatch`
- `resumeReview`
- `jobAlertToggle`
- `similarJobs`
- `howYouFitGuide`
- `manageJobBanner`

### `parentSpanId`

- Base64-style string (alphanumeric + `/` + `=`), e.g. `4ruJnbTMxW0=`.
- Many distinct values across captures (likely per page load / trace).

---

## 02 — Request body

Source: `mitm_http_captures.request_body` on the component path from §01  
Verified by: [02_request_body.ipynb](02_request_body.ipynb)

### Top level

- JSON body has one key: `clientArguments`.

### `clientArguments`

Nested keys on every component request:

- `payload`
- `states`
- `requestMetadata`
- `screenId`

### `payload`

Observed keys (counts from captures at time of discovery):

| Key | Count |
|-----|------:|
| `jobId` | 286 |
| `isTwoPane` | 119 |
| `renderAsCard` | 61 |
| `hideInterestCard` | 29 |
| `isPremium` | 29 |
| `profilePicture` | 3 |
| `profileUrl` | 3 |
| `isTopApplicant` | 3 |
| `companyLogo` | 3 |
| `tooltipLegoTrackingToken` | 3 |

### `states`

- Empty list `[]` on every component request body observed so far.

### `requestMetadata`

- Always:
  ```json
  {"$type": "proto.sdui.common.RequestMetadata"}
  ```

### `screenId`

| Value | Count |
|-------|------:|
| `com.linkedin.sdui.flagshipnav.jobs.JobDetails` | 270 |
| `com.linkedin.sdui.flagshipnav.jobs.SemanticJobDetails` | 16 |

---

## 03 — Response body (RSC wire format)

Source: `mitm_http_captures.response_body` on the component path from §01  
Verified by: [03_rsc_wire_format.ipynb](03_rsc_wire_format.ipynb)

### Format

- Response is **not** a single JSON document — it is a **multiline RSC stream**.
- Each line: `<chunk_id>:<data>`
- `chunk_id` is a hexadecimal string (e.g. `6`, `7`, `Q`).
- The `<data>` part parses as JSON on observed lines.

### RSC element shape

Nested inside parsed chunk data, UI elements appear as four-element lists:

```python
['$', component_type, key, props_dict]
```

### `componentId` suffixes with captured responses

Observed when loading job pages:

- `jobAlertToggle`
- `aboutTheJob`
- `resumeReview`
- `premiumApplicantInsightsForJobDetails`
- `aboutTheCompanyForJobDetails`
- `premiumCompanyInsightsForJobDetails`
- `peopleWhoCanHelp`
- `jobMatch`

Chunk id sets differ by `componentId` suffix (see notebook).

---

## 04 — aboutTheJob

Source: `aboutTheJob` rows — component path from §01, `request_body` + `response_body`  
Verified by: [04_about_the_job.ipynb](04_about_the_job.ipynb)

### Row selection

- Filter captures where `componentId` suffix is `aboutTheJob`.
- `jobId` is in `clientArguments.payload.jobId` on the matching request body.
- One `aboutTheJob` response corresponds to one `jobId` (same job may appear in multiple captures).

### Description location

- Job description text is in chunk id **`6`** of the `aboutTheJob` response stream.
- Parsed chunk `6` is an RSC node: `['$', '$L7', None, props_dict]`.
- Text tree: `props_dict["textProps"]["children"]`.
- **Embedded variant:** some responses have no standalone `6:` line — chunk `6` is nested inside another chunk’s payload (e.g. `9`), with intro text in a `T<id>,…` prefix referenced as `$9` in the tree. See [06_missing_job_description.ipynb](06_missing_job_description.ipynb).

### Rendering

Text is built by walking the RSC tree under `textProps.children`:

- string leaves (not starting with `$`) → appended as-is
- `strong` → `\n## `
- `li` → `\n- `
- `br` → newline

### Extract by jobId

Given a `jobId`, find the `aboutTheJob` row whose request body contains that id, parse chunk `6`, render `textProps.children`.

Extractor: `adapters/linkedin/extract/about_the_job.py`

---

## aboutTheCompanyForJobDetails

Source: `aboutTheCompanyForJobDetails` rows — same component path and request-body pattern as §04  
Extractor: `adapters/linkedin/extract/about_the_company.py`

- Same row selection as §04, but filter `componentId` suffix to `aboutTheCompanyForJobDetails`.
- **This section may be completely missing for a job** — LinkedIn does not always render it, so there may be no matching capture and all extracted fields will be empty.

---

## 05 — job header

Source: `/flagship-web/jobs/search-results/` — not the component path from §01  
Verified by: [05_job_header.ipynb](05_job_header.ipynb) (capture **3521**, job `4430365784`)

When you open a job from [search results](https://www.linkedin.com/jobs/search-results/) (`currentJobId=...` in the URL), the summary card (title, company, location, badges, apply button) is in this response — not in the later `/rsc-action/actions/component` fetches.

### Row selection

- Filter captures where `request_url` path is `/flagship-web/jobs/search-results/`.
- `jobId` is the `currentJobId` query param on the request URL (not `clientArguments.payload.jobId`).

### Field locations

Same RSC wire format as §03. Chunk ids vary by capture; locate by content / `observabilityIdentifier`:

| Field | Where |
|-------|--------|
| `title`, `company_name` | `...topcard.stickyTopCard` text nodes |
| `location_label`, `listed_at_label`, `applicant_count_label` | `...topcard.topCard` metadata line (`·`-separated) |
| `promoted_label`, `application_status_label` | `...topcard.topCard` status text |
| `workplace_type_label`, `employment_type_label` | preference pill buttons, or `uncategorizedPreferences` in navigate payload |
| `company_logo_url` | `renderPayload` near the company name |
| `is_easy_apply` | any chunk with `"text":["Easy Apply"]` |

### Extract by jobId

Given a `jobId`, find the search-results row whose URL contains that `currentJobId`, then walk the RSC stream as above.

Extractor: `adapters/linkedin/extract/job_header.py` → `JobHeaderExtract`

---

## 07 — missing job header

Source: same path as §05  
Verified by: [07_missing_job_header.ipynb](07_missing_job_header.ipynb) (capture **5143**, job `4428420015`)

The observability-based approach in §05 fails when `topcard.topCard` markers are absent. Fix: parse chunk **`28`** as a component tree and read ordered string nodes.

Generic tree parser (from this notebook) lives in `adapters/linkedin/rsc.py` — `build_module_lookup`, `ComponentTreeBuilder`, `build_component_tree`.

Header extraction: `adapters/linkedin/extract/job_header.py`.
