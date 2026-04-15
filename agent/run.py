"""Drachma CLI agent harness.

Two scenarios against the same user request:

  A (traditional)  ad spend / SEO / review volume
  B (drachma)      the Drachma feed

Uses OpenAI function calling. Duplicates the preset profiles from the Next app
to stay self-contained.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import requests
from openai import OpenAI


DRACHMA_URL = os.environ.get("DRACHMA_URL", "http://localhost:8000")
MOCK_PATH = Path(__file__).resolve().parent.parent / "backend" / "data" / "mock.json"
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1")


PROFILES: dict[str, dict[str, Any]] = {
    "A": {
        "label": "Edge-obsessed carbon enthusiast",
        "summary": (
            "Daily serious home cooking. I maintain my own edges on a whetstone and don't "
            "mind reactive carbon steel. Edge retention and steel quality matter more than "
            "anything else, and I'll pay for the right knife."
        ),
        "preference_profile": {
            "weights": {"edge_retention": 0.45, "steel_quality": 0.30, "balance": 0.15, "handle_ergonomics": 0.10},
            "constraints": {"max_price_usd": 400, "blade_length_mm": [200, 240]},
            "composite_weights": {"quality": 0.50, "coverage": 0.25, "outcome": 0.20, "value": 0.05},
        },
    },
    "B": {
        "label": "Precision workhorse, low maintenance",
        "summary": (
            "A knife that moves through prep cleanly and stays that way without babying it. "
            "Balance, handle ergonomics, fit-and-finish, and corrosion resistance. Willing to "
            "spend for the right geometry."
        ),
        "preference_profile": {
            "weights": {"balance": 0.35, "handle_ergonomics": 0.30, "corrosion_resistance": 0.20, "fit_and_finish": 0.15},
            "constraints": {"max_price_usd": 400},
            "composite_weights": {"quality": 0.35, "coverage": 0.25, "outcome": 0.30, "value": 0.10},
        },
    },
    "C": {
        "label": "First serious knife, budget-first",
        "summary": (
            "First real chef's knife. Sharp out of the box, comfortable to hold, stainless so "
            "it doesn't need fussing over. Budget under $180. I'll upgrade later."
        ),
        "preference_profile": {
            "weights": {"out_of_box_sharpness": 0.35, "handle_ergonomics": 0.25, "corrosion_resistance": 0.20, "balance": 0.20},
            "constraints": {"max_price_usd": 180},
            "composite_weights": {"quality": 0.25, "coverage": 0.15, "outcome": 0.25, "value": 0.35},
        },
    },
}


# ---------------------------------------------------------------------------
# Scenario A tools
# ---------------------------------------------------------------------------

def _load_mock() -> dict[str, Any]:
    with MOCK_PATH.open() as f:
        return json.load(f)


def traditional_search(max_price_usd: float, blade_length_min: int = 0, blade_length_max: int = 10_000, limit: int = 5) -> dict[str, Any]:
    data = _load_mock()
    results = []
    for p in data["products"]:
        if p["price_usd"] > max_price_usd:
            continue
        bl = p["specs"].get("blade_length_mm", 0)
        if not (blade_length_min <= bl <= blade_length_max):
            continue
        score = (
            0.40 * p["seo_authority"]
            + 0.40 * min(p["review_volume"] / 15000, 1.0)
            + 0.20 * (p["ad_spend_tier"] / 5)
        )
        results.append({
            "product_id": p["product_id"],
            "name": p["name"],
            "brand": p["brand"],
            "price_usd": p["price_usd"],
            "review_volume": p["review_volume"],
            "seo_authority": p["seo_authority"],
            "ad_spend_tier": p["ad_spend_tier"],
            "popularity_score": round(score, 4),
        })
    results.sort(key=lambda r: r["popularity_score"], reverse=True)
    return {"candidates": results[:limit]}


def get_product_reviews_summary(product_id: str) -> dict[str, Any]:
    data = _load_mock()
    product = next((p for p in data["products"] if p["product_id"] == product_id), None)
    if not product:
        return {"error": f"unknown product_id {product_id}"}
    popularity = 0.5 * product["seo_authority"] + 0.5 * min(product["review_volume"] / 15000, 1.0)
    noise = (hash(product_id) % 1000 / 1000 - 0.5) * 0.7
    stars = max(3.4, min(4.9, 3.9 + 0.5 * popularity + noise))
    return {
        "product_id": product_id,
        "average_stars": round(stars, 2),
        "review_count": product["review_volume"],
        "sample_headlines": [
            "Great knife, recommend!",
            "Came fast, feels solid.",
            "Sharper than expected.",
        ],
    }


TRADITIONAL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "traditional_search",
            "description": "Search products using mainstream popularity signals (SEO, reviews, ad spend).",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_price_usd": {"type": "number"},
                    "blade_length_min": {"type": "integer"},
                    "blade_length_max": {"type": "integer"},
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["max_price_usd"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_reviews_summary",
            "description": "Aggregate star rating and review count for a product.",
            "parameters": {
                "type": "object",
                "properties": {"product_id": {"type": "string"}},
                "required": ["product_id"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Scenario B tools
# ---------------------------------------------------------------------------

def _drachma(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    r = requests.request(method, f"{DRACHMA_URL}{path}", timeout=15, **kwargs)
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        return {"error": f"HTTP {r.status_code}: {detail}"}
    return r.json()


def drachma_feed_query(category: str, preference_profile: dict[str, Any], limit: int = 5) -> dict[str, Any]:
    return _drachma("POST", "/feed/query", json={"category": category, "preference_profile": preference_profile, "limit": limit})


def drachma_get_attestations(product_id: str) -> dict[str, Any]:
    return _drachma("GET", f"/attestations/{product_id}")


DRACHMA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "drachma_feed_query",
            "description": (
                "Rank products against a user preference profile using Drachma's four-dimension "
                "composite: verified quality, expert coverage, outcome alignment, value. Pass "
                "the full preference_profile including weights, constraints, and composite_weights. "
                "Supported category: 'chef_knife'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "preference_profile": {
                        "type": "object",
                        "properties": {
                            "weights": {"type": "object", "additionalProperties": {"type": "number"}},
                            "constraints": {"type": "object"},
                            "composite_weights": {"type": "object", "additionalProperties": {"type": "number"}},
                        },
                        "required": ["weights"],
                    },
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["category", "preference_profile"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "drachma_get_attestations",
            "description": "Fetch all verified creator attestations for a product (includes specialties and reputations).",
            "parameters": {
                "type": "object",
                "properties": {"product_id": {"type": "string"}},
                "required": ["product_id"],
            },
        },
    },
]


TOOL_IMPLS = {
    "traditional_search": traditional_search,
    "get_product_reviews_summary": get_product_reviews_summary,
    "drachma_feed_query": drachma_feed_query,
    "drachma_get_attestations": drachma_get_attestations,
}


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_TRADITIONAL = (
    "You are a procurement agent. You have access only to traditional product search "
    "(popularity, SEO, review volume, ad spend). Explore candidates and recommend exactly "
    "one product in under 100 words. End with a line: FINAL: <product_id>."
)

SYSTEM_PROMPT_DRACHMA = (
    "You are a procurement agent. You have access to the Drachma recommendation layer: "
    "creator attestations, outcome alignment, niche-fit scoring. Always start with "
    "drachma_feed_query — pass the user's full preference_profile including weights, "
    "constraints, and composite_weights. If useful, call drachma_get_attestations on your "
    "top 1-2 candidates. Recommend exactly one product in under 100 words, citing specialist "
    "creators and per-dimension scores. End with a line: FINAL: <product_id>."
)


def run_agent(client: OpenAI, system_prompt: str, tools: list, user_request: dict, label: str) -> str:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_request)},
    ]
    print(f"\n{'=' * 72}\n  {label}\n{'=' * 72}")
    for step in range(8):
        resp = client.chat.completions.create(
            model=MODEL, messages=messages, tools=tools, tool_choice="auto",
        )
        msg = resp.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))
        if msg.tool_calls:
            for call in msg.tool_calls:
                name = call.function.name
                args = json.loads(call.function.arguments or "{}")
                print(f"[tool] {name}({_short(args)})")
                try:
                    result = TOOL_IMPLS[name](**args)
                except Exception as e:
                    result = {"error": str(e)}
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result)[:6000],
                })
            continue
        content = msg.content or ""
        print(f"\n[recommendation]\n{content}\n")
        return content
    print("[warn] step budget exhausted")
    return ""


def _short(args: dict[str, Any]) -> str:
    s = json.dumps(args)
    return s if len(s) < 160 else s[:157] + "..."


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=["A", "B", "C"], default="A")
    parser.add_argument("--scenario", choices=["a", "b", "both"], default="both")
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        print("error: set OPENAI_API_KEY", file=sys.stderr)
        return 1

    profile = PROFILES[args.profile]
    user_request = {"summary": profile["summary"], "preference_profile": profile["preference_profile"]}
    print(f"profile {args.profile}: {profile['label']}")

    client = OpenAI()
    if args.scenario in ("a", "both"):
        run_agent(client, SYSTEM_PROMPT_TRADITIONAL, TRADITIONAL_TOOLS, user_request, "SCENARIO A  —  traditional ranking")
    if args.scenario in ("b", "both"):
        run_agent(client, SYSTEM_PROMPT_DRACHMA, DRACHMA_TOOLS, user_request, "SCENARIO B  —  Drachma feed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
