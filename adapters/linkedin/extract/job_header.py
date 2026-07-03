"""Extract job header fields from /flagship-web/jobs/search-results/ RSC responses."""

from __future__ import annotations

from dataclasses import dataclass

from adapters.linkedin import rsc

_HEADER_CHUNK_ID = "28"
_PROMOTED_MARKER = "Promoted by hirer ·"
_UI_NOISE = frozenset({"div", "p", "span", "·"})


@dataclass
class JobHeaderExtract:
    title: str | None = None
    company_name: str | None = None
    location: str | None = None
    listed_at: str | None = None
    apply_count: str | None = None
    promoted: bool = False
    hiring_insights: str | None = None


def _header_text_values(tree: rsc.Tree) -> list[str]:
    return [
        text
        for node in tree.strings()
        if (text := (node.value or "").strip())
        and text not in _UI_NOISE
        and not text.startswith("$")
    ]


def extract_job_header(
    response_body: str, *, job_id: str | None = None
) -> JobHeaderExtract:
    """Extract the job summary card from a search-results RSC response."""
    del job_id  # reserved for future validation / logging

    chunks = rsc.parse_stream(response_body)
    parsed = rsc.get_chunk_parsed(response_body, _HEADER_CHUNK_ID)
    tree = rsc.build_component_tree(chunks, parsed)
    values = _header_text_values(tree)

    promoted = values[5] == _PROMOTED_MARKER
    hiring_insights = values[6] if promoted else values[5]
    return JobHeaderExtract(
        company_name=values[0],
        title=values[1],
        location=values[2],
        listed_at=values[3],
        apply_count=values[4],
        promoted=promoted,
        hiring_insights=hiring_insights,
    )
