/**
 * Tool implementations shared between the two scenarios.
 *
 * Scenario A tools: traditional popularity-based search (local JSON, SEO / reviews / ad spend).
 * Scenario B tools: HTTP calls to the Drachma FastAPI backend.
 */

import fs from "node:fs";
import path from "node:path";

const DRACHMA_URL = process.env.DRACHMA_URL ?? "http://localhost:8000";
const MOCK_PATH = path.join(process.cwd(), "backend", "data", "mock.json");

type AnyRecord = Record<string, unknown>;

let cachedMock: AnyRecord | null = null;
function loadMock(): AnyRecord {
  if (!cachedMock) {
    cachedMock = JSON.parse(fs.readFileSync(MOCK_PATH, "utf8"));
  }
  return cachedMock!;
}

// ---------------------------------------------------------------------------
// Scenario A — traditional ranking
// ---------------------------------------------------------------------------

export async function traditionalSearch(args: {
  max_price_usd: number;
  blade_length_min: number;
  blade_length_max: number;
  limit?: number;
}): Promise<AnyRecord> {
  const data = loadMock();
  const products = (data.products as AnyRecord[]).filter((p) => {
    const bl = (p.specs as AnyRecord).blade_length_mm as number;
    return (
      (p.price_usd as number) <= args.max_price_usd &&
      bl >= args.blade_length_min &&
      bl <= args.blade_length_max
    );
  });
  const scored = products.map((p) => {
    const score =
      0.4 * (p.seo_authority as number) +
      0.4 * Math.min((p.review_volume as number) / 15000, 1) +
      0.2 * ((p.ad_spend_tier as number) / 5);
    return {
      product_id: p.product_id,
      name: p.name,
      brand: p.brand,
      price_usd: p.price_usd,
      review_volume: p.review_volume,
      seo_authority: p.seo_authority,
      ad_spend_tier: p.ad_spend_tier,
      popularity_score: Number(score.toFixed(4)),
    };
  });
  scored.sort((a, b) => b.popularity_score - a.popularity_score);
  return { candidates: scored.slice(0, args.limit ?? 5) };
}

export async function getProductReviewsSummary(args: {
  product_id: string;
}): Promise<AnyRecord> {
  const data = loadMock();
  const product = (data.products as AnyRecord[]).find(
    (p) => p.product_id === args.product_id
  );
  if (!product) return { error: `unknown product_id ${args.product_id}` };
  const stars = Math.min(
    3.8 +
      0.6 * (product.seo_authority as number) +
      0.2 * ((product.ad_spend_tier as number) / 5),
    5
  );
  return {
    product_id: args.product_id,
    average_stars: Number(stars.toFixed(2)),
    review_count: product.review_volume,
    sample_headlines: [
      "Great knife, recommend!",
      "Came fast, feels solid.",
      "My wife loves it.",
    ],
  };
}

// ---------------------------------------------------------------------------
// Scenario B — Drachma API
// ---------------------------------------------------------------------------

