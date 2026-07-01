from pathlib import Path

import pytest

from adapters.linkedin.extract.about_the_job import extract_about_the_job

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "linkedin" / "about_the_job"

EMBEDDED_SECTIONS = (
    "Job Description",
    "Practice Specialist Solution Architect",
    "We are seeking an experienced Practice Specialist",
    "Responsibilities",
    "Lead client discussions",
    "Experience",
    "Qualifications",
    "Working With Wipro",
    "Benefits @ Wipro",
    "Mandatory Skills: GenAI Consulting for Apps & Infra",
    "Reinvent your world",
)

STANDALONE_SECTIONS = (
    "About the role",
    "What you\u2019ll do?",
    "Design, build and evolve core services",
    "What will you bring?",
    "What next?",
    "To be eligible for this position",
    "Acknowledgement of Country",
    "Diversity + Inclusion",
)


def load_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text()


def test_standalone_chunk_6_fixture():
    description = extract_about_the_job(load_fixture("standalone_chunk_6.txt"))
    expected = load_fixture("standalone_chunk_6.expected.txt")

    assert description == expected
    for section in STANDALONE_SECTIONS:
        assert section in description, f"missing section: {section!r}"


def test_missing_chunk_6_fixture_raises():
    with pytest.raises(ValueError, match="missing chunk '6'"):
        extract_about_the_job(load_fixture("missing_chunk_6.txt"))


def test_embedded_chunk_6_in_9_fixture():
    description = extract_about_the_job(load_fixture("embedded_chunk_6_in_9.txt"))
    expected = load_fixture("embedded_chunk_6_in_9.expected.txt")

    assert description == expected
    for section in EMBEDDED_SECTIONS:
        assert section in description, f"missing section: {section!r}"
