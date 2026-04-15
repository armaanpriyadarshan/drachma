"""In-memory data store. Loads mock.json on startup; accepts outcome submissions at runtime."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "mock.json"


class Store:
    def __init__(self, path: Path = DATA_PATH) -> None:
        with path.open() as f:
            raw = json.load(f)
        self.category: str = raw["category"]
        self.rubric: dict[str, Any] = raw["rubric"]
        self.products: list[dict[str, Any]] = raw["products"]
        self.creators: list[dict[str, Any]] = raw["creators"]
        self.attestations: list[dict[str, Any]] = raw["attestations"]
        self.outcomes: list[dict[str, Any]] = raw["outcomes"]

        self._products_by_id = {p["product_id"]: p for p in self.products}
        self._creators_by_id = {c["creator_id"]: c for c in self.creators}
        self._lock = Lock()

    def product(self, product_id: str) -> dict[str, Any] | None:
        return self._products_by_id.get(product_id)

    def creator(self, creator_id: str) -> dict[str, Any] | None:
        return self._creators_by_id.get(creator_id)

    def attestations_for(self, product_id: str) -> list[dict[str, Any]]:
        return [a for a in self.attestations if a["product_id"] == product_id]

    def outcomes_for(self, product_id: str) -> list[dict[str, Any]]:
        return [o for o in self.outcomes if o["product_id"] == product_id]

    def add_outcome(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            record = {
                "outcome_id": f"out_{uuid.uuid4().hex[:8]}",
                "reported_at": datetime.now(timezone.utc).isoformat(),
                **payload,
            }
            self.outcomes.append(record)
        return record


store = Store()
