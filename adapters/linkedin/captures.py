"""Load and filter LinkedIn SDUI component captures from mitm_http_captures."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

from sqlalchemy import text

from core.db import SessionLocal

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

COMPONENT_PATH = "/flagship-web/rsc-action/actions/component"
COMPONENT_PREFIX = "com.linkedin.sdui.generated.jobseeker.dsl.impl."

ComponentRow = tuple[str, str, str]

_LOAD_QUERY = text("""
    SELECT request_url, request_body, response_body
    FROM mitm_http_captures
    WHERE request_body IS NOT NULL
      AND response_body IS NOT NULL
    ORDER BY captured_at_ms DESC
""")


def component_suffix(url: str) -> str:
    component_id = parse_qs(urlparse(url).query)["componentId"][0]
    if component_id.startswith(COMPONENT_PREFIX):
        return component_id[len(COMPONENT_PREFIX) :]
    return component_id


def job_id_from_request_body(request_body: str) -> str:
    payload = json.loads(request_body)["clientArguments"]["payload"]
    return str(payload["jobId"])


def load_component_rows(session: Session | None = None) -> list[ComponentRow]:
    if session is None:
        with SessionLocal() as session:
            return load_component_rows(session)
    return list(session.execute(_LOAD_QUERY).fetchall())


def filter_rows(
    rows: list[ComponentRow],
    *,
    suffix: str | None = None,
    job_id: str | None = None,
) -> list[ComponentRow]:
    out: list[ComponentRow] = []
    job_id = str(job_id) if job_id is not None else None
    for url, request_body, response_body in rows:
        if urlparse(url).path != COMPONENT_PATH:
            continue
        if suffix is not None and component_suffix(url) != suffix:
            continue
        if job_id is not None and job_id_from_request_body(request_body) != job_id:
            continue
        out.append((url, request_body, response_body))
    return out
