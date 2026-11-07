import csv
import json
import re

import responses

from catalog_scraper.cli import main
from catalog_scraper.export import guess_format

from .conftest import BASE, fixture

TRAVEL = BASE + "catalogue/category/books/travel_2/index.html"
PRODUCT_URL_RE = re.compile(r"https://books\.toscrape\.com/catalogue/[^/]+_\d+/index\.html")


def mock_site(product_html: str | None = None):
    responses.get(BASE + "robots.txt", status=404)
    responses.get(BASE, body=fixture("home.html"))
    responses.get(TRAVEL, body=fixture("category_travel.html"))
    responses.get(PRODUCT_URL_RE, body=product_html or fixture("product.html"))


@responses.activate
def test_cli_writes_csv(tmp_path):
    mock_site()
    out = tmp_path / "travel.csv"
    assert main(["-c", "travel", "-o", str(out), "--delay", "0", "--limit", "3"]) == 0
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert len(rows) == 3
    assert rows[0]["title"] == "It's Only the Himalayas"
    assert rows[0]["price"] == "45.17"


@responses.activate
def test_cli_writes_json_and_filters_rating(tmp_path):
    mock_site()
    out = tmp_path / "travel.json"
    assert main(["-c", "travel", "-o", str(out), "--delay", "0", "--min-rating", "3"]) == 0
    assert json.loads(out.read_text(encoding="utf-8")) == []  # fixture book is rated 2


@responses.activate
def test_cli_unknown_category_fails_cleanly(tmp_path, caplog):
    mock_site()
    out = tmp_path / "x.csv"
    assert main(["-c", "nope", "-o", str(out), "--delay", "0"]) == 2
    assert not out.exists()
    assert "unknown category" in caplog.text


@responses.activate
def test_cli_list_categories(capsys):
    mock_site()
    assert main(["--list-categories", "--delay", "0"]) == 0
    assert "travel" in capsys.readouterr().out.split()


@responses.activate
def test_bad_product_page_is_skipped(tmp_path):
    mock_site(product_html="<html>maintenance</html>")
    out = tmp_path / "t.jsonl"
    assert main(["-c", "travel", "-o", str(out), "--delay", "0"]) == 0
    assert out.read_text() == ""


def test_guess_format():
    assert guess_format("a.json") == "json"
    assert guess_format("a.JSONL") == "jsonl"
    assert guess_format("a.txt") == "csv"
    assert guess_format("-") == "csv"
