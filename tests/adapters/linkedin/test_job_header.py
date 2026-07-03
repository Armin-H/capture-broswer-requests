from pathlib import Path

from adapters.linkedin.extract.job_header import extract_job_header

FIXTURES_DIR = (
    Path(__file__).resolve().parents[2] / "fixtures" / "linkedin" / "job_header"
)


def load_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text()


def test_extract_non_promoted_regression_fixture():
    header = extract_job_header(load_fixture("non_promoted.txt"))

    assert header.company_name == "South Australia Police"
    assert header.title == "Data Analyst"
    assert header.location == "Adelaide, South Australia, Australia"
    assert header.listed_at == "2 weeks ago"
    assert header.apply_count == "Over 100 people clicked apply"
    assert header.promoted is False
    assert header.hiring_insights == "Responses managed off LinkedIn"


def test_extract_promoted_fixture():
    header = extract_job_header(load_fixture("promoted.txt"))

    assert header.company_name == "Kmart Australia Limited"
    assert header.title == "Facilities Data Analyst"
    assert header.location == "Chadstone, Victoria, Australia"
    assert header.listed_at == "Reposted 1 day ago"
    assert header.apply_count == "Over 100 people clicked apply"
    assert header.promoted is True
    assert header.hiring_insights == "Responses managed off LinkedIn"
