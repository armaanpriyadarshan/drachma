"""Drachma demo API. Three endpoints: feed query, attestations, outcome submission."""

from __future__ import annotations

from statistics import mean
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .ranking import rank
from .store import store


app = FastAPI(title="Drachma API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class PreferenceProfile(BaseModel):
    weights: dict[str, float] = Field(default_factory=dict)
    constraints: dict[str, Any] | None = None


class FeedQuery(BaseModel):
    category: str
    preference_profile: PreferenceProfile
    limit: int = 10


class OutcomePayload(BaseModel):
    product_id: str
    user_profile_tag: str
    event: str  # kept | returned | repurchased | exchanged
    satisfaction: float
    recommendation_id: str | None = None


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "category": store.category,
        "products": len(store.products),
        "creators": len(store.creators),
        "attestations": len(store.attestations),
        "outcomes": len(store.outcomes),
    }


@app.post("/feed/query")
def feed_query(body: FeedQuery) -> dict[str, Any]:
    if body.category != store.category:
        raise HTTPException(404, f"Unknown category {body.category!r} (demo supports {store.category!r})")
    profile = body.preference_profile.model_dump()
    results = rank(profile, store, limit=body.limit)
    for r in results:
        r["rationale"] = _rationale(r)
    return {"category": body.category, "candidates": results}


@app.get("/attestations/{product_id}")
def attestations(product_id: str) -> dict[str, Any]:
    product = store.product(product_id)
    if product is None:
        raise HTTPException(404, f"Unknown product_id {product_id!r}")
    atts = store.attestations_for(product_id)
    enriched = []
    for a in atts:
        creator = store.creator(a["creator_id"]) or {}
        enriched.append({
            **a,
            "creator_name": creator.get("name"),
            "creator_reputation": creator.get("reputation"),
            "creator_specialty": creator.get("specialty"),
        })
    return {
        "product_id": product_id,
        "product_name": product["name"],
        "rubric_version": store.rubric["version"],
        "attestation_count": len(enriched),
        "attestations": enriched,
    }


@app.post("/outcomes")
def outcomes(body: OutcomePayload) -> dict[str, Any]:
    if store.product(body.product_id) is None:
        raise HTTPException(404, f"Unknown product_id {body.product_id!r}")
    record = store.add_outcome(body.model_dump())
    affected = len(store.attestations_for(body.product_id))
    return {"accepted": True, "outcome": record, "affected_attestations": affected}


def _rationale(candidate: dict[str, Any]) -> str:
    atts = store.attestations_for(candidate["product_id"])
    if not atts:
        return "No creator attestations on record."
    top_creators = sorted(
        atts,
        key=lambda a: (store.creator(a["creator_id"]) or {}).get("reputation", 0),
        reverse=True,
    )[:3]
    names = ", ".join((store.creator(a["creator_id"]) or {}).get("name", "?") for a in top_creators)
    avg_edge = mean(a["scores"].get("edge_retention", 0) for a in atts)
    avg_steel = mean(a["scores"].get("steel_quality", 0) for a in atts)
    return (
        f"{len(atts)} verified creators tested this product, including {names}. "
        f"Mean edge_retention {avg_edge:.1f}/10, steel_quality {avg_steel:.1f}/10. "
        f"Ranked against the {candidate['matched_profile_tag']} outcome cohort."
    )
