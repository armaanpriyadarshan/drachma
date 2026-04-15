"""In-memory data store.

Loads mock.json on startup. Supports outcome submission and reputation updates
that persist for the life of the process.
"""

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
        self.outcomes: list[dict[str, Any]] = list(raw["outcomes"])

        self._products_by_id = {p["product_id"]: p for p in self.products}
        self._creators_by_id = {c["creator_id"]: c for c in self.creators}
        # Snapshot of the original reputation so a reset endpoint could restore it.
        self._original_reputation = {c["creator_id"]: float(c["reputation"]) for c in self.creators}
        # Live reputation per creator. Updated in-memory by outcome submission.
        self._live_reputation: dict[str, float] = dict(self._original_reputation)
        self._lock = Lock()

    # ---- Product / creator / attestation accessors ----

    def product(self, product_id: str) -> dict[str, Any] | None:
        return self._products_by_id.get(product_id)

    def creator(self, creator_id: str) -> dict[str, Any] | None:
        return self._creators_by_id.get(creator_id)

    def attestations_for(self, product_id: str) -> list[dict[str, Any]]:
        return [a for a in self.attestations if a["product_id"] == product_id]

    def outcomes_for(self, product_id: str) -> list[dict[str, Any]]:
        return [o for o in self.outcomes if o["product_id"] == product_id]

    # ---- Reputation ----

    def current_reputation(self, creator_id: str) -> float:
        return self._live_reputation.get(creator_id, 0.0)

    def nudge_reputation(self, creator_id: str, delta: float) -> float:
        """Add delta (possibly negative) to the creator's live reputation, clamped to [0, 1]."""
        with self._lock:
            cur = self._live_reputation.get(creator_id, 0.0)
            new = max(0.0, min(1.0, cur + delta))
            self._live_reputation[creator_id] = new
            return new

    def reputation_snapshot(self) -> dict[str, float]:
        return dict(self._live_reputation)

    def reset_reputation(self) -> None:
        with self._lock:
            self._live_reputation = dict(self._original_reputation)

    # ---- Outcomes ----

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
