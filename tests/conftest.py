from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
BASE = "https://books.toscrape.com/"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture
def no_sleep():
    calls: list[float] = []
    return calls.append, calls
