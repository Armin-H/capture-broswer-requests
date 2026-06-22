"""Reusable SQLAlchemy text() fragments for bronze / capture tables."""

from sqlalchemy import text

MITM_CAPTURES = text("""
    SELECT request_url, response_body FROM mitm_http_captures mhc
""")

MITM_CAPTURES_ORDERED = text("""
    SELECT request_url, response_body FROM mitm_http_captures mhc
    ORDER BY mhc.captured_at_ms DESC
""")
