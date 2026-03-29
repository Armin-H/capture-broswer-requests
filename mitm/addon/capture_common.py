from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen

from mitmproxy import http

BACKEND_URL = os.environ.get("BACKEND_URL", "http://backend:8000").rstrip("/")


def _media_type(content_type: str | None) -> str | None:
    if not content_type:
        return None
    return content_type.split(";")[0].strip().lower()


def _is_json_content_type(media_type: str | None) -> bool:
    if not media_type:
        return False
    return (
        media_type == "application/json"
        or media_type == "text/json"
        or "+json" in media_type
    )


def _body_text(content: bytes | None) -> str | None:
    if not content:
        return None
    return content.decode("utf-8", errors="replace")


def post_json(url: str, payload: dict) -> None:
    data = json.dumps(payload).encode("utf-8")
    req = Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(req, timeout=120) as resp:
        resp.read()


def send_flow_to_backend(flow: http.HTTPFlow) -> None:
    if not flow.response:
        return

    resp = flow.response
    req = flow.request
    if not _is_json_content_type(_media_type(resp.headers.get("Content-Type"))):
        return
    if req.pretty_host == "www.linkedin.com":

        if req.path_components[:3] == ("voyager", "api", "graphql"): 

            payload = {
                "request": {
                    "method": req.method,
                    "url": req.url,
                    "headers": dict(req.headers),
                    "body": _body_text(req.content),
                },
                "response": {
                    "status_code": resp.status_code,
                    "headers": dict(resp.headers),
                    "body": _body_text(resp.content),
                },
            }
            post_json(f"{BACKEND_URL}/mitm/captures", payload)
