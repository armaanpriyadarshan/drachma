/**
 * User profile presets. Safe to import from client components
 * (no Node-only dependencies).
 */

export type ProfileId = "A" | "B" | "C";

export type ProfilePreset = {
  id: ProfileId;
  label: string;
  summary: string;
  narrative: string;
  preference_profile: {
    weights: Record<string, number>;
    constraints: Record<string, unknown>;
    composite_weights: Record<string, number>;
  };
};

export const PROFILES: Record<ProfileId, ProfilePreset> = {
  A: {
    id: "A",
    label: "Edge-obsessed carbon enthusiast",
    summary:
      "Daily serious home cooking. I maintain my own edges on a whetstone and don't mind reactive carbon steel. Edge retention and steel quality matter more than anything else, and I'll pay for the right knife.",
    narrative:
      "Price is secondary. Composite leans heavy on verified quality and niche coverage.",
    preference_profile: {
      weights: {
        edge_retention: 0.45,
        steel_quality: 0.30,
        balance: 0.15,
        handle_ergonomics: 0.10,
      },
      constraints: { max_price_usd: 400, blade_length_mm: [200, 240] },
      composite_weights: { quality: 0.50, coverage: 0.25, outcome: 0.20, value: 0.05 },
    },
  },
  B: {
    id: "B",
    label: "Precision workhorse, low maintenance",
    summary:
      "A knife that moves through prep cleanly and stays that way without babying it. Balance, handle ergonomics, fit-and-finish, and corrosion resistance. Willing to spend for the right geometry.",
    narrative:
      "Balanced composite weights, moderate value, emphasis on outcome signal.",
    preference_profile: {
      weights: {
        balance: 0.35,
        handle_ergonomics: 0.30,
        corrosion_resistance: 0.20,
        fit_and_finish: 0.15,
      },
      constraints: { max_price_usd: 400 },
      composite_weights: { quality: 0.35, coverage: 0.25, outcome: 0.30, value: 0.10 },
    },
  },
  C: {
    id: "C",
    label: "First serious knife, budget-first",
    summary:
      "First real chef's knife. Sharp out of the box, comfortable to hold, stainless so it doesn't need fussing over. Budget under $180. I'll upgrade later.",
    narrative: "High value weight. Quality matters but so does price.",
    preference_profile: {
      weights: {
        out_of_box_sharpness: 0.35,
        handle_ergonomics: 0.25,
        corrosion_resistance: 0.20,
        balance: 0.20,
      },
      constraints: { max_price_usd: 180 },
      composite_weights: { quality: 0.25, coverage: 0.15, outcome: 0.25, value: 0.35 },
    },
  },
};
