from adapters.linkedin import rsc

_DESCRIPTION_CHUNK_ID = "6"

def extract_about_the_job(response_body: str) -> str:
    chunk = rsc.get_chunk_parsed(response_body, _DESCRIPTION_CHUNK_ID)
    if chunk is None:
        raise ValueError(
            f"aboutTheJob response missing chunk {_DESCRIPTION_CHUNK_ID!r}"
        )
    _, _, _, props_dict = chunk
    text_tree = props_dict["textProps"]["children"]
    return rsc.render_text(text_tree)
