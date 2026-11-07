from __future__ import annotations

from dataclasses import asdict, dataclass, fields


@dataclass(frozen=True)
class Book:
    title: str
    price: float
    currency: str
    in_stock: int
    rating: int
    category: str
    upc: str
    url: str
    image_url: str
    description: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def field_names(cls) -> list[str]:
        return [f.name for f in fields(cls)]
