"""Pure HTML parsing functions. No network access, so they are easy to test."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .models import Book

RATING_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
CURRENCY_SYMBOLS = {"£": "GBP", "$": "USD", "€": "EUR"}


@dataclass(frozen=True)
class ListingPage:
    product_urls: list[str]
    next_url: str | None


def parse_categories(html: str, base_url: str) -> dict[str, str]:
    """Map lower-case category slug (e.g. "travel") to its absolute listing URL."""
    soup = BeautifulSoup(html, "html.parser")
    result: dict[str, str] = {}
    for link in soup.select(".side_categories ul ul a"):
        name = link.get_text(strip=True)
        result[slugify(name)] = urljoin(base_url, link["href"])
    return result


def parse_listing(html: str, page_url: str) -> ListingPage:
    soup = BeautifulSoup(html, "html.parser")
    product_urls = [
        urljoin(page_url, a["href"]) for a in soup.select("article.product_pod h3 a[href]")
    ]
    next_link = soup.select_one("ul.pager li.next a[href]")
    next_url = urljoin(page_url, next_link["href"]) if next_link else None
    return ListingPage(product_urls=product_urls, next_url=next_url)


def parse_product(html: str, page_url: str) -> Book:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one(".product_main")
    if main is None:
        raise ValueError(f"not a product page: {page_url}")

    title = main.h1.get_text(strip=True)
    currency, price = parse_price(main.select_one(".price_color").get_text(strip=True))

    rating_tag = main.select_one("p.star-rating")
    rating_word = next((c for c in rating_tag.get("class", []) if c in RATING_WORDS), None)

    table = {
        row.th.get_text(strip=True): row.td.get_text(strip=True)
        for row in soup.select("table.table tr")
        if row.th and row.td
    }

    crumbs = [li.get_text(strip=True) for li in soup.select("ul.breadcrumb li")]
    category = crumbs[2] if len(crumbs) >= 4 else ""

    desc_header = soup.select_one("#product_description")
    desc_tag = desc_header.find_next_sibling("p") if desc_header else None
    description = desc_tag.get_text(strip=True) if desc_tag else ""
    description = re.sub(r"\s*\.\.\.more$", "", description)

    img = soup.select_one("#product_gallery img[src]")

    return Book(
        title=title,
        price=price,
        currency=currency,
        in_stock=parse_stock(table.get("Availability", "")),
        rating=RATING_WORDS.get(rating_word, 0),
        category=category,
        upc=table.get("UPC", ""),
        url=page_url,
        image_url=urljoin(page_url, img["src"]) if img else "",
        description=description,
    )


def parse_price(text: str) -> tuple[str, float]:
    match = re.search(r"([£$€])\s*([\d,]+(?:\.\d+)?)", text)
    if not match:
        raise ValueError(f"unrecognised price: {text!r}")
    return CURRENCY_SYMBOLS[match.group(1)], float(match.group(2).replace(",", ""))


def parse_stock(text: str) -> int:
    match = re.search(r"\((\d+) available\)", text)
    return int(match.group(1)) if match else 0


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
