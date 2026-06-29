"""Extract job header fields from /flagship-web/jobs/search-results/ RSC responses."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from adapters.linkedin import rsc

_TOPCARD_OBSERVABILITY = "topcard.topCard"
_STICKY_TOPCARD_OBSERVABILITY = "stickyTopCard"
_PROMOTED_LABEL = "Promoted by hirer"
_EASY_APPLY_MARKER = '"text":["Easy Apply"]'

_WORKPLACE_LABELS = frozenset({"On-site", "Remote", "Hybrid"})
_EMPLOYMENT_LABELS = frozenset(
    {"Full-time", "Part-time", "Contract", "Internship", "Temporary", "Volunteer"}
)

_PILL_TEXT_RE = re.compile(r'"text":\["([^"]+)"\]')


@dataclass
class JobHeaderExtract:
    job_id: str | None = None
    title: str | None = None
    company_name: str | None = None
    company_logo_url: str | None = None
    location_label: str | None = None
    listed_at_label: str | None = None
    applicant_count_label: str | None = None
    promoted_label: str | None = None
    application_status_label: str | None = None
    workplace_type_label: str | None = None
    employment_type_label: str | None = None
    is_easy_apply: bool = False


def _iter_text_props(obj: Any):
    if isinstance(obj, dict):
        text_props = obj.get("textProps")
        if isinstance(text_props, dict):
            text = rsc.render_text(text_props.get("children", [])).strip()
            if text:
                yield text
        for value in obj.values():
            yield from _iter_text_props(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _iter_text_props(value)


def _texts_for_observability(response_body: str, identifier_substring: str) -> list[str]:
    texts: list[str] = []
    for data in rsc.parse_stream(response_body).values():
        if identifier_substring not in data:
            continue
        parsed = json.loads(data)
        texts.extend(_iter_text_props(parsed))
    return texts


def _logo_url_from_render_payload(obj: Any) -> str | None:
    if isinstance(obj, dict):
        render_payload = obj.get("renderPayload")
        if isinstance(render_payload, dict):
            root_url = render_payload.get("rootUrl")
            if not isinstance(root_url, str):
                return None
            renditions = render_payload.get("imageRenditions")
            if not isinstance(renditions, list) or not renditions:
                return root_url
            best = max(
                renditions,
                key=lambda rendition: rendition.get("width", 0) if isinstance(rendition, dict) else 0,
            )
            suffix = best.get("suffixUrl") if isinstance(best, dict) else None
            if isinstance(suffix, str):
                return root_url + suffix
            return root_url
        for value in obj.values():
            found = _logo_url_from_render_payload(value)
            if found:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = _logo_url_from_render_payload(value)
            if found:
                return found
    return None


def _extract_logo_url(response_body: str, company_name: str | None) -> str | None:
    if not company_name:
        return None
    for data in rsc.parse_stream(response_body).values():
        if "renderPayload" not in data or company_name not in data:
            continue
        logo_url = _logo_url_from_render_payload(json.loads(data))
        if logo_url:
            return logo_url
    return None


def _parse_metadata_line(text: str) -> tuple[str | None, str | None, str | None]:
    if "·" not in text or "applicant" not in text.lower():
        return None, None, None
    parts = [part.strip() for part in text.split("·")]
    if len(parts) < 3:
        return None, None, None
    return parts[0], parts[1], parts[2]


def _parse_status_line(text: str) -> tuple[str | None, str | None]:
    promoted_label = _PROMOTED_LABEL if _PROMOTED_LABEL in text else None
    application_status_label = None
    if _PROMOTED_LABEL in text:
        remainder = text.split(_PROMOTED_LABEL, 1)[-1]
        remainder = remainder.replace("·", " ").replace("\n## ", " ").strip(" ·")
        if remainder:
            application_status_label = remainder
    elif "review" in text.lower() or "applicant" in text.lower():
        application_status_label = text.strip()
    return promoted_label, application_status_label


def _extract_sticky_header(sticky_texts: list[str]) -> tuple[str | None, str | None]:
    if not sticky_texts:
        return None, None
    title = sticky_texts[0]
    company_name = None
    if len(sticky_texts) > 1:
        company_name = sticky_texts[1].split("•", 1)[0].strip()
    return title, company_name


def _extract_preference_labels(response_body: str) -> tuple[str | None, str | None]:
    workplace_type_label = None
    employment_type_label = None
    for data in rsc.parse_stream(response_body).values():
        for match in _PILL_TEXT_RE.finditer(data):
            label = match.group(1)
            if label in _WORKPLACE_LABELS:
                workplace_type_label = label
            elif label in _EMPLOYMENT_LABELS:
                employment_type_label = label
    return workplace_type_label, employment_type_label


def extract_job_header(response_body: str, *, job_id: str | None = None) -> JobHeaderExtract:
    """Extract the job summary card from a search-results RSC response."""
    result = JobHeaderExtract(job_id=str(job_id) if job_id is not None else None)

    sticky_texts = _texts_for_observability(response_body, _STICKY_TOPCARD_OBSERVABILITY)
    result.title, result.company_name = _extract_sticky_header(sticky_texts)

    for text in _texts_for_observability(response_body, _TOPCARD_OBSERVABILITY):
        location_label, listed_at_label, applicant_count_label = _parse_metadata_line(text)
        if location_label is not None:
            result.location_label = location_label
            result.listed_at_label = listed_at_label
            result.applicant_count_label = applicant_count_label
        promoted_label, application_status_label = _parse_status_line(text)
        if promoted_label is not None:
            result.promoted_label = promoted_label
        if application_status_label is not None:
            result.application_status_label = application_status_label

    result.workplace_type_label, result.employment_type_label = _extract_preference_labels(
        response_body
    )
    result.company_logo_url = _extract_logo_url(response_body, result.company_name)
    result.is_easy_apply = _EASY_APPLY_MARKER in response_body
    return result
