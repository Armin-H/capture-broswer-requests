from dataclasses import dataclass, fields
from datetime import datetime, time, timedelta
from urllib.parse import parse_qs, urlparse

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from adapters.linkedin.captures import component_suffix, job_id_from_request_body
from adapters.linkedin.extract.about_the_company import (
    AboutTheCompanyExtract,
    extract_about_the_company,
)
from adapters.linkedin.extract.about_the_job import extract_about_the_job
from adapters.linkedin.extract.job_header import JobHeaderExtract, extract_job_header
from adapters.linkedin.models import (
    AboutTheCompanyForJobDetailsObservation,
    ObservationCapture,
)
from adapters.linkedin.models import (
    JobObservation as JobObservationRow,
)
from core.db import SessionLocal

GAP_THRESHOLD = timedelta(seconds=3)

_COMPONENT_PATH = "/flagship-web/rsc-action/actions/component"
_SEARCH_RESULTS_PATH = "/flagship-web/jobs/search-results/"
_JOB_SECTION_SUFFIXES = ("aboutTheJob", "aboutTheCompanyForJobDetails")

# (capture_id, url, response_body, captured_at_ms, job_id, component_id)
SectionCapture = tuple[int, str, str, int, str, str]


def today_capture_range_ms() -> tuple[int, int]:
    today = datetime.now().date()
    start = datetime.combine(today, time.min)
    end = datetime.combine(today + timedelta(days=1), time.min)
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def fetch_job_capture_rows(
    *,
    since_captured_at_ms: int | None = None,
    until_captured_at_ms: int | None = None,
):
    extra_clauses: list[str] = []
    params: dict[str, int] = {}
    if since_captured_at_ms is not None:
        extra_clauses.append("AND captured_at_ms >= :since_captured_at_ms")
        params["since_captured_at_ms"] = since_captured_at_ms
    if until_captured_at_ms is not None:
        extra_clauses.append("AND captured_at_ms < :until_captured_at_ms")
        params["until_captured_at_ms"] = until_captured_at_ms

    query = text(f"""
        SELECT id, request_url, request_body, response_body, captured_at_ms
        FROM mitm_http_captures
        WHERE (
            request_url LIKE '%/flagship-web/rsc-action/actions/component%'
            OR request_url LIKE '%/flagship-web/jobs/search-results/%'
        )
        AND response_body IS NOT NULL
        {" ".join(extra_clauses)}
        ORDER BY captured_at_ms DESC
    """)
    with SessionLocal() as session:
        return list(session.execute(query, params).fetchall())


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
            if (
                "aboutTheJob" in current_bundle
                and "aboutTheCompanyForJobDetails" in current_bundle
            ):
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

    if (
        "aboutTheJob" in current_bundle
        and "aboutTheCompanyForJobDetails" in current_bundle
    ):
        yield prev_job_id, current_bundle
    elif current_bundle:
        print(
            f"warning: dropping incomplete bundle: job {prev_job_id}, "
            f"current bundle: {current_bundle.keys()}"
        )


@dataclass
class ExtractedJobObservation:
    job_id: str
    observed_at_ms: int
    header: JobHeaderExtract | None
    description: str | None
    company: AboutTheCompanyExtract | None
    capture_ids: dict[str, int]


def _extract_has_data(extract) -> bool:
    return any(getattr(extract, f.name) for f in fields(extract))


def extract_job_observation(job_id, bundle) -> ExtractedJobObservation:
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
        extracted_company = extract_about_the_company(
            bundle["aboutTheCompanyForJobDetails"][2]
        )
        company = extracted_company if _extract_has_data(extracted_company) else None
    else:
        company = None

    return ExtractedJobObservation(
        job_id=job_id,
        observed_at_ms=observed_at_ms,
        header=header,
        description=description,
        company=company,
        capture_ids=capture_ids,
    )


def _build_job_observation_row(obs: ExtractedJobObservation) -> JobObservationRow:
    header = obs.header
    return JobObservationRow(
        job_id=obs.job_id,
        observed_at_ms=obs.observed_at_ms,
        title=header.title if header else None,
        company_name=header.company_name if header else None,
        location=header.location if header else None,
        listed_at=header.listed_at if header else None,
        apply_count=header.apply_count if header else None,
        promoted=header.promoted if header else None,
        hiring_insights=header.hiring_insights if header else None,
        description=obs.description,
    )


