"""Drachma ranking model — principled four-dimension composite.

Each of the four dimensions measures something structurally different from the
others. None can be inferred from another. The composite is an additive weighted
sum, so changing the component weights changes the final score linearly — no
hidden exponents, no circular normalizations.

Dimensions:

  1. VERIFIED QUALITY        reputation-weighted mean of creator scores, filtered
                             to the attributes the user actually cares about.
                             Measures: "do credible people say this product is
                             good at the things this user cares about?"

  2. EXPERT COVERAGE         count of attestations from creators whose declared
                             specialty *aligns with the user's weighted attrs*,
                             weighted by those creators' reputation.
                             Measures: "has this product been tested by people
                             who know this user's niche?" This is the new
                             "niche fit" and it is not the same as quality — a
                             mainstream product tested by many home cooks scores
                             high on quality but low on coverage.

  3. OUTCOME ALIGNMENT       Bayesian mean satisfaction over past outcomes,
                             where each outcome is weighted by cosine similarity
                             between that buyer's preference vector and the
                             current user's. Beta prior of 4 on sat=0.5 keeps
                             sparse data stable but allows 5+ relevant outcomes
                             to clearly move the score.
                             Measures: "did users like this one like the
                             product?"

  4. VALUE                   quality per dollar, normalized to a fixed reference
                             (quality=0.9, price=$250 → 1.0). Explicit, not
                             circular.

Composite: additive weighted sum. Defaults: 0.40 quality / 0.20 coverage /
0.25 outcome / 0.15 value. The dimensions' weights are user-tunable and
displayed in the UI — there is nothing arbitrary hidden inside the formula.
"""

from __future__ import annotations

import math
from statistics import mean
from typing import Any

from .store import Store


# ---------------------------------------------------------------------------
# Specialty / attribute alignment
# ---------------------------------------------------------------------------

# Maps a creator specialty tag to rubric attributes it credentials the creator
# for. Mirrors the generator's bias map but used here only to decide whether
# a creator counts as a "specialist" for a user's weighted attributes.

SPECIALTY_ATTRS: dict[str, set[str]] = {
    "edge_retention":       {"edge_retention", "out_of_box_sharpness"},
    "steel_quality":        {"steel_quality", "edge_retention"},
    "carbon_steel":         {"edge_retention", "steel_quality"},
    "stainless":            {"corrosion_resistance"},
    "german_steel":         {"corrosion_resistance", "fit_and_finish"},
    "japanese_knives":      {"edge_retention", "steel_quality", "fit_and_finish"},
    "sakai_forged":         {"fit_and_finish", "balance"},
    "corrosion_resistance": {"corrosion_resistance"},
    "fit_and_finish":       {"fit_and_finish"},
    "out_of_box_sharpness": {"out_of_box_sharpness"},
    "balance":              {"balance", "handle_ergonomics"},
    "handle_ergonomics":    {"handle_ergonomics", "balance"},
    "knife_geometry":       {"balance", "edge_retention", "out_of_box_sharpness"},
    "metallurgy":           {"steel_quality", "edge_retention"},
    "pro_kitchen":          {"handle_ergonomics", "edge_retention"},
    "restaurant_prep":      {"handle_ergonomics", "balance"},
    "butchery":             {"edge_retention", "handle_ergonomics"},
    "french_cuisine":       {"balance", "handle_ergonomics"},
    "traditional":          {"fit_and_finish"},
    "home_cooking":         set(),
    "budget_gear":          {"out_of_box_sharpness", "corrosion_resistance"},
}


def creator_specialty_attrs(creator: dict[str, Any]) -> set[str]:
    """Union of attributes this creator is credentialed on."""
    attrs: set[str] = set()
    for s in creator.get("specialties", []):
        attrs |= SPECIALTY_ATTRS.get(s, set())
    return attrs


# ---------------------------------------------------------------------------
# Constraint filtering
# ---------------------------------------------------------------------------

def passes_constraints(product: dict[str, Any], constraints: dict[str, Any] | None) -> bool:
    if not constraints:
        return True
    specs = product.get("specs", {})
    price = product.get("price_usd", 0)
    if "max_price_usd" in constraints and price > constraints["max_price_usd"]:
        return False
    if "min_price_usd" in constraints and price < constraints["min_price_usd"]:
        return False
    if "blade_length_mm" in constraints:
        rng = constraints["blade_length_mm"]
        lo, hi = rng[0], rng[1]
        if not (lo <= specs.get("blade_length_mm", 0) <= hi):
            return False
    if "min_hrc" in constraints and specs.get("hrc", 0) < constraints["min_hrc"]:
        return False
    if "profile" in constraints:
        allowed = constraints["profile"]
        allowed = [allowed] if isinstance(allowed, str) else allowed
        if specs.get("profile") not in allowed:
            return False
    return True


# ---------------------------------------------------------------------------
# Dimension 1: Verified quality
# ---------------------------------------------------------------------------

