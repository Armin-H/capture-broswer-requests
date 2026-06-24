import json
from collections import defaultdict
from urllib.parse import parse_qs, urlparse

from adapters.linkedin.graphql import (
    extract_job_posting_id,
    extract_query_id,
    parse_variables,
)
from adapters.linkedin.transform import flatten_dict, get_all_rows
from core.db import SessionLocal
from core.queries import MITM_CAPTURES


def find_keys(response_body: str, search_string: str):
    """Find keys in a response body that contain a search string."""
    if search_string.lower() in response_body.lower():
        flat_body = flatten_dict(json.loads(response_body))
        keys = []
        for k, v in flat_body.items():
            if type(v) is str:
                if search_string.lower() in v.lower():
                    keys.append(k)
        return keys
    return []


def query_name_counts():
    query_names = defaultdict(int)
    rows = get_all_rows()
    for row in rows:
        request_url, response_body = row
        query_params = parse_qs(urlparse(request_url).query)
        query_id = query_params["queryId"]
        query_name, _, query_hash = query_id[0].partition(".")
        query_names[query_name] += 1
    sorted_query_names = sorted(query_names.items(), key=lambda item: item[1], reverse=True)
    for query_name, count in sorted_query_names:
        print(f"{query_name}: {count}")


def locate_stuff(search_string: str):
    rows = get_all_rows()
    for row in rows:
        request_url, response_body = row
        keys = find_keys(response_body, search_string)
        if keys:
            job_posting_id = extract_job_posting_id(request_url)
            query_id = extract_query_id(request_url)
            parsed_variables = parse_variables(request_url)
            if parsed_variables:
                print(parsed_variables.get("query_name"))
                print(parsed_variables.get("query_hash"))
                print(parsed_variables.get("operation_variables"))
            print(job_posting_id)
            print(keys)
            print("-" * 100)


def pprint_response_body(response_body: str):
    flat_body = flatten_dict(json.loads(response_body))
    for k, v in flat_body.items():
        if type(v) is str and k.endswith(".jobPostingTitle"):
            print(k)
            print(v[:150])
            print("-" * 100)


def explore_top_card():
    rows = get_all_rows()
    for row in rows:
        request_url, response_body = row
        parsed_variables = parse_variables(request_url)
        if parsed_variables:
            operation_variables = parsed_variables.get("operation_variables")
            if operation_variables:
                if "TOP_CARD" in operation_variables.get("cardSectionTypes", []):
                    print(parsed_variables.get("query_name"))
                    print(parsed_variables.get("query_hash"))
                    print(parsed_variables.get("operation_variables"))
                    pprint_response_body(response_body)


def locate_company(job_posting_id: str, search_string: str):
    with SessionLocal() as session:
        rows = session.execute(MITM_CAPTURES)
        keys = []
        for row in rows:
            request_url, response_body = row
            flat_body = flatten_dict(json.loads(response_body))
            query_id = extract_query_id(request_url)
            job_posting_id = extract_job_posting_id(request_url)
            if "COMPANY_CARD" in request_url:
                print(query_id, job_posting_id)
    print(keys)
    return keys


if __name__ == "__main__":
    locate_stuff("AI ENGINEER")
