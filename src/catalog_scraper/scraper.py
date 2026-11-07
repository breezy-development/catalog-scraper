from __future__ import annotations

import logging
from collections.abc import Iterator

from .fetch import PoliteFetcher
from .models import Book
from .parse import parse_categories, parse_listing, parse_product

log = logging.getLogger(__name__)

BASE_URL = "https://books.toscrape.com/"


class CatalogScraper:
    def __init__(self, fetcher: PoliteFetcher, base_url: str = BASE_URL) -> None:
        self.fetcher = fetcher
        self.base_url = base_url

    def categories(self) -> dict[str, str]:
        return parse_categories(self.fetcher.get(self.base_url), self.base_url)

    def start_url(self, category: str | None) -> str:
        if not category:
            return self.base_url + "catalogue/page-1.html"
        cats = self.categories()
        if category not in cats:
            raise KeyError(
                f"unknown category {category!r}; run with --list-categories to see options"
            )
        return cats[category]

    def iter_product_urls(self, start_url: str, max_pages: int | None = None) -> Iterator[str]:
        url: str | None = start_url
        pages = 0
        while url and (max_pages is None or pages < max_pages):
            listing = parse_listing(self.fetcher.get(url), url)
            pages += 1
            log.info("listing page %d: %d products", pages, len(listing.product_urls))
            yield from listing.product_urls
            url = listing.next_url

    def iter_books(
        self,
        category: str | None = None,
        max_pages: int | None = None,
        limit: int | None = None,
        min_rating: int = 0,
        start_url: str | None = None,
    ) -> Iterator[Book]:
        seen: set[str] = set()
        produced = 0
        start_url = start_url or self.start_url(category)
        for url in self.iter_product_urls(start_url, max_pages):
            if url in seen:
                continue
            seen.add(url)
            try:
                book = parse_product(self.fetcher.get(url), url)
            except Exception as exc:  # one bad page must not kill a long run
                log.warning("skipping %s: %s", url, exc)
                continue
            if book.rating < min_rating:
                continue
            yield book
            produced += 1
            if limit is not None and produced >= limit:
                return