def verified_quality(product_id: str, weights: dict[str, float], store: Store) -> tuple[float, int]:
    """
    Reputation-weighted mean of creator scores on the user's weighted attributes.

    Returns (quality_0_to_1, attestation_count).
    """
    atts = store.attestations_for(product_id)
    if not atts:
        return 0.0, 0
    total_rep, total_score = 0.0, 0.0
    for att in atts:
        creator = store.creator(att["creator_id"]) or {}
        rep = float(store.current_reputation(creator.get("creator_id", "")))
        if rep <= 0:
            continue
        attr_sum, attr_w = 0.0, 0.0
        for attr, w in weights.items():
            if w <= 0:
                continue
            score = att["scores"].get(attr)
            if score is None:
                continue
            attr_sum += score * w
            attr_w += w
        if attr_w == 0:
            continue
        per_att = (attr_sum / attr_w) / 10.0
        total_score += per_att * rep
        total_rep += rep
    if total_rep == 0:
        return 0.0, len(atts)
    return total_score / total_rep, len(atts)


# ---------------------------------------------------------------------------
# Dimension 2: Expert coverage
# ---------------------------------------------------------------------------

SATURATION_N = 3.0   # sample-size saturation point


def expert_coverage(product_id: str, weights: dict[str, float], store: Store) -> float:
    """
    Reputation-weighted *proportion* of the tester pool whose declared specialty
    aligns with the user's weighted attributes, saturated once the sample size
    reaches SATURATION_N.

    This measures specificity of coverage, not raw count: a product tested by
    four edge-retention specialists scores higher than one tested by ten
    home-cooking generalists, even though the latter has more attestations.

    Unspecialized creators (e.g. "home_cooking") count as zero-match but still
    contribute reputation to the denominator, so they dilute specificity.
    """
    atts = store.attestations_for(product_id)
    if not atts:
        return 0.0
    user_mass = sum(w for w in weights.values() if w > 0) or 1.0

    weighted_match = 0.0
    weighted_rep = 0.0
    for att in atts:
        creator = store.creator(att["creator_id"]) or {}
        rep = float(store.current_reputation(creator.get("creator_id", "")))
        if rep <= 0:
            continue
        spec_attrs = creator_specialty_attrs(creator)
        match_mass = sum(w for a, w in weights.items() if a in spec_attrs and w > 0) if spec_attrs else 0.0
        match_fraction = match_mass / user_mass
        weighted_match += rep * match_fraction
        weighted_rep += rep

    if weighted_rep == 0:
        return 0.0
    specificity = weighted_match / weighted_rep
    sample_factor = min(len(atts) / SATURATION_N, 1.0)
    return specificity * sample_factor


# ---------------------------------------------------------------------------
# Dimension 3: Outcome alignment
# ---------------------------------------------------------------------------

PRIOR_WEIGHT = 4.0
PRIOR_SATISFACTION = 0.5


def cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    keys = set(a) | set(b)
    dot = sum(a.get(k, 0) * b.get(k, 0) for k in keys)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def outcome_alignment(product_id: str, weights: dict[str, float], store: Store) -> tuple[float, float]:
    """
    Bayesian satisfaction weighted by preference-vector similarity.

    Returns (aligned_mean_0_to_1, effective_sample_size).
    """
    outs = store.outcomes_for(product_id)
    weighted_sat = 0.0
    weighted_n = 0.0
    for o in outs:
        prefs = o.get("preference_vector") or {}
        sim = cosine_similarity(weights, prefs)
        if sim <= 0:
            continue
        sat = float(o.get("satisfaction", 0.5))
        # Small bonus for repurchase, small penalty for return — empirical
        # events carry a bit more weight than self-reported satisfaction alone.
        event = o.get("event")
        if event == "repurchased":
            sat = min(1.0, sat + 0.05)
        elif event == "returned":
            sat = max(0.0, sat - 0.05)
        weighted_sat += sat * sim
        weighted_n += sim
    n_eff = weighted_n
    posterior = (weighted_sat + PRIOR_SATISFACTION * PRIOR_WEIGHT) / (n_eff + PRIOR_WEIGHT)
    return posterior, n_eff


# ---------------------------------------------------------------------------
# Dimension 4: Value
# ---------------------------------------------------------------------------

REF_QUALITY = 0.9
REF_PRICE = 250.0


def value_score(price_usd: float, quality_0_1: float) -> float:
    """
    Quality per dollar with explicit reference scaling.

    A product with quality=0.9 priced at $250 returns 1.0. A product with the
    same quality at $125 returns ~2 → clipped to 1.0. A product with quality=0.6
    at $250 returns ~0.67.
    """
    if price_usd <= 0:
        return 0.0
    raw = (quality_0_1 / REF_QUALITY) * (REF_PRICE / price_usd)
    return max(0.0, min(raw, 1.0))


# ---------------------------------------------------------------------------
# Composite + rank
# ---------------------------------------------------------------------------

