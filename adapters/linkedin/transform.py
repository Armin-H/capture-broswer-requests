import json

from adapters.linkedin.graphql import parse_variables
from core.db import SessionLocal
from core.queries import MITM_CAPTURES


def flatten_dict(nested_item, parent_key="", sep=".") -> dict:
    items = []

    if isinstance(nested_item, dict):
        for key, value in nested_item.items():
            new_key = parent_key + sep + key if parent_key else key
            items.extend(flatten_dict(value, new_key, sep=sep).items())

    elif isinstance(nested_item, list):
        for i, value in enumerate(nested_item):
            new_key = parent_key + sep + str(i) if parent_key else str(i)
            items.extend(flatten_dict(value, new_key, sep=sep).items())

    else:
        items.append((parent_key, nested_item))

    return dict(items)


def get_all_rows():
    with SessionLocal() as session:
        return session.execute(MITM_CAPTURES)


def extract_all():
    rows = get_all_rows()
    for i, row in enumerate(rows):
        if i > 10:
            break

        request_url, response_body = row
        pv = parse_variables(request_url)
        print(pv)
        print("-" * 40)
        if pv:
            query_name = pv.get("query_name")
            if query_name == "voyagerJobsDashJobPostings":
                flat_body = flatten_dict(json.loads(response_body))
                for k, v in flat_body.items():
                    if type(v) is str and k.lower().endswith(".description.text"):
                        _job_desc = v
            elif query_name == "voyagerJobsDashJobPostingDetailSections":
                flat_body = flatten_dict(json.loads(response_body))
                if "COMPANY_CARD" in pv.get("operation_variables")["cardSectionTypes"]:
                    for k, v in flat_body.items():
                        if type(v) is str and k.lower().endswith(".description"):
                            company_desc = v
                            print(company_desc[:150])
                            print("-" * 40)


if __name__ == "__main__":
    extract_all()
