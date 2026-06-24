from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse


def extract_query_id(request_url: str) -> str | None:
    request_url_parsed = urlparse(request_url)
    match = re.search(r"queryId=([a-zA-Z0-9]+)", request_url_parsed.query)
    if match:
        return match.group(1)
    return None


def extract_job_posting_id(request_url: str) -> str | None:
    request_url_parsed = urlparse(request_url)
    match = re.search(r"fsd_jobPosting%([a-zA-Z0-9]+)", request_url_parsed.query)
    if match:
        return match.group(1)
    return None


def parse_request_url(request_url: str):
    return parse_qs(urlparse(request_url).query)


@dataclass
class Token:
    type: str
    value: str
    line: int
    column: int


def tokenize(code: str):
    token_specification = [
        ("URN", r"urn:li:[a-zA-Z0-9_:]+"),
        ("BOOL", r"true|false"),
        ("NUMBER", r"\d+(\.\d+)?"),
        ("ID", r"[a-zA-Z_][a-zA-Z0-9_]*"),
        ("LPAREN", r"\("),
        ("RPAREN", r"\)"),
        ("COLON", r":"),
        ("COMMA", r","),
        ("NEWLINE", r"\n"),
        ("SKIP", r"[ \t]+"),
        ("MISMATCH", r"."),
    ]

    tok_regex = "|".join("(?P<%s>%s)" % pair for pair in token_specification)
    line_num = 1
    line_start = 0

    for mo in re.finditer(tok_regex, code):
        kind = mo.lastgroup
        value = mo.group()
        column = mo.start() - line_start

        if kind == "NUMBER":
            value = float(value) if "." in value else int(value)
        elif kind == "BOOL":
            value = value == "true"
        elif kind == "NEWLINE":
            line_start = mo.end()
            line_num += 1
            continue
        elif kind == "SKIP":
            continue
        elif kind == "MISMATCH":
            raise RuntimeError(f"{value!r} unexpected on line {line_num}")

        yield Token(kind, value, line_num, column)


class PSpecParser:
    """Parses pspec text: ``( key:val, key:val )`` and ``List(...)``."""

    def __init__(self, text: str):
        self.tokens = tokenize(text)
        self.current_token = None
        self.next_token()

    def next_token(self):
        try:
            self.current_token = next(self.tokens)
        except StopIteration:
            self.current_token = None

    def eat(self, token_type):
        if self.current_token and self.current_token.type == token_type:
            token = self.current_token
            self.next_token()
            return token
        else:
            actual = self.current_token.type if self.current_token else "EOF"
            raise SyntaxError(f"Expected {token_type}, but got {actual}")

    def parse_object(self):
        result = {}
        self.eat("LPAREN")

        while self.current_token and self.current_token.type != "RPAREN":
            key, value = self.parse_pair()
            result[key] = value

            if self.current_token and self.current_token.type == "COMMA":
                self.eat("COMMA")

        self.eat("RPAREN")
        return result

    def parse_pair(self):
        key_token = self.eat("ID")
        self.eat("COLON")
        value = self.parse_value()
        return key_token.value, value

    def parse_value(self):
        token = self.current_token

        if token.type == "LPAREN":
            return self.parse_object()

        elif token.type == "ID" and token.value == "List":
            return self.parse_list()

        elif token.type in ("NUMBER", "BOOL", "URN", "ID"):
            self.next_token()
            return token.value

        raise SyntaxError(f"Unexpected value type: {token.type}")

    def parse_list(self):
        self.eat("ID")
        self.eat("LPAREN")
        items = []

        while self.current_token and self.current_token.type != "RPAREN":
            items.append(self.parse_value())
            if self.current_token and self.current_token.type == "COMMA":
                self.eat("COMMA")

        self.eat("RPAREN")
        return items

    def is_fully_consumed(self):
        return self.current_token is None


def is_valid_pspec(txt: str) -> bool:
    try:
        p = PSpecParser(txt)
        p.parse_object()
        return p.is_fully_consumed()
    except (SyntaxError, RuntimeError, StopIteration):
        return False


def try_parse_pspec(txt: str):
    try:
        p = PSpecParser(txt)
        data = p.parse_object()
        return data if p.is_fully_consumed() else None
    except Exception:
        return None


def parse_variables(request_url: str):
    """Decode ``queryId`` and ``variables`` from a captured GraphQL request URL."""
    query_params = parse_qs(urlparse(request_url).query)

    query_id = query_params["queryId"]
    query_name, _, query_hash = query_id[0].partition(".")

    variables = query_params.get("variables", ["()"])
    if variables[0] != "()":
        operation_variables = try_parse_pspec(variables[0])
        if operation_variables is not None:
            return {
                "query_name": query_name,
                "query_hash": query_hash,
                "operation_variables": operation_variables,
            }
    return None
