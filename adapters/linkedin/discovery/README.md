# LinkedIn SDUI discovery

Reverse-engineering notes and notebooks for LinkedIn job pages captured in `mitm_http_captures`.


## Notebooks

| # | Topic | Notebook | Status |
|---|--------|----------|--------|
| 01 | Request URL | [01_request_url.ipynb](01_request_url.ipynb) | done |


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
- `aboutTheCompanyForJobDetails`
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
