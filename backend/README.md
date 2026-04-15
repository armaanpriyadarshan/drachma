# Drachma backend (demo)

FastAPI service backed by `data/mock.json`. Three endpoints per [`../docs/api.md`](../docs/api.md).

## Run

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Smoke test

```bash
# Health / data summary
curl -s localhost:8000/health | jq

# Edge-retention-focused profile — hero product should be at or near the top
curl -s -X POST localhost:8000/feed/query \
  -H 'content-type: application/json' \
  -d '{
    "category": "chef_knife",
    "preference_profile": {
      "weights": {
        "edge_retention": 0.45,
        "steel_quality": 0.30,
        "balance": 0.15,
        "handle_ergonomics": 0.10
      },
      "constraints": { "max_price_usd": 400, "blade_length_mm": [200, 240] }
    },
    "limit": 5
  }' | jq

# Inspect the evidence
curl -s localhost:8000/attestations/prod_nakamura_aogami_gyuto_210 | jq

# Close the loop
curl -s -X POST localhost:8000/outcomes \
  -H 'content-type: application/json' \
  -d '{
    "product_id": "prod_nakamura_aogami_gyuto_210",
    "user_profile_tag": "edge_retention_heavy",
    "event": "kept",
    "satisfaction": 0.95
  }' | jq
```

## Mock data at a glance

- 1 category: chef's knives, 7-attribute rubric (`chef_knife.v2`)
- 18 products: niche Japanese makers, global incumbents, mid-tier established, DTC startups
- 16 creators with per-category reputation
- 88 attestations
- 48 pre-seeded outcome signals tagged by user-profile archetype

The data is tuned so that a profile weighting `edge_retention` + `steel_quality` surfaces `prod_nakamura_aogami_gyuto_210` (the Okayama hero) above Wusthof/Henckels/Shun, while a `low_maintenance` + `budget_conscious` profile surfaces Victorinox or MAC — which is the Scenario A/B contrast the demo is built around.
