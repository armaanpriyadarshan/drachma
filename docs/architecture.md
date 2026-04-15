# Architecture

Drachma is a recommendation layer between agents and commerce. This document describes the system's actors, data flow, and the four-dimension ranking model.

## Actors

- **Brands.** Submit products with structured specs. Pay for distribution into the feed. Do not influence ranking.
- **Creators.** A verified network of product testers. Receive products, test against a category-specific rubric, publish signed attestations. Each creator declares specialties (e.g. `edge_retention`, `carbon_steel`, `balance`, `corrosion_resistance`) which determine what the creator's scores are credentialed to attest.
- **Agents.** Consume the Drachma feed on behalf of end users. Query with a user preference profile, receive ranked candidates, submit outcome data post-purchase.
- **End users.** Never interact with Drachma directly. Their agents do.

## Data objects

### Product
Structured spec submitted by a brand. Category-typed. Includes price, specs, and popularity metadata (review_volume, seo_authority) used only by the traditional-ranking baseline.

### Rubric
Category-specific schema defining the attributes creators score. Example for chef's knives: `edge_retention`, `steel_quality`, `balance`, `handle_ergonomics`, `out_of_box_sharpness`, `fit_and_finish`, `corrosion_resistance`. Rubrics are versioned.

### Attestation
A creator's structured output after testing a product. Includes per-attribute scores, testing duration, methodology notes, signature, and rubric version. Attestations are not reviews — they are quality certificates intended for programmatic evaluation.

### Preference profile
A structured description of what a specific user cares about in a category. Produced by the user's agent, not by Drachma. Three components:

- `weights` — user's weight over rubric attributes (must sum to ~1, zeros allowed).
- `constraints` — hard filters (budget, size, etc.).
- `composite_weights` — the user's weight over the four Drachma dimensions. Exposed so it can be displayed in the UI; nothing is hidden in the formula.

### Outcome signal
Post-purchase event submitted by the agent: `kept` | `returned` | `repurchased` | `exchanged`, plus a 0–1 satisfaction score and the submitter's preference vector. The preference vector is stored so future outcome-alignment scoring can similarity-weight it.

## Ranking model — the four dimensions

The composite score is an additive weighted sum of four dimensions, each measuring something structurally different. None is inferable from another.

### 1. Verified quality

Reputation-weighted mean of creator attestation scores, restricted to the attributes the user weighted above zero.

```
quality = Σ_att  reputation(att.creator) · weighted_mean(att.scores, user.weights)
         ───────────────────────────────────────────────────────────────────────
          Σ_att  reputation(att.creator)
```

Measures: "Do credible people say this product is good at the things this user cares about?"

### 2. Expert coverage

Reputation-weighted *proportion* of the tester pool whose declared specialty aligns with the user's weighted attributes, saturated at a sample-size reference.

```
specificity = Σ_att  reputation · match_fraction
             ──────────────────────────────────
              Σ_att  reputation

sample_factor = min(n_attestations / 3, 1)

coverage = specificity · sample_factor
```

`match_fraction` for each attestation = fraction of the user's preference weight that falls on attributes the creator is credentialed for.

Measures: "Has this product been tested by people who know this user's niche?" A mainstream product with ten home-cooking generalists scores low here. A niche product with four edge-retention specialists scores high. This is what makes niche products surface.

### 3. Outcome alignment

Bayesian mean satisfaction over past outcomes on this product, with each outcome weighted by cosine similarity between the buyer's preference vector and the current user's. Beta prior of 4 on satisfaction=0.5.

```
sim_i = cosine(outcome_i.preference_vector, user.weights)
weighted_sat = Σ  sat_i · sim_i
weighted_n   = Σ  sim_i
posterior    = (weighted_sat + 0.5 · 4) / (weighted_n + 4)
```

Event bonus/penalty: `repurchased` adds +0.05 to the effective satisfaction; `returned` subtracts 0.05. Keeps outcomes honest without letting self-reported numbers fully dominate.

Measures: "Did users similar to this one like the product?"

### 4. Value

Quality per dollar with explicit reference scaling. A product at quality 0.9 priced at $250 returns 1.0. Doubling quality halves the price requirement; halving price doubles the value.

```
value = clamp( (quality / 0.9) · ($250 / price), 0, 1 )
```

No arbitrary exponents. The reference point is documented.

### Composite

```
composite = w_quality · quality + w_coverage · coverage + w_outcome · outcome + w_value · value
```

`w_*` come from the user's `composite_weights`. Default is 0.40 / 0.20 / 0.25 / 0.15. The demo exposes three presets that tune these weights per archetype (edge-obsessed users weight quality heavily and value almost nothing; budget-first users weight value heavily).

## Creator reputation and the feedback loop

Reputation is dynamic. Every outcome submission runs an update:

1. For each attestation on the product, compute the creator's **implied satisfaction prediction** — the creator's attestation scores weighted by the user's preference vector.
2. Compare to observed satisfaction. If within tolerance, reputation inches up (by up to `REPUTATION_STEP · specialty_weight`). If outside tolerance, reputation moves down, proportional to error magnitude.
3. Under-prediction (creator said 0.6, reality was 0.9) is penalized half as hard as over-prediction — a conservative creator is better than an inflating one.
4. Specialist creators (whose specialties align with the user's weighted attributes) get larger reputation updates than generalists. A home-cooking creator's prediction barely moves rep; an edge-retention specialist's moves it meaningfully.

The endpoint returns both the new reputation deltas and the re-ranked candidates for the submitter's profile, so the caller can visualize the live impact.

## The moat, restated

Every transaction through Drachma generates a longitudinal record of (user preference vector, recommendation, attestation set, outcome). AI platforms see the recommendation but not the outcome. Brands see their own outcomes but not competitors'. Retailers see purchases but not cross-platform satisfaction. Drachma sits at the intersection, and the intersection compounds as (a) the reputation signal becomes more predictive over time and (b) the outcome corpus covers more preference-vector combinations.

## Demo scope

The demo runs a single category (chef's knives), 34 products, 28 creators, ~240 attestations, ~220 outcomes. Attestations and outcomes are generated deterministically by `backend/data/generate.py` from a seeded RNG — the generator is checked in so the data is reproducible and the noise model is inspectable. No product was hand-tuned to win.

Three preset user profiles each produce a different winning product under Drachma, while the traditional-ranking baseline returns the same popularity cluster regardless of profile. That contrast is the pitch.
