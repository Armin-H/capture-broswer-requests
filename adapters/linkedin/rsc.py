"""Parse LinkedIn SDUI RSC response streams and render text trees."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any


def parse_stream(response_body: str) -> dict[str, str]:
    chunks: dict[str, str] = {}
    for line in response_body.splitlines():
        if not line.strip():
            continue
        chunk_id, data = line.split(":", 1)
        chunks[chunk_id] = data
    return chunks


def get_chunk(response_body: str, chunk_id: str) -> str | None:
    return parse_stream(response_body).get(chunk_id)


def get_chunk_parsed(response_body: str, chunk_id: str) -> Any:
    raw = get_chunk(response_body, chunk_id)
    return None if raw is None else json.loads(raw)


def is_rsc_node(value: Any) -> bool:
    return isinstance(value, list) and len(value) == 4 and value[0] == "$"


def find_rsc_nodes(obj: Any) -> list[list[Any]]:
    found: list[list[Any]] = []

    def walk(value: Any) -> None:
        if is_rsc_node(value):
            found.append(value)
        elif isinstance(value, dict):
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(obj)
    return found


def get_path(obj: Any, *keys: str) -> Any:
    for key in keys:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


def render_text(element: Any) -> str:
    result: list[str] = []
    if element is None:
        return ""
    if isinstance(element, str):
        if not element.startswith("$"):
            result.append(element)
    elif is_rsc_node(element):
        component_type = element[1]
        if component_type == "strong":
            result.append("\n## ")
        elif component_type == "li":
            result.append("\n- ")
        elif component_type == "br":
            result.append("\n")
        props = element[3]
        if isinstance(props, dict):
            for child in props.get("children", []):
                result.append(render_text(child))
    elif isinstance(element, list):
        for child in element:
            result.append(render_text(child))
    return "".join(result)


def iter_chunk_nodes(response_body: str) -> Iterator[tuple[str, Any]]:
    for chunk_id, data in parse_stream(response_body).items():
        yield chunk_id, json.loads(data)
