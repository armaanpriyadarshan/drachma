# Drachma demo agent

Simulates a procurement agent using OpenAI function calling. Runs the same user request twice:

- **Scenario A** — traditional ranking: SEO authority, review volume, ad spend.
- **Scenario B** — Drachma feed: creator attestations, post-purchase outcomes, niche fit.

The contrast is the pitch. Scenario A typically recommends Victorinox / Wusthof / Shun. Scenario B recommends the Nakamura Aogami gyuto that the traditional pipeline never surfaces.

## Run

```bash
# 1. Start the backend (in another terminal)
cd ../backend && uvicorn app.main:app --port 8000

# 2. Agent
cd agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export OPENAI_API_KEY=sk-...
export OPENAI_MODEL=gpt-4.1   # optional, default gpt-4.1
python run.py                  # both scenarios
python run.py --scenario b     # just Drachma
```

`DRACHMA_URL` defaults to `http://localhost:8000` — override if running the backend elsewhere.

## What you'll see

Each scenario prints `[tool] <name>(<args>)` lines as the model calls tools, then a final recommendation ending with `FINAL: <product_id>`. Scenario A's tools return popularity-weighted results; Scenario B's tools hit the FastAPI backend.
