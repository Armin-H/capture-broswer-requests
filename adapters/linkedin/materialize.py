from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

from sqlalchemy import text

from adapters.linkedin.captures import component_suffix, job_id_from_request_body
from adapters.linkedin.extract.about_the_company import (
    AboutTheCompanyExtract,
    extract_about_the_company,
)
from adapters.linkedin.extract.about_the_job import extract_about_the_job
from adapters.linkedin.extract.job_header import JobHeaderExtract, extract_job_header
from core.db import SessionLocal

GAP_THRESHOLD = timedelta(seconds=3)

_COMPONENT_PATH = "/flagship-web/rsc-action/actions/component"
_SEARCH_RESULTS_PATH = "/flagship-web/jobs/search-results/"
_JOB_SECTION_SUFFIXES = ("aboutTheJob", "aboutTheCompanyForJobDetails")

# (capture_id, url, response_body, captured_at_ms, job_id, component_id)
SectionCapture = tuple[int, str, str, int, str, str]


def fetch_job_capture_rows():
    query = text("""
        SELECT id, request_url, request_body, response_body, captured_at_ms
        FROM mitm_http_captures
        WHERE (
            request_url LIKE '%/flagship-web/rsc-action/actions/component%'
            OR request_url LIKE '%/flagship-web/jobs/search-results/%'
        )
        AND response_body IS NOT NULL
        ORDER BY captured_at_ms DESC
    """)
    with SessionLocal() as session:
        return list(session.execute(query).fetchall())


def format_captured_at(captured_at_ms: int) -> str:
    dt = datetime.fromtimestamp(captured_at_ms / 1000)
    return dt.strftime(f"{dt.day}.%b.{dt.year} - %I:%M:%S%p").lower()


def select_job_section_captures(rows):
    for capture_id, url, request_body, response_body, captured_at_ms in rows:
        url_path = urlparse(url).path
        job_id = None
        if url_path == _COMPONENT_PATH:
            component_id = component_suffix(url)
            if component_id not in _JOB_SECTION_SUFFIXES:
                continue
            job_id = job_id_from_request_body(request_body)
        elif url_path == _SEARCH_RESULTS_PATH:
            job_id = parse_qs(urlparse(url).query).get("currentJobId", [None])[0]
            component_id = "search-results"
        else:
            print(f"Skipping row {url} because it's not a LinkedIn endpoint")
        if job_id is None:
            print("no job id found", url)
            continue
        yield capture_id, url, response_body, captured_at_ms, job_id, component_id


def pretty_timedelta(td: timedelta) -> str:
    total = int(td.total_seconds())
    if total < 60:
        return f"{total}s"
    m, s = divmod(total, 60)
    if m < 60:
        return f"{m}m{s}s" if s else f"{m}m"
    h, m = divmod(m, 60)
    if h < 24:
        return f"{h}h{m}m" if m else f"{h}h"
    d, h = divmod(h, 24)
    return f"{d}d{h}h" if h else f"{d}d"


def bundle_rows(rows):
    prev_job_id = None
    current_bundle: dict[str, SectionCapture] = {}
    for capture_id, url, response_body, captured_at_ms, job_id, component_id in rows:
        row: SectionCapture = (
            capture_id,
            url,
            response_body,
            captured_at_ms,
            job_id,
            component_id,
        )
        if prev_job_id and prev_job_id != job_id:
            if "aboutTheJob" in current_bundle and "aboutTheCompanyForJobDetails" in current_bundle:
                yield prev_job_id, current_bundle
                current_bundle = {component_id: row}
                prev_job_id = job_id
            else:
                print(
                    f"warning: dropping incomplete bundle: job {prev_job_id}, "
                    f"current bundle: {current_bundle.keys()}"
                )
                current_bundle = {component_id: row}
                prev_job_id = job_id
        else:
            if component_id in current_bundle:
                time_gap = timedelta(
                    milliseconds=min(
                        abs(captured_at_ms - section_row[3])
                        for section_row in current_bundle.values()
                    )
                )
                if time_gap < GAP_THRESHOLD:
                    print(
                        f"warning: duplicate capture for job {job_id}, "
                        f"component {component_id}, skipping capture"
                    )
                else:
                    yield prev_job_id, current_bundle
                    current_bundle = {component_id: row}
                    prev_job_id = job_id
            else:
                current_bundle[component_id] = row
        prev_job_id = job_id

    if "aboutTheJob" in current_bundle and "aboutTheCompanyForJobDetails" in current_bundle:
        yield prev_job_id, current_bundle
    elif current_bundle:
        print(
            f"warning: dropping incomplete bundle: job {prev_job_id}, "
            f"current bundle: {current_bundle.keys()}"
        )

@dataclass
class JobObservation:
    job_id: str
    observed_at_ms: int
    header: JobHeaderExtract | None
    description: str | None
    company: AboutTheCompanyExtract | None
    capture_ids: dict[str, int]


def extract_job_observation(job_id, bundle) -> JobObservation:
    observed_at_ms = min(row[3] for row in bundle.values())
    capture_ids = {section: row[0] for section, row in bundle.items()}

    if "search-results" in bundle:
        header = extract_job_header(bundle["search-results"][2], job_id=job_id)
    else:
        header = None
    if "aboutTheJob" in bundle:
        description = extract_about_the_job(bundle["aboutTheJob"][2])
    else:
        description = None
    if "aboutTheCompanyForJobDetails" in bundle:
        company = extract_about_the_company(bundle["aboutTheCompanyForJobDetails"][2])
    else:
        company = None

    return JobObservation(
        job_id=job_id,
        observed_at_ms=observed_at_ms,
        header=header,
        description=description,
        company=company,
        capture_ids=capture_ids,
    )


def materialize_observations() -> None:
    rows = select_job_section_captures(fetch_job_capture_rows())
    for job_id, bundle in bundle_rows(rows):
        obs = extract_job_observation(job_id, bundle)
        print(obs.job_id, obs.capture_ids)
        if obs.header:
            print("  title:", obs.header.title)
        print("  description len:", len(obs.description or ""))
        if obs.company:
            print("  company:", obs.company.name)
        print("--------------------------------")


if __name__ == "__main__":
    materialize_observations()
