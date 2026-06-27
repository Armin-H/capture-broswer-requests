# LinkedIn SDUI discovery

Reverse-engineering notes and notebooks for LinkedIn job pages captured in `mitm_http_captures`.


## Notebooks

| # | Topic | Notebook |
|---|--------|----------|
| 01 | Request URL | [01_request_url.ipynb](01_request_url.ipynb) |
| 02 | Request body | [02_request_body.ipynb](02_request_body.ipynb) |


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
