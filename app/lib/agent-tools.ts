/**
 * Tool implementations shared between the two agent scenarios.
 *
 * Scenario A: traditional popularity-based search (local JSON, SEO / reviews / ad spend).
 * Scenario B: HTTP to the Drachma FastAPI backend.
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

export { PROFILES, type ProfileId, type ProfilePreset } from "./profiles";

// ---------------------------------------------------------------------------
// Scenario A — traditional ranking
// ---------------------------------------------------------------------------

export async function traditionalSearch(args: {
  max_price_usd: number;
  blade_length_min?: number;
  blade_length_max?: number;
  limit?: number;
}): Promise<AnyRecord> {
  const data = loadMock();
  const products = (data.products as AnyRecord[]).filter((p) => {
    const bl = (p.specs as AnyRecord).blade_length_mm as number;
    if ((p.price_usd as number) > args.max_price_usd) return false;
    if (args.blade_length_min !== undefined && bl < args.blade_length_min) return false;
    if (args.blade_length_max !== undefined && bl > args.blade_length_max) return false;
    return true;
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
  // Stars: weakly correlated with popularity (review count and brand recognition
  // correlate with a happier average rating in practice), plus independent noise
  // so stars aren't a deterministic restatement of ad metrics.
  const popularity = 0.5 * (product.seo_authority as number) +
    0.5 * Math.min((product.review_volume as number) / 15000, 1);
  // Deterministic pseudo-random noise tied to product_id so repeated calls agree.
  let seed = 0;
  for (const c of args.product_id) seed = (seed * 31 + c.charCodeAt(0)) | 0;
  const noise = (Math.sin(seed) * 10000) % 1; // in (-1, 1)
  const stars = Math.max(3.4, Math.min(4.9, 3.9 + 0.5 * popularity + 0.35 * noise));
  return {
    product_id: args.product_id,
    average_stars: Number(stars.toFixed(2)),
    review_count: product.review_volume,
    sample_headlines: [
      "Great knife, recommend!",
      "Came fast, feels solid.",
      "Sharper than expected.",
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

// ---------------------------------------------------------------------------
// OpenAI tool specs
// ---------------------------------------------------------------------------

export const TRADITIONAL_TOOLS = [
  {
    type: "function" as const,
    function: {
      name: "traditional_search",
      description:
        "Search products using mainstream popularity signals (SEO authority, review volume, ad spend). Applies a price cap and optional blade length range.",
      parameters: {
        type: "object",
        properties: {
          max_price_usd: { type: "number" },
          blade_length_min: { type: "integer" },
          blade_length_max: { type: "integer" },
          limit: { type: "integer", default: 5 },
        },
        required: ["max_price_usd"],
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
        "Rank products against a user preference profile using Drachma's four-dimension composite: verified quality, expert coverage, outcome alignment, value. Pass the full preference_profile including weights, constraints, and composite_weights. Supported category: 'chef_knife'.",
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
              composite_weights: {
                type: "object",
                additionalProperties: { type: "number" },
                description: "Weights over (quality, coverage, outcome, value).",
              },
            },
            required: ["weights"],
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
        "Fetch all verified creator attestations for a product. Includes creator specialties and current reputation.",
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
};

export const SYSTEM_PROMPT_TRADITIONAL =
  "You are a procurement agent. You have access only to traditional product search tools " +
  "(popularity, SEO, review volume, ad spend). Use them to explore candidates and recommend " +
  "exactly one product for the user. Explain your reasoning in under 100 words. " +
  "End with a line: FINAL: <product_id>.";

export const SYSTEM_PROMPT_DRACHMA =
  "You are a procurement agent. You have access to the Drachma recommendation layer: creator " +
  "attestations, post-purchase outcome data, and niche-fit scoring. Always start with " +
  "drachma_feed_query — pass the user's full preference_profile including weights, constraints, " +
  "and composite_weights. If useful, call drachma_get_attestations on your top 1-2 candidates " +
  "to inspect the evidence (creator specialties, scores, reputations). Recommend exactly one " +
  "product. Explain your reasoning in under 100 words, citing specific specialists and per-" +
  "dimension scores. End with a line: FINAL: <product_id>.";
