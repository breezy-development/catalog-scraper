from __future__ import annotations

import argparse
import logging
import sys
import time

from . import __version__
from .export import FORMATS, guess_format, write
from .fetch import PoliteFetcher
from .scraper import BASE_URL, CatalogScraper


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="catalog-scraper",
        description="Scrape books.toscrape.com politely and export clean CSV, JSON or JSONL.",
    )
    p.add_argument("-c", "--category", help="category slug, e.g. travel or mystery (default: all)")
    p.add_argument("-o", "--out", default="-", help="output file (default: stdout)")
    p.add_argument("-f", "--format", choices=FORMATS, help="output format (default: from --out)")
    p.add_argument("--max-pages", type=int, help="stop after N listing pages")
    p.add_argument("--limit", type=int, help="stop after N books")
    p.add_argument("--min-rating", type=int, default=0, choices=range(0, 6), metavar="0-5")
    p.add_argument("--delay", type=float, default=1.0, help="seconds between requests (default 1)")
    p.add_argument("--base-url", default=BASE_URL, help=argparse.SUPPRESS)
    p.add_argument("--list-categories", action="store_true", help="print category slugs and exit")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )
    log = logging.getLogger("catalog_scraper")

    scraper = CatalogScraper(PoliteFetcher(delay=args.delay), base_url=args.base_url)

    if args.list_categories:
        for slug in sorted(scraper.categories()):
            print(slug)
        return 0

    try:
        start_url = scraper.start_url(args.category)
    except KeyError as exc:
        log.error("%s", exc.args[0])
        return 2

    fmt = args.format or guess_format(args.out)
    books = scraper.iter_books(
        max_pages=args.max_pages,
        limit=args.limit,
        min_rating=args.min_rating,
        start_url=start_url,
    )

    started = time.monotonic()
    if args.out == "-":
        count = write(books, fmt, sys.stdout)
    else:
        with open(args.out, "w", newline="", encoding="utf-8") as fh:
            count = write(books, fmt, fh)

    where = "stdout" if args.out == "-" else args.out
    log.info("wrote %d books to %s as %s in %.1fs", count, where, fmt, time.monotonic() - started)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
