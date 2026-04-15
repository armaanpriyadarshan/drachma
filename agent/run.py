"""Drachma demo agent harness.

Runs a simulated procurement agent twice against the same user request:

  Scenario A — ranks via ad-spend / SEO / review-volume (traditional).
  Scenario B — queries the Drachma API (attestations + outcomes + niche fit).

Uses OpenAI function calling to let the model decide when to call tools and when to recommend.
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


# ---------------------------------------------------------------------------
# User request
# ---------------------------------------------------------------------------

USER_REQUEST = {
    "summary": (
        "I want a single chef's knife I'll use daily for serious home cooking. "
        "I maintain my own edges on a whetstone, I don't mind reactive carbon steel, "
        "and I care about edge retention and steel quality above everything else. "
        "Budget up to $400. Blade length between 200 and 240 mm."
    ),
    "preference_profile": {
        "weights": {
            "edge_retention": 0.45,
            "steel_quality": 0.30,
            "balance": 0.15,
            "handle_ergonomics": 0.10,
        },
        "constraints": {
            "max_price_usd": 400,
            "blade_length_mm": [200, 240],
        },
    },
}


# ---------------------------------------------------------------------------
# Scenario A: traditional ranking (local, no Drachma)
# ---------------------------------------------------------------------------

def _load_mock() -> dict[str, Any]:
    with MOCK_PATH.open() as f:
        return json.load(f)


def traditional_search(max_price_usd: float, blade_length_min: int, blade_length_max: int, limit: int = 5) -> dict[str, Any]:
    """Return top candidates ranked the way a typical AI-mediated search would: popularity + authority."""
    data = _load_mock()
    results = []
    for p in data["products"]:
        if p["price_usd"] > max_price_usd:
            continue
        bl = p["specs"].get("blade_length_mm", 0)
        if not (blade_length_min <= bl <= blade_length_max):
            continue
        # Traditional signal: SEO authority + review volume + ad spend.
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
    """Simulated aggregate review data — the only evidence a traditional AI has access to."""
    data = _load_mock()
    product = next((p for p in data["products"] if p["product_id"] == product_id), None)
    if not product:
        return {"error": f"unknown product_id {product_id}"}
    # Fake an aggregate that tracks popularity, not quality.
    stars = 3.8 + 0.6 * product["seo_authority"] + 0.2 * (product["ad_spend_tier"] / 5)
    return {
        "product_id": product_id,
        "average_stars": round(min(stars, 5.0), 2),
        "review_count": product["review_volume"],
        "sample_headlines": [
            "Great knife, recommend!",
            "Came fast, feels solid.",
            "My wife loves it.",
        ],
    }


TRADITIONAL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "traditional_search",
            "description": "Search products using mainstream popularity signals (SEO authority, review volume, ad spend).",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_price_usd": {"type": "number"},
                    "blade_length_min": {"type": "integer"},
                    "blade_length_max": {"type": "integer"},
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["max_price_usd", "blade_length_min", "blade_length_max"],
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
# Scenario B: Drachma
# ---------------------------------------------------------------------------

def _drachma_call(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    r = requests.request(method, f"{DRACHMA_URL}{path}", timeout=10, **kwargs)
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        return {"error": f"HTTP {r.status_code}: {detail}"}
    return r.json()


def drachma_feed_query(category: str, preference_profile: dict[str, Any], limit: int = 5) -> dict[str, Any]:
    return _drachma_call("POST", "/feed/query", json={"category": category, "preference_profile": preference_profile, "limit": limit})


def drachma_get_attestations(product_id: str) -> dict[str, Any]:
    return _drachma_call("GET", f"/attestations/{product_id}")


def drachma_submit_outcome(product_id: str, user_profile_tag: str, event: str, satisfaction: float) -> dict[str, Any]:
    return _drachma_call("POST", "/outcomes", json={
        "product_id": product_id,
        "user_profile_tag": user_profile_tag,
        "event": event,
        "satisfaction": satisfaction,
    })


DRACHMA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "drachma_feed_query",
            "description": (
                "Rank products in a category against a user preference profile using the Drachma signal: "
                "creator attestations, post-purchase outcomes, niche fit, and value. Use this first. "
                "Supported categories: 'chef_knife'."
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
                        },
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
            "description": "Fetch all verified creator attestations for a product — the underlying evidence for a candidate.",
            "parameters": {
                "type": "object",
                "properties": {"product_id": {"type": "string"}},
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "drachma_submit_outcome",
            "description": "Report a post-purchase outcome so future rankings incorporate this signal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string"},
                    "user_profile_tag": {"type": "string"},
                    "event": {"type": "string", "enum": ["kept", "returned", "repurchased", "exchanged"]},
                    "satisfaction": {"type": "number"},
                },
                "required": ["product_id", "user_profile_tag", "event", "satisfaction"],
            },
        },
    },
]


TOOL_IMPLS = {
    "traditional_search": traditional_search,
    "get_product_reviews_summary": get_product_reviews_summary,
    "drachma_feed_query": drachma_feed_query,
    "drachma_get_attestations": drachma_get_attestations,
    "drachma_submit_outcome": drachma_submit_outcome,
}


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_TRADITIONAL = (
    "You are a procurement agent making a purchase decision on behalf of your user. "
    "You have access only to traditional product search (popularity, SEO, review volume, ad spend). "
    "Use the tools to explore candidates, then recommend exactly one product. "
    "Explain your reasoning in under 120 words. End with a line: FINAL: <product_id>."
)

SYSTEM_PROMPT_DRACHMA = (
    "You are a procurement agent making a purchase decision on behalf of your user. "
    "You have access to the Drachma recommendation layer: creator attestations, post-purchase outcome data, "
    "and niche-fit scoring. Always start by calling drachma_feed_query with category='chef_knife' and the "
    "user's full preference_profile (weights + constraints). "
    "If useful, call drachma_get_attestations on your top 1-2 candidates to inspect the evidence. "
    "Recommend exactly one product. Explain your reasoning in under 120 words, citing specific attestation "
    "signals. End with a line: FINAL: <product_id>."
)


def run_agent(client: OpenAI, system_prompt: str, tools: list[dict], user_request: dict, label: str) -> str:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_request)},
    ]
    print(f"\n{'=' * 72}\n  {label}\n{'=' * 72}")
    for step in range(8):
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto",
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
    print("[warn] agent exceeded step budget")
    return ""


def _short(args: dict[str, Any]) -> str:
    s = json.dumps(args)
    return s if len(s) < 160 else s[:157] + "..."


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=["a", "b", "both"], default="both")
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        print("error: set OPENAI_API_KEY", file=sys.stderr)
        return 1

    client = OpenAI()

    if args.scenario in ("a", "both"):
        run_agent(client, SYSTEM_PROMPT_TRADITIONAL, TRADITIONAL_TOOLS, USER_REQUEST, "SCENARIO A  —  traditional ranking")
    if args.scenario in ("b", "both"):
        run_agent(client, SYSTEM_PROMPT_DRACHMA, DRACHMA_TOOLS, USER_REQUEST, "SCENARIO B  —  Drachma feed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
