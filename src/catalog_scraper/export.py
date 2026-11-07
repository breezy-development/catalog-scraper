from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from pathlib import Path
from typing import TextIO

from .models import Book

FORMATS = ("csv", "json", "jsonl")


def write(books: Iterable[Book], fmt: str, out: TextIO) -> int:
    if fmt == "csv":
        return write_csv(books, out)
    if fmt == "json":
        return write_json(books, out)
    if fmt == "jsonl":
        return write_jsonl(books, out)
    raise ValueError(f"unknown format {fmt!r}; choose from {FORMATS}")


def write_csv(books: Iterable[Book], out: TextIO) -> int:
    writer = csv.DictWriter(out, fieldnames=Book.field_names())
    writer.writeheader()
    count = 0
    for book in books:
        writer.writerow(book.to_dict())
        count += 1
    return count


def write_json(books: Iterable[Book], out: TextIO) -> int:
    rows = [b.to_dict() for b in books]
    json.dump(rows, out, ensure_ascii=False, indent=2)
    out.write("\n")
    return len(rows)


def write_jsonl(books: Iterable[Book], out: TextIO) -> int:
    count = 0
    for book in books:
        out.write(json.dumps(book.to_dict(), ensure_ascii=False) + "\n")
        out.flush()
        count += 1
    return count


def guess_format(path: str | None, default: str = "csv") -> str:
    if not path or path == "-":
        return default
    suffix = Path(path).suffix.lstrip(".").lower()
    return suffix if suffix in FORMATS else default