async function drachmaCall(
  method: string,
  pathname: string,
  body?: unknown
): Promise<AnyRecord> {
  const res = await fetch(`${DRACHMA_URL}${pathname}`, {
    method,
    headers: { "content-type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    return { error: `HTTP ${res.status}: ${text}` };
  }
  return res.json();
}

export async function drachmaFeedQuery(args: {
  category: string;
  preference_profile: AnyRecord;
  limit?: number;
}): Promise<AnyRecord> {
  return drachmaCall("POST", "/feed/query", {
    category: args.category,
    preference_profile: args.preference_profile,
    limit: args.limit ?? 5,
  });
}

export async function drachmaGetAttestations(args: {
  product_id: string;
}): Promise<AnyRecord> {
  return drachmaCall("GET", `/attestations/${args.product_id}`);
}

export async function drachmaSubmitOutcome(args: {
  product_id: string;
  user_profile_tag: string;
  event: string;
  satisfaction: number;
}): Promise<AnyRecord> {
  return drachmaCall("POST", "/outcomes", args);
}

// ---------------------------------------------------------------------------
// OpenAI tool specs
// ---------------------------------------------------------------------------

export const TRADITIONAL_TOOLS = [
  {
    type: "function" as const,
    function: {
      name: "traditional_search",
      description:
        "Search products using mainstream popularity signals (SEO authority, review volume, ad spend).",
      parameters: {
        type: "object",
        properties: {
          max_price_usd: { type: "number" },
          blade_length_min: { type: "integer" },
          blade_length_max: { type: "integer" },
          limit: { type: "integer", default: 5 },
        },
        required: ["max_price_usd", "blade_length_min", "blade_length_max"],
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "get_product_reviews_summary",
      description: "Aggregate star rating and review count for a product.",
      parameters: {
        type: "object",
        properties: { product_id: { type: "string" } },
        required: ["product_id"],
      },
    },
  },
];

export const DRACHMA_TOOLS = [
  {
    type: "function" as const,
    function: {
      name: "drachma_feed_query",
      description:
        "Rank products in a category using the Drachma signal: creator attestations, post-purchase outcomes, niche fit, value. Use this first. Supported categories: 'chef_knife'.",
      parameters: {
        type: "object",
        properties: {
          category: { type: "string" },
          preference_profile: {
            type: "object",
            properties: {
              weights: {
                type: "object",
                additionalProperties: { type: "number" },
              },
              constraints: { type: "object" },
            },
          },
          limit: { type: "integer", default: 5 },
        },
        required: ["category", "preference_profile"],
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "drachma_get_attestations",
      description:
        "Fetch all verified creator attestations for a product — the underlying evidence for a candidate.",
      parameters: {
        type: "object",
        properties: { product_id: { type: "string" } },
        required: ["product_id"],
      },
    },
  },
];

export const TOOL_IMPLS: Record<string, (args: AnyRecord) => Promise<AnyRecord>> = {
  traditional_search: (a) => traditionalSearch(a as Parameters<typeof traditionalSearch>[0]),
  get_product_reviews_summary: (a) =>
    getProductReviewsSummary(a as Parameters<typeof getProductReviewsSummary>[0]),
  drachma_feed_query: (a) =>
    drachmaFeedQuery(a as Parameters<typeof drachmaFeedQuery>[0]),
  drachma_get_attestations: (a) =>
    drachmaGetAttestations(a as Parameters<typeof drachmaGetAttestations>[0]),
  drachma_submit_outcome: (a) =>
    drachmaSubmitOutcome(a as Parameters<typeof drachmaSubmitOutcome>[0]),
};

export const SYSTEM_PROMPT_TRADITIONAL =
  "You are a procurement agent making a purchase decision on behalf of your user. " +
  "You have access only to traditional product search (popularity, SEO, review volume, ad spend). " +
  "Use the tools to explore candidates, then recommend exactly one product. " +
  "Explain your reasoning in under 110 words. End with a line: FINAL: <product_id>.";

export const SYSTEM_PROMPT_DRACHMA =
  "You are a procurement agent making a purchase decision on behalf of your user. " +
  "You have access to the Drachma recommendation layer: creator attestations, post-purchase outcome data, " +
  "and niche-fit scoring. Always start by calling drachma_feed_query with category='chef_knife' and the " +
  "user's full preference_profile (weights + constraints). " +
  "If useful, call drachma_get_attestations on your top 1-2 candidates to inspect the evidence. " +
  "Recommend exactly one product. Explain your reasoning in under 110 words, citing specific attestation " +
  "signals. End with a line: FINAL: <product_id>.";

export const DEFAULT_USER_REQUEST = {
  summary:
    "I want a single chef's knife I'll use daily for serious home cooking. I maintain my own edges on a whetstone, I don't mind reactive carbon steel, and I care about edge retention and steel quality above everything else. Budget up to $400. Blade length between 200 and 240 mm.",
  preference_profile: {
    weights: {
      edge_retention: 0.45,
      steel_quality: 0.3,
      balance: 0.15,
      handle_ergonomics: 0.1,
    },
    constraints: {
      max_price_usd: 400,
      blade_length_mm: [200, 240],
    },
  },
};