DEFAULT_COMPOSITE_WEIGHTS = {
    "quality": 0.40,
    "coverage": 0.20,
    "outcome": 0.25,
    "value": 0.15,
}


def composite_score(
    quality: float, coverage: float, outcome: float, value: float,
    w: dict[str, float] = DEFAULT_COMPOSITE_WEIGHTS,
) -> float:
    total_w = sum(w.values()) or 1.0
    return (
        quality * w["quality"]
        + coverage * w["coverage"]
        + outcome * w["outcome"]
        + value * w["value"]
    ) / total_w


def rank(
    preference_profile: dict[str, Any],
    store: Store,
    limit: int = 10,
) -> list[dict[str, Any]]:
    weights: dict[str, float] = preference_profile.get("weights", {})
    constraints = preference_profile.get("constraints")
    composite_w = preference_profile.get("composite_weights") or DEFAULT_COMPOSITE_WEIGHTS

    candidates = []
    for product in store.products:
        if not passes_constraints(product, constraints):
            continue

        quality, n_atts = verified_quality(product["product_id"], weights, store)
        coverage = expert_coverage(product["product_id"], weights, store)
        outcome, n_eff = outcome_alignment(product["product_id"], weights, store)
        value = value_score(product["price_usd"], quality)

        composite = composite_score(quality, coverage, outcome, value, composite_w)

        candidates.append({
            "product_id": product["product_id"],
            "name": product["name"],
            "brand": product["brand"],
            "price_usd": product["price_usd"],
            "composite_score": round(composite, 4),
            "scores": {
                "quality": round(quality, 4),
                "coverage": round(coverage, 4),
                "outcome": round(outcome, 4),
                "value": round(value, 4),
            },
            "attestation_count": n_atts,
            "outcome_sample_size": round(n_eff, 2),
        })

    candidates.sort(key=lambda c: c["composite_score"], reverse=True)
    return candidates[:limit]


# ---------------------------------------------------------------------------
# Reputation update (called from /outcomes)
# ---------------------------------------------------------------------------

REPUTATION_STEP = 0.04       # max single-outcome movement
TOLERANCE = 0.15             # how close a prediction must be to count as correct


def update_reputations_for_outcome(
    store: Store,
    product_id: str,
    preference_vector: dict[str, float],
    observed_satisfaction: float,
) -> list[dict[str, Any]]:
    """
    For each attestation on this product, measure how well the creator's scores
    predicted the observed satisfaction for this preference vector, and nudge
    reputation accordingly.

    Returns a list of per-creator deltas for the UI to display.
    """
    atts = store.attestations_for(product_id)
    if not atts:
        return []

    deltas: list[dict[str, Any]] = []
    user_mass = sum(w for w in preference_vector.values() if w > 0) or 1.0

    for att in atts:
        creator = store.creator(att["creator_id"]) or {}
        creator_id = creator.get("creator_id")
        if not creator_id:
            continue

        # Compute the creator's implied-satisfaction prediction from their scores
        # weighted by the user's preferences.
        attr_sum, attr_w = 0.0, 0.0
        for attr, w in preference_vector.items():
            if w <= 0:
                continue
            score = att["scores"].get(attr)
            if score is None:
                continue
            attr_sum += score * w
            attr_w += w
        if attr_w == 0:
            continue
        predicted = (attr_sum / attr_w) / 10.0

        # How far off? Close means reputation up; far means down.
        err = predicted - observed_satisfaction
        # Creator weight in this update: how much of the user's preference mass
        # they're credentialed for (via specialties). A home-cooking generalist's
        # prediction doesn't update rep much; a specialist's does.
        spec_attrs = creator_specialty_attrs(creator)
        specialty_weight = (
            sum(w for a, w in preference_vector.items() if a in spec_attrs and w > 0)
            / user_mass
        ) if spec_attrs else 0.25  # non-specialists still get a small update

        # Direction: err>0 means creator was optimistic → reputation down.
        # err<0 means creator was pessimistic but product did well → reputation up
        # (though we weight under-prediction less than over-prediction: a conservative
        # creator is less penalized than an inflating one).
        if abs(err) <= TOLERANCE:
            delta = +REPUTATION_STEP * specialty_weight
        else:
            direction = -1.0 if err > 0 else -0.5  # under-prediction less bad
            magnitude = min(abs(err) - TOLERANCE, 0.4) / 0.4   # 0..1
            delta = REPUTATION_STEP * specialty_weight * direction * magnitude

        new_rep = store.nudge_reputation(creator_id, delta)
        if abs(delta) < 0.003:
            continue
        deltas.append({
            "creator_id": creator_id,
            "creator_name": creator.get("name"),
            "attestation_id": att["attestation_id"],
            "predicted": round(predicted, 3),
            "observed": round(observed_satisfaction, 3),
            "delta": round(delta, 4),
            "new_reputation": round(new_rep, 4),
        })
    # Rank by absolute delta so the most material changes show up first
    deltas.sort(key=lambda d: abs(d["delta"]), reverse=True)
    return deltas
