# Demo

The demo's job is to make the pitch visible: a simulated agent making a purchase decision twice — once with traditional ranking signals, once against the Drachma feed — and the Drachma version recommending a better product the other pipeline couldn't see.

## What the demo shows

Two scenarios, side by side:

**Scenario A — Traditional AI ranking.** The agent ranks by ad spend, SEO authority, and review volume. It recommends a generic big-brand product. Fine. Unremarkable. The kind of answer everyone gets today.

**Scenario B — Drachma feed.** The same agent, same user profile, queries `/feed/query` instead. It surfaces a niche product — the third-generation Okayama bladesmith with 47 reviews — because 14 creators tested it and the attestations match this user's preference profile. The recommendation comes with per-dimension scores and a readable rationale pulled from attestation data.

Then: the feedback loop. An outcome signal is submitted to `/outcomes`. The visualization shows creator reputations updating and the product's composite score shifting.

The contrast between A and B is the pitch.

## Technical implementation

All mock data. No database. Runs locally.

### Backend — FastAPI
- Serves the three endpoints documented in [`api.md`](api.md).
- Reads from a JSON file of mock products, creators, attestations, and outcome history.
- Holds outcome submissions in memory so the feedback loop is visible during a demo session.

### Agent harness — Python + Claude tool use
- A Python script uses Claude's API with tool use to simulate a procurement agent.
- Tools exposed to the model correspond 1:1 with the Drachma endpoints.
- The agent queries the feed, optionally pulls attestations for its top candidates, and produces a recommendation with a written rationale.
- The same script runs the "traditional ranking" scenario against a separate mock ranker that uses ad-spend / SEO / review-volume weights.

### Frontend — Next.js
- Visualizes the agent's decision process in real time.
- Panels: candidate sourcing, per-dimension scoring, final ranking, and the feedback loop.
- Streams tool-call events from the agent harness so the viewer sees the agent think.
- Renders scenarios A and B side by side.

> Note: this repo's Next.js version ships breaking changes vs. what's in model training data. See `AGENTS.md` and `node_modules/next/dist/docs/` before touching frontend code.

## Mock data shape

One category for the demo: chef's knives. Enough products and creators to make the contrast land:

- ~30 products, mix of global brands and niche makers
- ~20 creators with varied reputation scores
- ~150 attestations across the product set
- Pre-seeded outcome history so Scenario B has real numbers to rank on

## Running locally

The full runbook (ports, env, seeds, demo script) lives alongside the backend and frontend code once those ship. Target: `pnpm dev` for the Next.js app, `uvicorn` for the API, `python agent/run.py` for the agent harness.
