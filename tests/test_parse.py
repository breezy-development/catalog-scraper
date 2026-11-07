import pytest

from catalog_scraper.parse import (
    parse_categories,
    parse_listing,
    parse_price,
    parse_product,
    parse_stock,
    slugify,
)

from .conftest import BASE, fixture

TRAVEL = BASE + "catalogue/category/books/travel_2/index.html"
MYSTERY = BASE + "catalogue/category/books/mystery_3/index.html"
PRODUCT = BASE + "catalogue/its-only-the-himalayas_981/index.html"


def test_parse_categories_returns_absolute_urls():
    cats = parse_categories(fixture("home.html"), BASE)
    assert len(cats) == 50
    assert cats["travel"] == TRAVEL
    assert cats["historical-fiction"].endswith("historical-fiction_4/index.html")


def test_listing_without_next_page():
    page = parse_listing(fixture("category_travel.html"), TRAVEL)
    assert len(page.product_urls) == 11
    assert page.product_urls[0] == PRODUCT
    assert page.next_url is None


def test_listing_with_next_page():
    page = parse_listing(fixture("category_mystery_page1.html"), MYSTERY)
    assert len(page.product_urls) == 20
    assert page.next_url == BASE + "catalogue/category/books/mystery_3/page-2.html"


def test_parse_product_fields():
    book = parse_product(fixture("product.html"), PRODUCT)
    assert book.title == "It's Only the Himalayas"
    assert book.price == 45.17
    assert book.currency == "GBP"
    assert book.in_stock == 19
    assert book.rating == 2
    assert book.category == "Travel"
    assert book.upc == "a22124811bfa8350"
    assert book.image_url.startswith(BASE + "media/cache/")
    assert book.description.startswith("“Wherever you go")
    assert not book.description.endswith("...more")


def test_parse_product_rejects_non_product_page():
    with pytest.raises(ValueError):
        parse_product(fixture("category_travel.html"), TRAVEL)


@pytest.mark.parametrize(
    "text,expected",
    [("£45.17", ("GBP", 45.17)), ("$1,299.00", ("USD", 1299.0)), ("€ 9", ("EUR", 9.0))],
)
def test_parse_price(text, expected):
    assert parse_price(text) == expected


def test_parse_price_rejects_garbage():
    with pytest.raises(ValueError):
        parse_price("free")


def test_parse_stock():
    assert parse_stock("In stock (19 available)") == 19
    assert parse_stock("Out of stock") == 0


def test_slugify():
    assert slugify("Historical Fiction") == "historical-fiction"
    assert slugify("Sequential Art") == "sequential-art"
