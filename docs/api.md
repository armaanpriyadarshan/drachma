# API Reference

The Drachma API is the interface agents call to make purchase decisions. The demo exposes three endpoints backed by a FastAPI server reading from seeded mock data.

Base URL (demo): `http://localhost:8000`

## `POST /feed/query`

Rank products in a category against a user preference profile.

**Request**
```json
{
  "category": "chef_knife",
  "preference_profile": {
    "weights": {
      "edge_retention": 0.45,
      "steel_quality": 0.30,
      "balance": 0.15,
      "handle_ergonomics": 0.10
    },
    "constraints": {
      "max_price_usd": 400,
      "blade_length_mm": [200, 240]
    },
    "composite_weights": {
      "quality": 0.50,
      "coverage": 0.25,
      "outcome": 0.20,
      "value": 0.05
    }
  },
  "limit": 5
}
```

`composite_weights` is optional. If omitted, Drachma uses the default (0.40 / 0.20 / 0.25 / 0.15).

**Response**
```json
{
  "category": "chef_knife",
  "candidates": [
    {
      "product_id": "prod_masamoto_ks_210",
      "name": "Masamoto KS Gyuto 210mm",
      "brand": "Masamoto Sohonten",
      "price_usd": 380,
      "composite_score": 0.785,
      "scores": {
        "quality": 0.893,
        "coverage": 0.700,
        "outcome": 0.654,
        "value": 0.653
      },
      "attestation_count": 5,
      "outcome_sample_size": 4.25,
      "rationale": "5 verified creators tested this product including Hiro Tanaka (rep 0.93, specializes in sakai_forged/japanese_knives) ..."
    }
  ]
}
```

## `GET /attestations/{product_id}`

Return all creator attestations for a product, enriched with current (live) creator reputation and declared specialties.

**Response**
```json
{
  "product_id": "prod_nakamura_aogami_gyuto_210",
  "product_name": "Nakamura Hamono Aogami #2 Gyuto 210mm",
  "rubric_version": "chef_knife.v3",
  "attestation_count": 5,
  "attestations": [
    {
      "attestation_id": "att_0042",
      "creator_id": "cr_tanaka_h",
      "creator_name": "Hiro Tanaka",
      "creator_reputation": 0.93,
      "creator_specialties": ["sakai_forged", "japanese_knives", "fit_and_finish"],
      "testing_duration_days": 24,
      "scores": {
        "edge_retention": 9.4,
        "steel_quality": 9.5,
        "balance": 8.7,
        "handle_ergonomics": 8.1,
        "out_of_box_sharpness": 9.1,
        "fit_and_finish": 9.4,
        "corrosion_resistance": 4.3
      },
      "methodology_notes": "...",
      "signed_at": "2026-02-14T12:00:00Z"
    }
  ]
}
```

## `POST /outcomes`

Submit a post-purchase outcome. Updates creator reputation and returns a re-rank for the submitter's profile so the caller can visualize the feedback loop.

**Request**
```json
{
  "product_id": "prod_masamoto_ks_210",
  "preference_vector": {
    "edge_retention": 0.45,
    "steel_quality": 0.30,
    "balance": 0.15,
    "handle_ergonomics": 0.10
  },
  "event": "returned",
  "satisfaction": 0.20
}
```

`event` is one of: `kept` | `returned` | `repurchased` | `exchanged`.

**Response**
```json
{
  "accepted": true,
  "outcome": { "outcome_id": "out_...", "product_id": "...", "event": "returned", "satisfaction": 0.2, ... },
  "reputation_deltas": [
    {
      "creator_id": "cr_tanaka_h",
      "creator_name": "Hiro Tanaka",
      "attestation_id": "att_0042",
      "predicted": 0.872,
      "observed": 0.20,
      "delta": -0.036,
      "new_reputation": 0.894
    }
  ],
  "reranked_candidates": [ ... same shape as /feed/query candidates ... ]
}
```

`reputation_deltas` is sorted by absolute delta, descending. A delta of ±0.003 or smaller is filtered out (too small to visualize).

## `GET /health`

Returns data scale for quick sanity checks.

```json
{ "status": "ok", "category": "chef_knife",
  "products": 34, "creators": 28, "attestations": 236, "outcomes": 220 }
```

## MCP server

Phase 1 of the roadmap ships an MCP server wrapping these endpoints so any agent developer can plug Drachma in without writing HTTP glue. The MCP tool surface mirrors the three endpoints above.

## Auth (production, not demo)

- Brands authenticate with API keys scoped to product submission.
- Creators authenticate with keys that sign attestations.
- Agent callers authenticate with keys scoped to `feed/query` and `outcomes`.

The demo skips all of this.
