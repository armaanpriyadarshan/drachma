# Architecture

Drachma is a recommendation layer between agents and commerce. This document describes the system's moving parts, data flow, and the ranking model.

## Actors

- **Brands.** Submit products with structured specs. Pay for distribution into the feed. Do not influence ranking.
- **Creators.** A verified network of product testers. Receive products, test against a category-specific rubric, publish signed attestations. Not influencers — evaluators.
- **Agents.** Consume the Drachma feed on behalf of end users. Query with a user preference profile, receive ranked candidates, submit outcome data post-purchase.
- **End users.** Never interact with Drachma directly. Their agents do.

## Data objects

### Product
Structured spec submitted by a brand. Category-typed. Includes price, dimensions, materials, and all category-specific attributes the rubric is defined over.

### Rubric
Category-specific schema defining the attributes creators score. Example for chef's knives: edge retention, carbon content, balance, handle ergonomics, out-of-box sharpness. Rubrics are versioned.

### Attestation
A creator's structured output after testing a product. Includes:
- Per-attribute scores (against the rubric)
- Testing duration
- Methodology notes
- Signature tying it to the creator's verified identity
- Rubric version

Attestations are not reviews. They are quality certificates intended for programmatic evaluation.

### Preference profile
A structured description of what a specific user cares about in a category. Produced by the user's agent, not by Drachma. Weights over rubric attributes plus hard constraints (budget, size, etc.).

### Outcome signal
Post-purchase event submitted by the agent: kept, returned, repurchased, satisfaction score. Tied back to the originating recommendation and the attestations that produced it.

## Data flow

```
Brand ──submit──▶ Product
                     │
Creator ──test──▶ Attestation ──▶ Feed
                                   │
                    Preference ──▶ Rank ──▶ Candidates ──▶ Agent ──▶ Purchase
                    Profile                                             │
                                                                        ▼
                              Creator reputation ◀── Outcome signal ────┘
```

## Ranking model

For a given (product, user preference profile) pair, Drachma scores across four dimensions:

1. **Creator attestation score.** Weighted aggregate of attestation scores on the attributes this user's profile weights highly. Weighted by creator reputation.
2. **Outcome data.** Repurchase rate, return rate, satisfaction — filtered to users with similar profiles. Higher similarity, higher weight.
3. **Niche fit.** Cosine-style similarity between the product's attribute vector (from attestations) and the user's preference weights.
4. **Value ratio.** Price relative to the composite quality signal.

The composite score is the product of these dimensions, not a sum — a product that's cheap but untested doesn't win on value alone.

## Creator reputation

Reputation is computed from the predictive accuracy of a creator's attestations: for every product a creator attested, does post-purchase outcome data for matched users line up with what the creator predicted? Creators whose attestations predict real outcomes gain weight. Creators whose attestations diverge lose weight. Reputation is per-category.

## The moat, restated

Every transaction through Drachma generates a longitudinal record: "this product was recommended to this type of user, and here's what happened." AI platforms see the recommendation but not the outcome. Brands see their own outcomes but not competitors'. Retailers see purchases but not cross-platform satisfaction. Drachma sits at the intersection.

## Out of scope for the demo

- Persistent storage (mock JSON only)
- Real cryptographic attestation signing
- Real creator identity verification
- Cross-category rubric generalization

See [`demo.md`](demo.md) for what the demo actually ships.
