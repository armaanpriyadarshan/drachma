# API Reference

The Drachma API is the interface agents call to make purchase decisions. The demo exposes three endpoints backed by a FastAPI server reading from mock JSON.

Base URL (demo): `http://localhost:8000`

## `POST /feed/query`

Rank products in a category against a user preference profile.

**Request**
```json
{
  "category": "chef_knife",
  "preference_profile": {
    "weights": {
      "edge_retention": 0.4,
      "carbon_content": 0.3,
      "balance": 0.2,
      "handle_ergonomics": 0.1
    },
    "constraints": {
      "max_price_usd": 400,
      "blade_length_mm": [200, 240]
    }
  },
  "limit": 10
}
```

**Response**
```json
{
  "candidates": [
    {
      "product_id": "prod_okayama_bladesmith_01",
      "name": "...",
      "brand": "...",
      "price_usd": 320,
      "composite_score": 0.87,
      "scores": {
        "attestation": 0.92,
        "outcome": 0.81,
        "niche_fit": 0.95,
        "value": 0.79
      },
      "attestation_count": 14,
      "rationale": "14 creators tested this product; weighted mean edge_retention score 9.1/10 ..."
    }
  ]
}
```

## `GET /attestations/{product_id}`

Return all creator attestations for a product. Used when an agent wants to inspect the underlying evidence before recommending.

**Response**
```json
{
  "product_id": "prod_okayama_bladesmith_01",
  "rubric_version": "chef_knife.v2",
  "attestations": [
    {
      "attestation_id": "att_0019",
      "creator_id": "cr_nakamura",
      "creator_reputation": 0.88,
      "testing_duration_days": 21,
      "methodology_notes": "...",
      "scores": {
        "edge_retention": 9.2,
        "carbon_content": 9.5,
        "balance": 8.4,
        "handle_ergonomics": 7.9
      },
      "signed_at": "2026-02-14T10:00:00Z"
    }
  ]
}
```

## `POST /outcomes`

Submit a post-purchase outcome signal. Closes the feedback loop.

**Request**
```json
{
  "recommendation_id": "rec_8f21",
  "product_id": "prod_okayama_bladesmith_01",
  "user_profile_hash": "...",
  "event": "kept" ,
  "satisfaction": 0.92,
  "reported_at": "2026-04-10T12:00:00Z"
}
```

`event` is one of: `kept`, `returned`, `repurchased`, `exchanged`.

**Response**
```json
{ "accepted": true, "affected_attestations": 14 }
```

The server updates creator reputation and outcome aggregates in memory.

## MCP server

Phase 1 of the roadmap ships an MCP server wrapping these endpoints so any agent developer can plug Drachma in without writing HTTP glue. The MCP tool surface mirrors the three endpoints above.

## Auth (production, not demo)

- Brands authenticate with API keys scoped to product submission.
- Creators authenticate with keys that sign attestations.
- Agent callers authenticate with keys scoped to `feed/query` and `outcomes`.

The demo skips all of this.
