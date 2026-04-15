"""Drachma ranking model.

Four dimensions, combined multiplicatively so an unmeasured product doesn't win on price alone.
"""

from __future__ import annotations

from statistics import mean
from typing import Any

from .store import Store


# Tags used in mock outcomes. A real system would derive profile similarity from the preference vector.
PROFILE_TAG_WEIGHTS: dict[str, dict[str, float]] = {
    "edge_retention_heavy": {"edge_retention": 0.5, "steel_quality": 0.3},
    "carbon_steel_friendly": {"steel_quality": 0.4, "edge_retention": 0.3, "corrosion_resistance": -0.2},
    "balance_focused": {"balance": 0.5, "handle_ergonomics": 0.3},
    "low_maintenance": {"corrosion_resistance": 0.5, "out_of_box_sharpness": 0.2},
    "budget_conscious": {"out_of_box_sharpness": 0.3, "corrosion_resistance": 0.2},
}


def infer_profile_tag(weights: dict[str, float]) -> str:
    """Map a preference weight vector to the closest outcome tag for mock-data lookup."""
    best_tag = "balance_focused"
    best_score = float("-inf")
    for tag, tag_weights in PROFILE_TAG_WEIGHTS.items():
        score = sum(weights.get(k, 0.0) * v for k, v in tag_weights.items())
        if score > best_score:
            best_score, best_tag = score, tag
    return best_tag


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
        lo, hi = constraints["blade_length_mm"]
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


def attestation_score(product_id: str, weights: dict[str, float], store: Store) -> tuple[float, int]:
    """Reputation-weighted mean over creators, scored on the attributes the user cares about."""
    atts = store.attestations_for(product_id)
    if not atts:
        return 0.0, 0
    total_w, total_s = 0.0, 0.0
    for att in atts:
        creator = store.creator(att["creator_id"]) or {}
        rep = float(creator.get("reputation", 0.5))
        attr_sum, attr_w = 0.0, 0.0
        for attr, w in weights.items():
            if attr in att["scores"] and w > 0:
                attr_sum += att["scores"][attr] * w
                attr_w += w
        if attr_w == 0:
            continue
        per_attestation = attr_sum / attr_w / 10.0  # normalize 0-1
        total_s += per_attestation * rep
        total_w += rep
    if total_w == 0:
        return 0.0, len(atts)
    return total_s / total_w, len(atts)


def outcome_score(product_id: str, profile_tag: str, store: Store) -> float:
    """Satisfaction among similar users, with a prior to keep sparse data from dominating."""
    outs = store.outcomes_for(product_id)
    matched = [o for o in outs if o["user_profile_tag"] == profile_tag]
    pool = matched if len(matched) >= 2 else outs
    if not pool:
        return 0.5
    kept_bonus = mean(1.0 if o["event"] in ("kept", "repurchased") else 0.0 for o in pool)
    sat = mean(float(o["satisfaction"]) for o in pool)
    n = len(pool)
    prior_weight = 3.0
    return (sat * n + 0.5 * prior_weight) / (n + prior_weight) * (0.6 + 0.4 * kept_bonus)


def niche_fit_score(product_id: str, weights: dict[str, float], store: Store) -> float:
    """Cosine-ish similarity between the product's attestation-derived attribute vector and user weights."""
    atts = store.attestations_for(product_id)
    if not atts or not weights:
        return 0.0
    attr_means: dict[str, float] = {}
    for attr in weights:
        vals = [a["scores"].get(attr) for a in atts if attr in a["scores"]]
        if vals:
            attr_means[attr] = mean(vals) / 10.0
    if not attr_means:
        return 0.0
    weight_norm = sum(abs(w) for w in weights.values()) or 1.0
    return sum(attr_means.get(attr, 0.0) * w for attr, w in weights.items()) / weight_norm


def value_score(product: dict[str, Any], quality_proxy: float) -> float:
    """Quality per dollar, squashed so a $50 mediocre knife doesn't beat a $300 excellent one."""
    price = max(float(product.get("price_usd", 1)), 1.0)
    raw = quality_proxy / (price ** 0.4)
    # Normalize into ~[0, 1] using a reference: quality 0.9, price 200 → raw ≈ 0.108
    return min(raw / 0.12, 1.0)


def rank(
    preference_profile: dict[str, Any],
    store: Store,
    limit: int = 10,
) -> list[dict[str, Any]]:
    weights: dict[str, float] = preference_profile.get("weights", {})
    constraints = preference_profile.get("constraints")
    profile_tag = infer_profile_tag(weights)

    candidates = []
    for product in store.products:
        if not passes_constraints(product, constraints):
            continue

        att_s, att_n = attestation_score(product["product_id"], weights, store)
        out_s = outcome_score(product["product_id"], profile_tag, store)
        fit_s = niche_fit_score(product["product_id"], weights, store)
        val_s = value_score(product, quality_proxy=(att_s * 0.6 + fit_s * 0.4))

        # Multiplicative composite — a product with no attestations can't win.
        composite = (att_s ** 0.4) * (out_s ** 0.25) * (fit_s ** 0.25) * (val_s ** 0.1)

        candidates.append({
            "product_id": product["product_id"],
            "name": product["name"],
            "brand": product["brand"],
            "price_usd": product["price_usd"],
            "composite_score": round(composite, 4),
            "scores": {
                "attestation": round(att_s, 4),
                "outcome": round(out_s, 4),
                "niche_fit": round(fit_s, 4),
                "value": round(val_s, 4),
            },
            "attestation_count": att_n,
            "matched_profile_tag": profile_tag,
        })

    candidates.sort(key=lambda c: c["composite_score"], reverse=True)
    return candidates[:limit]
