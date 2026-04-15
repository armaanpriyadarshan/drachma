"""Drachma demo API."""

from __future__ import annotations

from statistics import mean
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .ranking import rank, update_reputations_for_outcome
from .store import store


app = FastAPI(title="Drachma API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class PreferenceProfile(BaseModel):
    weights: dict[str, float] = Field(default_factory=dict)
    constraints: dict[str, Any] | None = None
    # Per-profile weights on the four composite dimensions. Intentionally exposed
    # so the UI can display them — nothing hidden.
    composite_weights: dict[str, float] | None = None


class FeedQuery(BaseModel):
    category: str
    preference_profile: PreferenceProfile
    limit: int = 10


class OutcomePayload(BaseModel):
    product_id: str
    preference_vector: dict[str, float]
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
        r["rationale"] = _rationale(r, profile.get("weights", {}))
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
            "creator_reputation": store.current_reputation(a["creator_id"]),
            "creator_specialties": creator.get("specialties", []),
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
    product = store.product(body.product_id)
    if product is None:
        raise HTTPException(404, f"Unknown product_id {body.product_id!r}")

    # Apply reputation updates BEFORE storing the outcome so that the re-rank
    # uses the new reputation values.
    deltas = update_reputations_for_outcome(
        store,
        body.product_id,
        body.preference_vector,
        body.satisfaction,
    )
    record = store.add_outcome(body.model_dump())

    # Re-rank from the submitter's profile so the UI can show the live ranking shift.
    reranked = rank(
        {"weights": body.preference_vector, "constraints": None},
        store,
        limit=8,
    )
    for r in reranked:
        r["rationale"] = _rationale(r, body.preference_vector)

    return {
        "accepted": True,
        "outcome": record,
        "reputation_deltas": deltas,
        "reranked_candidates": reranked,
    }


# ---------------------------------------------------------------------------
# Rationale
# ---------------------------------------------------------------------------

def _rationale(candidate: dict[str, Any], weights: dict[str, float]) -> str:
    """
    Short prose citing the per-dimension evidence. Prefers to name specialist
    creators who are credentialed for the user's weighted attributes.
    """
    atts = store.attestations_for(candidate["product_id"])
    if not atts:
        return "No creator attestations on record."

    # Pick the top-weighted user attributes.
    top_attrs = sorted(weights.items(), key=lambda kv: -kv[1])[:2]
    top_attr_names = [a for a, _ in top_attrs if _ > 0]

    # Find specialist creators for those attrs, citing only their aligned specialties.
    from .ranking import SPECIALTY_ATTRS, creator_specialty_attrs
    specialist_cites: list[str] = []
    for att in atts:
        creator = store.creator(att["creator_id"]) or {}
        spec_attrs = creator_specialty_attrs(creator)
        if not any(a in spec_attrs for a in top_attr_names):
            continue
        aligned = [
            s for s in creator.get("specialties", [])
            if SPECIALTY_ATTRS.get(s, set()) & set(top_attr_names)
        ] or creator.get("specialties", [])[:2]
        rep = store.current_reputation(creator.get("creator_id", ""))
        specialist_cites.append(
            f"{creator.get('name','?')} (rep {rep:.2f}, specializes in {'/'.join(aligned[:2])})"
        )
        if len(specialist_cites) >= 2:
            break

    opener = f"{len(atts)} verified creators tested this product"
    if specialist_cites:
        opener += f" including {', '.join(specialist_cites)}"

    pieces = [opener]
    if top_attr_names:
        means_str = []
        for a in top_attr_names:
            vals = [att["scores"].get(a) for att in atts if att["scores"].get(a) is not None]
            if vals:
                means_str.append(f"{a.replace('_',' ')} {mean(vals):.1f}/10")
        if means_str:
            pieces.append("Mean " + ", ".join(means_str))

    return ". ".join(pieces) + "."
