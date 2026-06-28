"""Extract company profile fields from aboutTheCompanyForJobDetails RSC responses."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from adapters.linkedin import rsc

_HEADER_CHUNK_ID = "0"
_LOGO_CHUNK_ID = "8"
_DESCRIPTION_CHUNK_ID = "11"

_UI_SKIP = frozenset({"•", "Follow", "Following", "About the company", "Company photos", "Show more"})

_NOISE_SUBSTRINGS = (
    "limit of 50 companies",
    "interested in a company may be",
    "prioritizing your choices",
    "Interested in working with us",
    "Learn more",
    "Something went wrong",
)


@dataclass
class AboutTheCompanyExtract:
    name: str | None = None
    followers_label: str | None = None
    industry_label: str | None = None
    size_label: str | None = None
    linkedin_headcount_label: str | None = None
    company_id: str | None = None
    company_url: str | None = None
    logo_url: str | None = None
    description: str | None = None


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


def _is_noise(text: str) -> bool:
    if text in _UI_SKIP:
        return True
    return any(fragment in text for fragment in _NOISE_SUBSTRINGS)


def _find_organization_id_in_text(text: str) -> str | None:
    match = re.search(r'"organizationId"\s*:\s*"(\d+)"', text)
    if match:
        return match.group(1)
    match = re.search(r"urn:li:fsd_company:(\d+)", text)
    if match:
        return match.group(1)
    return None


def _find_organization_id(obj: Any) -> str | None:
    if isinstance(obj, dict):
        org_id = obj.get("organizationId")
        if org_id is not None:
            return str(org_id)
        for value in obj.values():
            found = _find_organization_id(value)
            if found:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = _find_organization_id(value)
            if found:
                return found
    return None


def _find_company_url(obj: Any) -> str | None:
    if isinstance(obj, dict):
        url = obj.get("url")
        if isinstance(url, str) and "/company/" in url and "linkedin.com" in url:
            return url
        for value in obj.values():
            found = _find_company_url(value)
            if found:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = _find_company_url(value)
            if found:
                return found
    return None


def _text_from_chunk(chunk: Any) -> str | None:
    if not isinstance(chunk, list) or len(chunk) < 4:
        return None
    props = chunk[3]
    if not isinstance(props, dict):
        return None
    text_props = props.get("textProps")
    if not isinstance(text_props, dict):
        return None
    text = rsc.render_text(text_props.get("children", [])).strip()
    return text or None


def _extract_logo_url(response_body: str) -> str | None:
    chunk = rsc.get_chunk_parsed(response_body, _LOGO_CHUNK_ID)
    if not isinstance(chunk, list) or len(chunk) < 4:
        return None
    props = chunk[3]
    if not isinstance(props, dict):
        return None
    render_payload = props.get("renderPayload")
    if not isinstance(render_payload, dict):
        return None
    root_url = render_payload.get("rootUrl")
    if not isinstance(root_url, str):
        return None
    renditions = render_payload.get("imageRenditions")
    if not isinstance(renditions, list) or not renditions:
        return root_url
    best = max(renditions, key=lambda r: r.get("width", 0) if isinstance(r, dict) else 0)
    suffix = best.get("suffixUrl") if isinstance(best, dict) else None
    if isinstance(suffix, str):
        return root_url + suffix
    return root_url


def _classify_header_text(text: str) -> str | None:
    if text.endswith(" followers"):
        return "followers_label"
    if text.endswith(" employees"):
        return "size_label"
    if text.endswith(" on LinkedIn"):
        return "linkedin_headcount_label"
    return None


def _extract_header(response_body: str) -> AboutTheCompanyExtract:
    result = AboutTheCompanyExtract(logo_url=_extract_logo_url(response_body))
    chunk = rsc.get_chunk_parsed(response_body, _HEADER_CHUNK_ID)
    if chunk is None:
        result.company_id = _find_organization_id_in_text(response_body)
        return result

    result.company_id = _find_organization_id(chunk) or _find_organization_id_in_text(response_body)
    result.company_url = _find_company_url(chunk)

    industry_candidates: list[str] = []
    for text in _iter_text_props(chunk):
        if _is_noise(text):
            continue
        field = _classify_header_text(text)
        if field == "followers_label":
            result.followers_label = text
        elif field == "size_label":
            result.size_label = text
        elif field == "linkedin_headcount_label":
            result.linkedin_headcount_label = text
        elif result.name is None:
            result.name = text
        else:
            industry_candidates.append(text)

    if result.industry_label is None and industry_candidates:
        result.industry_label = industry_candidates[0]

    return result


def extract_about_the_company(response_body: str) -> AboutTheCompanyExtract:
    """Extract company header, logo, and short description from an aboutTheCompany response."""
    result = _extract_header(response_body)

    chunk = rsc.get_chunk_parsed(response_body, _DESCRIPTION_CHUNK_ID)
    if chunk is not None:
        result.description = _text_from_chunk(chunk)

    return result


def extract_about_the_company_header(response_body: str) -> AboutTheCompanyExtract:
    """Extract company header and logo only (no description blurb)."""
    result = _extract_header(response_body)
    return result
