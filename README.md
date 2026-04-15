# Drachma

**Attention economics for agents. Powered by people, not budgets.**

Drachma is a recommendation layer that AI agents query when making purchase decisions on behalf of users. Instead of ranking products by ad spend, SEO, and review volume, Drachma ranks by empirical product quality — verified by a network of human testers generating structured, machine-readable quality attestations.

## The problem

The $600B+ advertising industry is built on capturing human attention. As AI agents increasingly mediate purchasing decisions, that model breaks. Agents don't watch ads, don't respond to emotional branding, don't scroll feeds. In an agent-mediated world, the products that win are the ones with the best structured data and the biggest marketing budgets — not the best products.

This is the same problem Google had in 2001, except now the searcher isn't a human who can scroll past bad results. It's an agent that returns one answer.

## The thesis

The ranking signal for agent-mediated commerce should be empirical product quality verified by humans with skin in the game, not marketing spend. Drachma provides:

1. A structured output format agents can consume.
2. A ranking algorithm that rewards genuine product-market fit over brand dominance.
3. A verified creator network that generates signed quality attestations.
4. A closed feedback loop from post-purchase outcome data.

## How it works

- **Brands** submit products with structured specs to the Drachma feed. They pay for distribution into the signal network — not for placement or ranking.
- **Creators** from a verified network receive products and test them against a standardized, category-specific attribute rubric. They publish signed attestations: per-attribute scores, testing duration, methodology notes.
- **Agents** query the Drachma API with a user's preference profile. The API returns candidates ranked across four dimensions:
  - Creator attestation score
  - Post-purchase outcome data (repurchase, return, satisfaction among similar users)
  - Niche fit to the user's preference model
  - Value ratio (price vs. quality signal)
- **Outcome data** flows back from the user's agent post-purchase, validating or degrading creator signals and refining matching for similar user profiles.

## Why niche products win

Traditional AI recommendation surfaces optimize for popularity proxies that systematically favor incumbents. Drachma replaces proxies with direct measurement. A knife made by a third-generation bladesmith in Okayama with 47 reviews and zero ad spend can outrank a global brand with 12,000 reviews, because 14 creators tested both and the data shows the small maker is empirically better for users who care about edge retention and carbon steel.

A product 200 people love beats a product 10,000 people find mediocre — the audience isn't humans scrolling a feed, it's agents making procurement decisions.

## Moat

1. **Outcome data.** Drachma sits at the intersection of recommendations, brand performance, and post-purchase satisfaction. No single party — AI platforms, brands, retailers — sees the full longitudinal record. The more niche the match, the less replicable the data.
2. **The creator network.** A curated, reputation-scored network of verified testers is both a data asset and a network effect. Trust relationships and the historical attestation corpus compound.

## Revenue model

Brands pay to be in the feed. Not for placement, not for ranking — for distribution into the signal network. The fee is access to evaluation, not influence over the algorithm.

## Docs

- [`docs/architecture.md`](docs/architecture.md) — system design and ranking model
- [`docs/api.md`](docs/api.md) — Drachma API reference
- [`docs/creators.md`](docs/creators.md) — creator network, attestations, reputation
- [`docs/demo.md`](docs/demo.md) — demo scope and technical implementation
- [`docs/gtm.md`](docs/gtm.md) — go-to-market phases

## Repository

This repo contains the Drachma demo: a FastAPI backend, a Python agent harness built on Claude tool use, and a Next.js frontend that visualizes the agent's decision process in real time. All mock data, no database, runs locally. See [`docs/demo.md`](docs/demo.md).
