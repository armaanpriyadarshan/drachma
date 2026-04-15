# Creator Network

Creators are the human signal source that makes Drachma work. This document describes who they are, what they produce, and how reputation is earned and lost.

## Creators are not influencers

The skill is evaluation, not entertainment. Creators don't need audiences. They receive products, test them against a standardized rubric, and publish structured attestations. The output is data, not content.

A creator's value is determined by the predictive accuracy of their attestations — whether the products they rated highly actually performed the way they said they would, for the users those products got matched to.

## Attestation workflow

1. Creator is verified and admitted to the network for one or more categories.
2. Brand ships the creator a product (or a set of products for comparative testing).
3. Creator tests the product against the current rubric version for that category.
4. Creator submits an attestation: per-attribute scores, testing duration, methodology notes.
5. The attestation is signed by the creator's verified identity and enters the feed.

## Rubrics

Each product category has a rubric: a schema of attributes creators must score. Rubrics are versioned — when a rubric is revised, old attestations remain valid against their version but are re-weighted as new attestations come in.

Example (chef's knives):
- `edge_retention` — measured against a standardized cut test over N days
- `carbon_content` — derived from material spec + hardness test
- `balance` — subjective but anchored to a defined reference point
- `handle_ergonomics` — scored against a fatigue protocol
- `out_of_box_sharpness` — single-trial cut test

The rubric defines both the attributes and the testing methodology. Creators are expected to follow it.

## Reputation

Per-category reputation is computed from two signals:

1. **Outcome alignment.** For every product a creator attested, compare their attribute-level scores against aggregate outcome data from users who purchased it. Creators whose predictions track outcomes gain reputation.
2. **Inter-creator agreement.** Where multiple creators test the same product, systematic divergence from the consensus (that is itself predictive) costs reputation.

Reputation weights a creator's attestation score in the ranking model. A high-reputation creator's scores count more; a low-reputation creator's count less.

## Why this is a moat

New entrants can't replicate:
- The trust relationships with verified creators
- The historical attestation corpus tied to outcome data
- The rubric versions, refined across thousands of tests

A copycat can re-implement the API in a weekend. They can't re-create the data.

## Out of scope for the demo

- Real identity verification
- Cryptographic attestation signing (the demo uses a fake `signed_at` + `creator_id` pair)
- Rubric versioning UI

Mock creators in the demo have hard-coded reputation scores that feed into ranking so the contrast scenarios render correctly.
