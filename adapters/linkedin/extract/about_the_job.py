from adapters.linkedin import rsc

_DESCRIPTION_CHUNK_ID = "6"
_FLIGHT_TEXT_REF = "$9"


def extract_about_the_job(response_body: str) -> str:
    chunk = rsc.get_chunk_parsed(response_body, _DESCRIPTION_CHUNK_ID)
    if chunk is not None:
        text_tree = chunk[3]["textProps"]["children"]
        return rsc.render_text(text_tree)

    matches = rsc.find_embedded_chunks(response_body, _DESCRIPTION_CHUNK_ID)
    if not matches:
        raise ValueError(
            f"aboutTheJob response missing chunk {_DESCRIPTION_CHUNK_ID!r}"
        )
    if len(matches) > 1:
        raise ValueError(
            f"aboutTheJob response has ambiguous embedded chunk {_DESCRIPTION_CHUNK_ID!r}"
        )

    host_raw, chunk, split_at = matches[0]
    intro = rsc.flight_text_prefix(host_raw, split_at)
    text_tree = chunk[3]["textProps"]["children"]
    return rsc.render_text(
        text_tree,
        refs={_FLIGHT_TEXT_REF: f"\n\n{intro}\n\n"},
    ).strip()
