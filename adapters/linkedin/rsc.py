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


def extract_embedded_chunk_json(
    raw: str, chunk_id: str
) -> tuple[Any, int] | None:
    """Parse a chunk payload embedded inside another chunk's raw string."""
    marker = f"{chunk_id}:"
    start = raw.find(marker)
    if start == -1:
        return None
    json_part = raw[start + len(marker) :]
    if not json_part.startswith("["):
        return None
    depth = 0
    for index, char in enumerate(json_part):
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return json.loads(json_part[: index + 1]), start
    return None


def flight_text_prefix(host_raw: str, split_at: int) -> str:
    """Extract inline flight text from a T-prefixed host chunk payload."""
    prefix = host_raw[:split_at]
    comma = prefix.find(",")
    if prefix.startswith("T") and comma != -1:
        return prefix[comma + 1 :]
    return prefix


def find_embedded_chunks(
    response_body: str, chunk_id: str
) -> list[tuple[str, Any, int]]:
    matches: list[tuple[str, Any, int]] = []
    for host_raw in parse_stream(response_body).values():
        parsed = extract_embedded_chunk_json(host_raw, chunk_id)
        if parsed is not None:
            chunk, split_at = parsed
            matches.append((host_raw, chunk, split_at))
    return matches


def render_text(
    element: Any,
    *,
    refs: dict[str, str] | None = None,
    strong_format: str = "\n## ",
    li_format: str = "\n- ",
) -> str:
    result: list[str] = []
    if element is None:
        return ""
    if isinstance(element, str):
        if refs is not None and element in refs:
            result.append(refs[element])
        elif not element.startswith("$"):
            result.append(element)
    elif is_rsc_node(element):
        component_type = element[1]
        if component_type == "strong":
            result.append(strong_format)
        elif component_type == "li":
            result.append(li_format)
        elif component_type == "br":
            result.append("\n")
        props = element[3]
        if isinstance(props, dict):
            for child in props.get("children", []):
                result.append(
                    render_text(
                        child,
                        refs=refs,
                        strong_format=strong_format,
                        li_format=li_format,
                    )
                )
    elif isinstance(element, list):
        for child in element:
            result.append(
                render_text(
                    child,
                    refs=refs,
                    strong_format=strong_format,
                    li_format=li_format,
                )
            )
    return "".join(result)


def iter_chunk_nodes(response_body: str) -> Iterator[tuple[str, Any]]:
    for chunk_id, data in parse_stream(response_body).items():
        yield chunk_id, json.loads(data)
