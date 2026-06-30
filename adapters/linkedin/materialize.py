from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

from sqlalchemy import text

from adapters.linkedin.captures import component_suffix, job_id_from_request_body
from core.db import SessionLocal

GAP_THRESHOLD = timedelta(seconds=3)

_COMPONENT_PATH = "/flagship-web/rsc-action/actions/component"
_SEARCH_RESULTS_PATH = "/flagship-web/jobs/search-results/"
_JOB_SECTION_SUFFIXES = ("aboutTheJob", "aboutTheCompanyForJobDetails")


def fetch_job_capture_rows():
    query = text("""
        SELECT request_url, request_body, response_body, captured_at_ms
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
    for url, request_body, response_body, captured_at_ms in rows:
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
        yield url, response_body, captured_at_ms, job_id, component_id


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
    current_bundle = {}
    for url, response_body, captured_at_ms, job_id, component_id in rows:
        if prev_job_id and prev_job_id != job_id:
            if "aboutTheJob" in current_bundle and "aboutTheCompanyForJobDetails" in current_bundle:
                yield prev_job_id, current_bundle
                current_bundle = {component_id: (url, response_body, captured_at_ms, job_id, component_id)}
                prev_job_id = job_id
            else:
                print(
                    f"warning: dropping incomplete bundle: job {prev_job_id}, "
                    f"current bundle: {current_bundle.keys()}"
                )
                current_bundle = {component_id: (url, response_body, captured_at_ms, job_id, component_id)}
                prev_job_id = job_id
        else:
            if component_id in current_bundle:
                time_gap = timedelta(
                    milliseconds=min(
                        abs(captured_at_ms - current_bundle[component_id][2])
                        for component_id in current_bundle
                    )
                )
                if time_gap < GAP_THRESHOLD:
                    print(
                        f"warning: duplicate capture for job {job_id}, "
                        f"component {component_id}, skipping capture"
                    )
                else:
                    yield prev_job_id, current_bundle
                    current_bundle = {component_id: (url, response_body, captured_at_ms, job_id, component_id)}
                    prev_job_id = job_id
            else:
                current_bundle[component_id] = (url, response_body, captured_at_ms, job_id, component_id)
        prev_job_id = job_id


def materialize_observations() -> None:
    rows = select_job_section_captures(fetch_job_capture_rows())
    for job_id, bundle in bundle_rows(rows):
        print(job_id, bundle.keys())


if __name__ == "__main__":
    materialize_observations()