def _build_about_the_company_row(
    job_observation_id: int,
    company: AboutTheCompanyExtract,
) -> AboutTheCompanyForJobDetailsObservation:
    return AboutTheCompanyForJobDetailsObservation(
        job_observation_id=job_observation_id,
        name=company.name,
        followers_label=company.followers_label,
        industry_label=company.industry_label,
        size_label=company.size_label,
        linkedin_headcount_label=company.linkedin_headcount_label,
        company_id=company.company_id,
        company_url=company.company_url,
        logo_url=company.logo_url,
        description=company.description,
    )


def _build_observation_capture_rows(
    job_observation_id: int,
    capture_ids: dict[str, int],
) -> list[ObservationCapture]:
    return [
        ObservationCapture(
            job_observation_id=job_observation_id,
            mitm_capture_id=capture_id,
            section=section,
        )
        for section, capture_id in capture_ids.items()
    ]


def _observation_already_persisted(
    session: Session, capture_ids: dict[str, int]
) -> bool:
    if not capture_ids:
        return False
    return (
        session.scalars(
            select(ObservationCapture.id)
            .where(ObservationCapture.mitm_capture_id.in_(capture_ids.values()))
            .limit(1)
        ).first()
        is not None
    )


def _delete_observations_for_capture_ids(
    session: Session, capture_ids: dict[str, int]
) -> None:
    job_observation_ids = session.scalars(
        select(ObservationCapture.job_observation_id)
        .where(ObservationCapture.mitm_capture_id.in_(capture_ids.values()))
        .distinct()
    ).all()
    for job_observation_id in job_observation_ids:
        session.execute(
            delete(ObservationCapture).where(
                ObservationCapture.job_observation_id == job_observation_id
            )
        )
        session.execute(
            delete(AboutTheCompanyForJobDetailsObservation).where(
                AboutTheCompanyForJobDetailsObservation.job_observation_id
                == job_observation_id
            )
        )
        session.execute(
            delete(JobObservationRow).where(JobObservationRow.id == job_observation_id)
        )


def insert_job_observation(
    session: Session,
    obs: ExtractedJobObservation,
    *,
    rewrite: bool = False,
) -> int:
    if obs.description is None:
        raise ValueError(
            f"no description for job {obs.job_id}, captures={obs.capture_ids}"
        )

    with session.begin():
        already_persisted = _observation_already_persisted(session, obs.capture_ids)
        if already_persisted and not rewrite:
            return -1

        if already_persisted and rewrite:
            _delete_observations_for_capture_ids(session, obs.capture_ids)

        row = _build_job_observation_row(obs)
        session.add(row)
        session.flush()

        if obs.company is not None:
            session.add(_build_about_the_company_row(row.id, obs.company))

        for capture_row in _build_observation_capture_rows(row.id, obs.capture_ids):
            session.add(capture_row)

        return row.id


def load_observations_from_captures(
    *,
    rewrite: bool = False,
    since_captured_at_ms: int | None = None,
    until_captured_at_ms: int | None = None,
) -> None:
    rows = select_job_section_captures(
        fetch_job_capture_rows(
            since_captured_at_ms=since_captured_at_ms,
            until_captured_at_ms=until_captured_at_ms,
        )
    )
    inserted = 0
    skipped = 0
    failed = 0
    with SessionLocal() as session:
        for job_id, bundle in bundle_rows(rows):
            try:
                obs = extract_job_observation(job_id, bundle)
                row_id = insert_job_observation(session, obs, rewrite=rewrite)
                if row_id == -1:
                    skipped += 1
                else:
                    inserted += 1
            except ValueError as exc:
                failed += 1
                capture_ids = {section: row[0] for section, row in bundle.items()}
                print(f"warning: skipping job {job_id}, captures={capture_ids}: {exc}")
                continue
    print(f"inserted {inserted} observations, skipped {skipped} duplicates")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--rewrite", action="store_true")
    since_group = parser.add_mutually_exclusive_group()
    since_group.add_argument("--since-ms", type=int, dest="since_ms")
    since_group.add_argument("--today", action="store_true")
    args = parser.parse_args()

    since_ms = args.since_ms
    until_ms = None
    if args.today:
        since_ms, until_ms = today_capture_range_ms()

    load_observations_from_captures(
        rewrite=args.rewrite,
        since_captured_at_ms=since_ms,
        until_captured_at_ms=until_ms,
    )


if __name__ == "__main__":
    main()
