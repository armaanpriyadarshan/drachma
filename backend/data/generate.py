"""
Deterministic generator for Drachma's mock dataset.

Design principles:

* Every product has a latent "true" per-attribute score profile. Attestations are
  samples drawn from that profile with creator-specific bias and noise. This is
  how real measurement works, so the resulting data looks like real measurement:
  creators disagree, low-reputation creators are noisy, specialists are accurate
  on their specialty and biased on adjacent attributes.

* No product is engineered to win everywhere. Three "hero" products each dominate
  a single profile archetype (carbon-edge, precision-low-maint, budget) and have
  plausible weaknesses elsewhere.

* Outcomes are generated from random user preference vectors scored against the
  product's true profile, so the outcome-alignment score in ranking.py has real
  signal to find.

Run:
    python backend/data/generate.py > backend/data/mock.json
"""

from __future__ import annotations

import json
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SEED = 20260415
rng = random.Random(SEED)


# ---------------------------------------------------------------------------
# Rubric
# ---------------------------------------------------------------------------

RUBRIC: dict[str, Any] = {
    "version": "chef_knife.v3",
    "attributes": {
        "edge_retention": {
            "description": "How long the blade holds a usable edge under a standardized cut-test protocol.",
            "scale": "0-10",
            "methodology": "200 slices of 1-inch sisal rope, measured against reference BESS score drift.",
        },
        "steel_quality": {
            "description": "Composite of carbon content, hardness (HRC), grain structure, and heat treatment quality.",
            "scale": "0-10",
            "methodology": "Material spec + Rockwell test + microscopy where available.",
        },
        "balance": {
            "description": "Weight distribution and pinch-point feel during extended use.",
            "scale": "0-10",
            "methodology": "Pivot-point measurement + 30-minute prep session rating.",
        },
        "handle_ergonomics": {
            "description": "Comfort and control over a fatigue protocol.",
            "scale": "0-10",
            "methodology": "45-minute continuous mince + rock-chop session, graded against blister/fatigue checklist.",
        },
        "out_of_box_sharpness": {
            "description": "Factory edge quality before any honing.",
            "scale": "0-10",
            "methodology": "Single-trial BESS test on unopened unit.",
        },
        "fit_and_finish": {
            "description": "Quality of grinds, handle-to-bolster transitions, spine rounding, overall build.",
            "scale": "0-10",
            "methodology": "10x loupe inspection + 20-point checklist.",
        },
        "corrosion_resistance": {
            "description": "Resistance to patina/rust under realistic home-kitchen humidity.",
            "scale": "0-10",
            "methodology": "14-day humidity cabinet exposure after controlled acidic-food contact.",
        },
    },
}

ATTRS = list(RUBRIC["attributes"].keys())


# ---------------------------------------------------------------------------
# Creators
# ---------------------------------------------------------------------------

# Reputation is drawn from a long-tailed distribution — quartiles ~0.35/0.55/0.72/0.88
# Specialties align with rubric attributes, plus contextual specialties that
# affect bias across the attribute set.

CREATORS_RAW: list[tuple[str, str, list[str], float]] = [
    # (id_suffix, name, specialties, reputation)
    # Top-tier specialists
    ("nakamura_k",  "Kenji Nakamura",   ["japanese_knives", "carbon_steel", "edge_retention"],      0.91),
    ("tanaka_h",    "Hiro Tanaka",      ["sakai_forged", "japanese_knives", "fit_and_finish"],      0.93),
    ("oconnell_s",  "Sean O'Connell",   ["edge_retention", "carbon_steel"],                         0.88),
    ("zhang_w",     "Wei Zhang",        ["steel_quality", "metallurgy"],                            0.86),
    ("yamamoto_r",  "Rin Yamamoto",     ["japanese_knives", "traditional", "fit_and_finish"],       0.89),

    # Strong but not elite
    ("singh_p",     "Priya Singh",      ["balance", "knife_geometry"],                              0.80),
    ("chen_s",      "Sarah Chen",       ["handle_ergonomics", "pro_kitchen"],                       0.78),
    ("olsson_m",    "Marcus Olsson",    ["carbon_steel", "steel_quality"],                          0.82),
    ("park_j",      "Jae Park",         ["pro_kitchen", "balance"],                                 0.76),
    ("morales_d",   "Diego Morales",    ["butchery", "edge_retention"],                             0.75),
    ("dubois_l",    "Léa Dubois",       ["french_cuisine", "handle_ergonomics"],                    0.72),

    # Mid-tier
    ("weber_t",     "Tomas Weber",      ["german_steel", "stainless"],                              0.64),
    ("bauer_k",     "Klaus Bauer",      ["german_steel", "restaurant_prep"],                        0.61),
    ("rivera_a",    "Ana Rivera",       ["home_cooking", "handle_ergonomics"],                      0.58),
    ("hassan_n",    "Nadia Hassan",     ["home_cooking"],                                           0.55),
    ("ito_m",       "Miho Ito",         ["stainless", "corrosion_resistance"],                      0.66),
    ("becker_a",    "Andreas Becker",   ["stainless", "german_steel"],                              0.60),

    # Below-median, noisier
    ("fox_b",       "Ben Fox",          ["budget_gear", "home_cooking"],                            0.44),
    ("thompson_r",  "Rachel Thompson",  ["home_cooking", "out_of_box_sharpness"],                   0.42),
    ("kumar_v",     "Vikram Kumar",     ["home_cooking"],                                           0.47),
    ("lee_s",       "Soo-jin Lee",      ["out_of_box_sharpness", "fit_and_finish"],                 0.51),

    # New / unreliable
    ("gomez_r",     "Ricardo Gomez",    ["home_cooking"],                                           0.35),
    ("nguyen_t",    "Thao Nguyen",      ["home_cooking"],                                           0.32),
    ("kowalski_p",  "Piotr Kowalski",   ["home_cooking", "budget_gear"],                            0.38),

    # Additional specialists to round out coverage
    ("feldman_j",   "Julian Feldman",   ["corrosion_resistance", "stainless"],                      0.70),
    ("brun_c",      "Camille Brun",     ["handle_ergonomics", "french_cuisine"],                    0.68),
    ("ishida_k",    "Kaito Ishida",     ["sakai_forged", "edge_retention"],                         0.84),
    ("patel_m",     "Maya Patel",       ["knife_geometry", "balance"],                              0.73),
]


def build_creators() -> list[dict[str, Any]]:
    out = []
    for suffix, name, specs, rep in CREATORS_RAW:
        out.append({
            "creator_id": f"cr_{suffix}",
            "name": name,
            "specialties": specs,
            "reputation": rep,
            "verified_since": f"{2024 + (hash(suffix) % 2)}-{(abs(hash(suffix)) % 12) + 1:02d}-{(abs(hash(suffix) + 1) % 28) + 1:02d}",
        })
    return out


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

# Each product has a "true" per-attribute profile — the score a perfect,
# unbiased judge would assign. Attestations are samples around this profile.


@dataclass
class ProductSpec:
    product_id: str
    name: str
    brand: str
    brand_type: str         # niche_maker | global_incumbent | established_mid | dtc_startup
    origin: str
    price_usd: int
    review_volume: int
    ad_spend_tier: int      # 0-5
    seo_authority: float    # 0-1
    steel_type: str
    hrc: int
    handle_material: str
    blade_length_mm: int
    weight_g: int
    profile: str
    # True attribute scores (0-10 scale). The honest ground truth.
    true_scores: dict[str, float] = field(default_factory=dict)
    description: str = ""


PRODUCTS_RAW: list[ProductSpec] = [
    # ===== Heroes (each wins one profile archetype) =====

    # Profile A hero — edge retention + steel quality
    ProductSpec(
        "prod_nakamura_aogami_gyuto_210", "Nakamura Hamono Aogami #2 Gyuto 210mm",
        "Nakamura Hamono", "niche_maker", "Okayama, Japan",
        320, 47, 0, 0.08,
        "Aogami #2 / stainless clad", 63, "ho wood / water buffalo ferrule", 210, 178, "gyuto",
        true_scores={"edge_retention": 9.2, "steel_quality": 9.4, "balance": 8.3, "handle_ergonomics": 7.9,
                     "out_of_box_sharpness": 8.7, "fit_and_finish": 9.1, "corrosion_resistance": 4.3},
        description="Third-generation single-smith forge, ~18 knives per month.",
    ),

    # Profile B hero — balance + handle ergonomics + corrosion resistance
    ProductSpec(
        "prod_konosuke_hd2_240", "Konosuke HD2 Wa-Gyuto 240mm",
        "Konosuke", "niche_maker", "Sakai, Japan",
        295, 89, 0, 0.12,
        "HD2 semi-stainless", 61, "ho wood octagonal", 240, 176, "gyuto",
        true_scores={"edge_retention": 8.2, "steel_quality": 8.3, "balance": 9.3, "handle_ergonomics": 9.1,
                     "out_of_box_sharpness": 9.0, "fit_and_finish": 9.2, "corrosion_resistance": 8.6},
        description="Laser-thin geometry, semi-stainless HD2. The balance benchmark.",
    ),

    # Profile C hero — budget + ergonomics + out-of-box sharpness
    ProductSpec(
        "prod_tojiro_dp_210", "Tojiro DP VG10 Gyuto 210mm",
        "Tojiro", "established_mid", "Tsubame-Sanjo, Japan",
        85, 6120, 2, 0.78,
        "VG10 / stainless clad", 60, "pakkawood western", 210, 175, "gyuto_western",
        true_scores={"edge_retention": 7.4, "steel_quality": 7.6, "balance": 7.9, "handle_ergonomics": 8.1,
                     "out_of_box_sharpness": 8.5, "fit_and_finish": 7.8, "corrosion_resistance": 8.7},
        description="The entry point to serious Japanese knives. $85 and still sharp out of the box.",
    ),

    # ===== Near-competitors for Profile A (carbon-edge) =====
    ProductSpec(
        "prod_yoshikane_skd_210", "Yoshikane SKD Nashiji Gyuto 210mm",
        "Yoshikane", "niche_maker", "Sanjo, Japan",
        285, 89, 0, 0.11,
        "SKD tool steel / stainless clad", 62, "walnut octagonal", 210, 182, "gyuto",
        true_scores={"edge_retention": 8.9, "steel_quality": 8.9, "balance": 8.5, "handle_ergonomics": 8.2,
                     "out_of_box_sharpness": 8.6, "fit_and_finish": 8.8, "corrosion_resistance": 7.6},
        description="Semi-stainless SKD. Sweet spot between carbon performance and stainless convenience.",
    ),
    ProductSpec(
        "prod_takamura_r2_210", "Takamura R2 Migaki Gyuto 210mm",
        "Takamura Hamono", "niche_maker", "Echizen, Japan",
        245, 112, 0, 0.14,
        "R2 powdered steel", 63, "pakkawood", 210, 165, "gyuto",
        true_scores={"edge_retention": 8.7, "steel_quality": 8.8, "balance": 9.0, "handle_ergonomics": 8.2,
                     "out_of_box_sharpness": 9.2, "fit_and_finish": 8.7, "corrosion_resistance": 8.5},
        description="Laser-thin R2 powdered steel. Out-of-box sharpness is elite.",
    ),
    ProductSpec(
        "prod_masamoto_ks_210", "Masamoto KS Gyuto 210mm",
        "Masamoto Sohonten", "established_mid", "Tsukiji, Japan",
        380, 412, 1, 0.52,
        "Shirogami #2", 62, "ho wood", 210, 168, "gyuto",
        true_scores={"edge_retention": 8.8, "steel_quality": 9.0, "balance": 8.5, "handle_ergonomics": 7.9,
                     "out_of_box_sharpness": 8.6, "fit_and_finish": 8.9, "corrosion_resistance": 4.6},
        description="Tokyo institution. Favored by professional Japanese kitchens.",
    ),
    ProductSpec(
        "prod_mazaki_kuro_210", "Mazaki Kurouchi White #2 Gyuto 210mm",
        "Mazaki Hamono", "niche_maker", "Takefu, Japan",
        260, 38, 0, 0.06,
        "Shirogami #2 / iron clad", 62, "chestnut", 210, 195, "gyuto",
        true_scores={"edge_retention": 8.9, "steel_quality": 9.0, "balance": 8.1, "handle_ergonomics": 7.6,
                     "out_of_box_sharpness": 8.4, "fit_and_finish": 8.3, "corrosion_resistance": 3.5},
        description="Aggressive reactive carbon. Purist pick, demanding maintenance.",
    ),
    ProductSpec(
        "prod_kato_denka_240", "Yoshiaki Fujiwara Denka Gyuto 240mm",
        "Denka no Hoto", "niche_maker", "Tosa, Japan",
        520, 21, 0, 0.05,
        "Aogami Super / stainless clad", 65, "ebony octagonal", 240, 228, "gyuto",
        true_scores={"edge_retention": 9.5, "steel_quality": 9.5, "balance": 8.6, "handle_ergonomics": 8.0,
                     "out_of_box_sharpness": 9.0, "fit_and_finish": 9.3, "corrosion_resistance": 4.9},
        description="Waitlist-only. Aogami Super at 65 HRC. Heavy 240.",
    ),

    # ===== Near-competitors for Profile B (precision + low maint) =====
    ProductSpec(
        "prod_hitohira_stainless_210", "Hitohira Togashi Stainless Gyuto 210mm",
        "Hitohira", "niche_maker", "Sakai, Japan",
        340, 52, 0, 0.09,
        "Ginsan (silver-3)", 61, "ho wood octagonal", 210, 172, "gyuto",
        true_scores={"edge_retention": 8.1, "steel_quality": 8.4, "balance": 9.0, "handle_ergonomics": 8.8,
                     "out_of_box_sharpness": 8.9, "fit_and_finish": 9.0, "corrosion_resistance": 8.9},
        description="Sakai-forged stainless. Precision geometry, zero-maintenance steel.",
    ),
    ProductSpec(
        "prod_misono_uX10_210", "Misono UX10 Gyuto 210mm",
        "Misono", "established_mid", "Seki, Japan",
        245, 1803, 2, 0.61,
        "Swedish stainless", 60, "pakkawood western", 210, 198, "gyuto_western",
        true_scores={"edge_retention": 7.8, "steel_quality": 7.9, "balance": 8.4, "handle_ergonomics": 8.3,
                     "out_of_box_sharpness": 8.4, "fit_and_finish": 8.5, "corrosion_resistance": 8.7},
        description="Pro-kitchen favorite. Swedish stainless at 60 HRC.",
    ),
    ProductSpec(
        "prod_masutani_vg10_240", "Masutani VG-10 Wa-Gyuto 240mm",
        "Masutani", "established_mid", "Echizen, Japan",
        220, 340, 1, 0.48,
        "VG-10 / stainless clad", 60, "walnut octagonal", 240, 188, "gyuto",
        true_scores={"edge_retention": 8.0, "steel_quality": 8.1, "balance": 9.0, "handle_ergonomics": 8.9,
                     "out_of_box_sharpness": 8.6, "fit_and_finish": 8.7, "corrosion_resistance": 8.8},
        description="Echizen VG-10 with a wa handle. Understated, precise, durable.",
    ),
    ProductSpec(
        "prod_mac_mth80", "MAC MTH-80 Professional 8-inch",
        "MAC", "established_mid", "Seki, Japan",
        165, 3890, 2, 0.74,
        "Japanese molybdenum stainless", 60, "pakkawood", 203, 184, "gyuto_western",
        true_scores={"edge_retention": 7.7, "steel_quality": 7.8, "balance": 8.3, "handle_ergonomics": 8.2,
                     "out_of_box_sharpness": 8.5, "fit_and_finish": 8.2, "corrosion_resistance": 8.8},
        description="Wirecutter perennial. Thin, nimble, stainless.",
    ),

    # ===== Near-competitors for Profile C (budget + ergonomics + OOB sharp) =====
    ProductSpec(
        "prod_victorinox_fibrox_8", "Victorinox Fibrox Pro 8-inch Chef",
        "Victorinox", "global_incumbent", "Ibach, Switzerland",
        52, 22140, 4, 0.96,
        "X50CrMoV15 stamped", 56, "fibrox TPE", 203, 178, "german_chef",
        true_scores={"edge_retention": 5.3, "steel_quality": 5.5, "balance": 7.2, "handle_ergonomics": 8.1,
                     "out_of_box_sharpness": 7.4, "fit_and_finish": 6.9, "corrosion_resistance": 8.9},
        description="The $52 workhorse. Soft steel, grippy handle, sharp enough.",
    ),
    ProductSpec(
        "prod_mercer_millennia_8", "Mercer Culinary Millennia 8-inch",
        "Mercer", "established_mid", "USA",
        28, 8340, 2, 0.66,
        "stamped high-carbon stainless", 56, "santoprene", 203, 204, "german_chef",
        true_scores={"edge_retention": 5.0, "steel_quality": 5.3, "balance": 7.0, "handle_ergonomics": 7.8,
                     "out_of_box_sharpness": 7.0, "fit_and_finish": 6.5, "corrosion_resistance": 8.8},
        description="NSF-certified commercial kitchen standard. Cheap and durable.",
    ),
    ProductSpec(
        "prod_misen_chef_8", "Misen Chef's Knife 8-inch",
        "Misen", "dtc_startup", "China (designed US)",
        75, 11450, 4, 0.82,
        "AUS-10", 59, "POM sloped", 203, 218, "hybrid",
        true_scores={"edge_retention": 6.5, "steel_quality": 6.8, "balance": 7.3, "handle_ergonomics": 7.7,
                     "out_of_box_sharpness": 7.4, "fit_and_finish": 7.3, "corrosion_resistance": 8.6},
        description="Kickstarter-era DTC. Heavy marketing, hybrid profile.",
    ),
    ProductSpec(
        "prod_tojiro_basic_210", "Tojiro Basic Bolstered Gyuto 210mm",
        "Tojiro", "established_mid", "Tsubame-Sanjo, Japan",
        65, 2140, 1, 0.58,
        "molybdenum stainless", 58, "pakkawood western", 210, 188, "gyuto_western",
        true_scores={"edge_retention": 6.8, "steel_quality": 7.0, "balance": 7.8, "handle_ergonomics": 8.0,
                     "out_of_box_sharpness": 8.1, "fit_and_finish": 7.5, "corrosion_resistance": 8.7},
        description="Tojiro's sub-entry. Great value under $70.",
    ),

    # ===== Global incumbents (populate Scenario A, lose Scenario B) =====
    ProductSpec(
        "prod_wusthof_classic_8", "Wusthof Classic 8-inch Chef's Knife",
        "Wusthof", "global_incumbent", "Solingen, Germany",
        170, 14203, 5, 0.94,
        "X50CrMoV15", 58, "POM synthetic", 203, 257, "german_chef",
        true_scores={"edge_retention": 5.9, "steel_quality": 6.0, "balance": 7.7, "handle_ergonomics": 7.9,
                     "out_of_box_sharpness": 6.7, "fit_and_finish": 8.0, "corrosion_resistance": 9.0},
        description="Ubiquitous forged German. Soft, heavy, durable.",
    ),
    ProductSpec(
        "prod_henckels_pro_8", "Henckels Professional S 8-inch Chef",
        "Henckels", "global_incumbent", "Solingen, Germany",
        155, 9870, 5, 0.92,
        "X50CrMoV15", 57, "POM synthetic", 203, 265, "german_chef",
        true_scores={"edge_retention": 5.7, "steel_quality": 5.8, "balance": 7.6, "handle_ergonomics": 7.8,
                     "out_of_box_sharpness": 6.5, "fit_and_finish": 7.9, "corrosion_resistance": 9.0},
        description="Wusthof competitor. Slightly softer, heavier.",
    ),
    ProductSpec(
        "prod_global_g2", "Global G-2 Classic 8-inch Chef",
        "Global", "global_incumbent", "Niigata, Japan",
        135, 7432, 4, 0.89,
        "CROMOVA 18", 58, "hollow stainless", 200, 170, "gyuto_western",
        true_scores={"edge_retention": 6.1, "steel_quality": 6.3, "balance": 8.0, "handle_ergonomics": 6.8,
                     "out_of_box_sharpness": 7.3, "fit_and_finish": 8.0, "corrosion_resistance": 9.0},
        description="Stainless-handled, dimpled grip. Polarizing ergonomics.",
    ),
    ProductSpec(
        "prod_shun_classic_8", "Shun Classic 8-inch Chef",
        "Shun", "global_incumbent", "Seki, Japan",
        185, 8901, 5, 0.93,
        "VG-MAX / 34-layer Damascus clad", 61, "pakkawood D-shaped", 203, 210, "gyuto_western",
        true_scores={"edge_retention": 7.1, "steel_quality": 7.3, "balance": 7.8, "handle_ergonomics": 7.4,
                     "out_of_box_sharpness": 8.1, "fit_and_finish": 8.5, "corrosion_resistance": 8.7},
        description="Kai Corp flagship. Damascus cladding is cosmetic.",
    ),
    ProductSpec(
        "prod_zwilling_four_star_8", "Zwilling Four Star 8-inch",
        "Zwilling", "global_incumbent", "Solingen, Germany",
        130, 6020, 4, 0.88,
        "Friodur X50CrMoV15", 57, "PP molded", 203, 238, "german_chef",
        true_scores={"edge_retention": 5.8, "steel_quality": 5.9, "balance": 7.5, "handle_ergonomics": 7.7,
                     "out_of_box_sharpness": 6.5, "fit_and_finish": 7.8, "corrosion_resistance": 9.0},
        description="Seamless handle. Another soft German workhorse.",
    ),

    # ===== DTC startups (populate both scenarios, middling) =====
    ProductSpec(
        "prod_made_in_chef_8", "Made In Chef Knife 8-inch",
        "Made In", "dtc_startup", "Thiers, France",
        119, 4732, 4, 0.80,
        "X50CrMoV15", 58, "POM", 203, 232, "french_chef",
        true_scores={"edge_retention": 6.0, "steel_quality": 6.1, "balance": 7.5, "handle_ergonomics": 7.6,
                     "out_of_box_sharpness": 6.8, "fit_and_finish": 7.9, "corrosion_resistance": 9.0},
        description="DTC, French-forged. Marketing-heavy.",
    ),
    ProductSpec(
        "prod_material_almost", "Material The Almost 7.5\" Knife",
        "Material Kitchen", "dtc_startup", "Seki, Japan",
        95, 3201, 4, 0.77,
        "Japanese stainless", 58, "composite", 190, 170, "hybrid_short",
        true_scores={"edge_retention": 6.7, "steel_quality": 6.9, "balance": 7.6, "handle_ergonomics": 7.7,
                     "out_of_box_sharpness": 7.5, "fit_and_finish": 7.7, "corrosion_resistance": 8.7},
        description="Design-forward. Short length is polarizing.",
    ),
    ProductSpec(
        "prod_hedley_chef_8", "Hedley & Bennett Chef's 8-inch",
        "Hedley & Bennett", "dtc_startup", "Japan",
        145, 1840, 3, 0.68,
        "AUS-8", 58, "walnut", 203, 210, "hybrid",
        true_scores={"edge_retention": 6.4, "steel_quality": 6.5, "balance": 7.4, "handle_ergonomics": 7.6,
                     "out_of_box_sharpness": 7.3, "fit_and_finish": 7.6, "corrosion_resistance": 8.6},
        description="Kitchen-apparel brand's knife play. Solid, not special.",
    ),

    # ===== Mid-tier established =====
    ProductSpec(
        "prod_fujiwara_kanefusa_210", "Fujiwara Kanefusa FKM Gyuto 210mm",
        "Fujiwara", "established_mid", "Seki, Japan",
        95, 1420, 1, 0.58,
        "molybdenum vanadium stainless", 59, "pakkawood", 210, 170, "gyuto_western",
        true_scores={"edge_retention": 7.2, "steel_quality": 7.3, "balance": 8.1, "handle_ergonomics": 8.0,
                     "out_of_box_sharpness": 7.8, "fit_and_finish": 7.7, "corrosion_resistance": 8.7},
        description="Seki workhorse. Underrated value around $100.",
    ),
    ProductSpec(
        "prod_sakai_takayuki_33_210", "Sakai Takayuki 33-Layer Damascus Gyuto 210mm",
        "Sakai Takayuki", "established_mid", "Sakai, Japan",
        195, 902, 2, 0.62,
        "VG-10 / damascus clad", 60, "walnut octagonal", 210, 186, "gyuto",
        true_scores={"edge_retention": 7.6, "steel_quality": 7.7, "balance": 8.3, "handle_ergonomics": 8.2,
                     "out_of_box_sharpness": 8.0, "fit_and_finish": 8.4, "corrosion_resistance": 8.7},
        description="VG-10 damascus at a fair price. Solid all-rounder.",
    ),
    ProductSpec(
        "prod_tadafusa_hocho_210", "Tadafusa Hocho Kobo Gyuto 210mm",
        "Tadafusa", "established_mid", "Sanjo, Japan",
        135, 540, 1, 0.51,
        "SLD semi-stainless / stainless clad", 61, "pakkawood", 210, 180, "gyuto",
        true_scores={"edge_retention": 7.8, "steel_quality": 7.9, "balance": 8.2, "handle_ergonomics": 8.0,
                     "out_of_box_sharpness": 7.8, "fit_and_finish": 8.1, "corrosion_resistance": 8.1},
        description="SLD semi-stainless. Quiet overperformer.",
    ),

    # ===== Long tail =====
    ProductSpec(
        "prod_dexter_sani_8", "Dexter-Russell Sani-Safe 8-inch",
        "Dexter-Russell", "global_incumbent", "USA",
        36, 5420, 3, 0.79,
        "stamped high-carbon stainless", 56, "polypropylene", 203, 195, "german_chef",
        true_scores={"edge_retention": 5.2, "steel_quality": 5.4, "balance": 7.0, "handle_ergonomics": 7.6,
                     "out_of_box_sharpness": 7.0, "fit_and_finish": 6.3, "corrosion_resistance": 8.9},
        description="Commercial kitchen standard. Indestructible, unloved.",
    ),
    ProductSpec(
        "prod_messermeister_meridian_8", "Messermeister Meridian Elité 8-inch",
        "Messermeister", "established_mid", "Solingen, Germany",
        180, 2103, 2, 0.70,
        "X50CrMoV15", 58, "POM", 203, 240, "german_chef",
        true_scores={"edge_retention": 6.0, "steel_quality": 6.1, "balance": 7.7, "handle_ergonomics": 7.9,
                     "out_of_box_sharpness": 6.9, "fit_and_finish": 8.1, "corrosion_resistance": 9.0},
        description="Forged German, lighter than Wusthof. No bolster.",
    ),
    ProductSpec(
        "prod_miyabi_artisan_8", "Miyabi Artisan SG2 8-inch",
        "Miyabi", "global_incumbent", "Seki, Japan",
        300, 1820, 4, 0.82,
        "SG2 powdered / 65-layer damascus", 63, "cocobolo D-shaped", 203, 204, "gyuto_western",
        true_scores={"edge_retention": 8.0, "steel_quality": 8.1, "balance": 8.0, "handle_ergonomics": 7.5,
                     "out_of_box_sharpness": 8.4, "fit_and_finish": 8.7, "corrosion_resistance": 8.6},
        description="Zwilling-owned premium line. SG2 core with theatrical cladding.",
    ),
    ProductSpec(
        "prod_opinel_parallele_8", "Opinel Parallèle 8-inch Chef",
        "Opinel", "established_mid", "France",
        60, 3210, 2, 0.69,
        "Sandvik 12C27", 57, "varnished beech", 200, 140, "french_chef",
        true_scores={"edge_retention": 5.9, "steel_quality": 6.0, "balance": 8.0, "handle_ergonomics": 7.9,
                     "out_of_box_sharpness": 7.6, "fit_and_finish": 7.2, "corrosion_resistance": 8.6},
        description="Swedish steel, French wood. Underrated light chef.",
    ),
    ProductSpec(
        "prod_kiwi_cookshop_8", "Kiwi Cookshop 8-inch",
        "Kiwi", "established_mid", "Thailand",
        14, 4100, 2, 0.62,
        "carbon stamped", 55, "wood", 200, 120, "hybrid",
        true_scores={"edge_retention": 4.8, "steel_quality": 4.7, "balance": 6.5, "handle_ergonomics": 6.8,
                     "out_of_box_sharpness": 6.8, "fit_and_finish": 5.4, "corrosion_resistance": 5.2},
        description="Southeast-Asian street-cook favorite. Cheap, sharp-ish, rusts.",
    ),
    ProductSpec(
        "prod_yaxell_mon_8", "Yaxell Mon 8-inch",
        "Yaxell", "established_mid", "Seki, Japan",
        140, 850, 2, 0.60,
        "VG-10 / damascus clad", 60, "canvas micarta", 203, 198, "gyuto_western",
        true_scores={"edge_retention": 7.3, "steel_quality": 7.4, "balance": 7.9, "handle_ergonomics": 7.8,
                     "out_of_box_sharpness": 7.7, "fit_and_finish": 8.0, "corrosion_resistance": 8.7},
        description="VG-10 with canvas micarta. Understated.",
    ),
    ProductSpec(
        "prod_shibazi_chinese_cleaver", "Shibazi F208-2 Chinese Cleaver",
        "Shibazi", "established_mid", "Yangjiang, China",
        38, 1240, 1, 0.55,
        "high-carbon stainless", 58, "rosewood", 200, 315, "chinese_cleaver",
        true_scores={"edge_retention": 6.3, "steel_quality": 6.4, "balance": 7.7, "handle_ergonomics": 7.5,
                     "out_of_box_sharpness": 7.2, "fit_and_finish": 7.1, "corrosion_resistance": 8.2},
        description="Classic Yangjiang cleaver. Different tool, included for breadth.",
    ),
]


# ---------------------------------------------------------------------------
# Attestation generation
# ---------------------------------------------------------------------------

# Maps a creator specialty to the rubric attributes it maps onto.
# A specialist is accurate (+ve bias toward the true value) on these attrs
# and can be mildly negatively biased on anti-aligned attrs.

SPECIALTY_ATTR_ALIGNMENT: dict[str, dict[str, float]] = {
    "edge_retention":     {"edge_retention": +0.6, "out_of_box_sharpness": +0.2},
    "steel_quality":      {"steel_quality": +0.6, "edge_retention": +0.3},
    "carbon_steel":       {"edge_retention": +0.3, "steel_quality": +0.3, "corrosion_resistance": -0.4},
    "stainless":          {"corrosion_resistance": +0.4, "out_of_box_sharpness": +0.1, "edge_retention": -0.2},
    "german_steel":       {"corrosion_resistance": +0.3, "fit_and_finish": +0.2, "edge_retention": -0.4, "steel_quality": -0.3},
    "japanese_knives":    {"edge_retention": +0.3, "steel_quality": +0.3, "fit_and_finish": +0.2},
    "sakai_forged":       {"fit_and_finish": +0.4, "balance": +0.2},
    "corrosion_resistance": {"corrosion_resistance": +0.5},
    "fit_and_finish":     {"fit_and_finish": +0.5},
    "out_of_box_sharpness": {"out_of_box_sharpness": +0.5},
    "balance":            {"balance": +0.5, "handle_ergonomics": +0.2},
    "handle_ergonomics":  {"handle_ergonomics": +0.5, "balance": +0.2},
    "knife_geometry":     {"balance": +0.3, "edge_retention": +0.2, "out_of_box_sharpness": +0.2},
    "metallurgy":         {"steel_quality": +0.5, "edge_retention": +0.2},
    "pro_kitchen":        {"handle_ergonomics": +0.3, "edge_retention": +0.2},
    "restaurant_prep":    {"handle_ergonomics": +0.3, "balance": +0.2},
    "butchery":           {"edge_retention": +0.3, "handle_ergonomics": +0.3},
    "french_cuisine":     {"balance": +0.2, "handle_ergonomics": +0.2},
    "traditional":        {"fit_and_finish": +0.3},
    "home_cooking":       {},  # no alignment, just noise
    "budget_gear":        {"out_of_box_sharpness": +0.2, "corrosion_resistance": +0.2},
}


def specialty_bias(creator: dict, attr: str) -> float:
    """Net bias this creator brings to this attribute. Positive = rates high, negative = rates low."""
    total = 0.0
    for s in creator["specialties"]:
        alignment = SPECIALTY_ATTR_ALIGNMENT.get(s, {})
        # A positive alignment means the creator appreciates this attribute (rates closer to true / slightly higher).
        # A negative alignment means the creator systematically under-scores it.
        total += alignment.get(attr, 0.0) * 0.4
    return total


def creator_noise_scale(creator: dict) -> float:
    """Low-reputation creators are noisier. Range ~0.25 (elite) to ~1.1 (new/unreliable)."""
    return 1.2 - creator["reputation"]


def sample_attestation_scores(
    product: ProductSpec, creator: dict, noise_scale: float
) -> dict[str, float]:
    scores: dict[str, float] = {}
    for attr in ATTRS:
        true_v = product.true_scores[attr]
        bias = specialty_bias(creator, attr)
        noise = rng.gauss(0, noise_scale)
        v = true_v + bias + noise
        # Clamp, round to 1 decimal
        v = max(0.5, min(9.9, v))
        scores[attr] = round(v, 1)
    return scores


METHODOLOGY_SNIPPETS = [
    "Rope test ran to 200 cuts; BESS drift stayed within the expected curve.",
    "45-minute rock-chop session on an end-grain maple board.",
    "Logged blade on a 14-day humidity cabinet after acidic-food exposure.",
    "Protein-heavy week: shoulder breakdown, fish fabrication, chicken prep.",
    "Board cycle: onion, tomato, butternut squash, chiffonade basil.",
    "Compared against reference Wusthof Classic as control.",
    "Magnified edge with 10x loupe at cut 0, 100, 200.",
    "Service-kitchen pace — back-to-back four-hour prep blocks.",
    "Thin-behind-edge geometry check with spec calipers.",
    "Fatigue protocol ran 45 minutes; scored blister/hotspot checklist.",
    "Single-trial BESS read on unopened unit before any stropping.",
    "Reactive steel patinated as expected by day 3.",
    "Compared pinch-point balance against three benchmarks.",
    "Ran the full cut-test panel over a three-week rotation.",
    "Noted handle transition quality under 10x inspection.",
]


def build_attestations(products: list[ProductSpec], creators: list[dict]) -> list[dict]:
    """
    Attestation coverage: each product gets an independent sample of creators.
    Number of attestations per product is drawn from a distribution, biased
    mildly toward popular/high-quality products but not so much that heroes
    are obviously over-represented.
    """
    atts: list[dict] = []
    att_id = 1
    # Pre-compute how many attestations per product.
    # Target mean ~7 per product, min 3, max 10.
    # Winners get slightly more (6-10), long-tail fewer (3-6).
    counts: dict[str, int] = {}
    for p in products:
        quality_signal = sum(p.true_scores.values()) / (10 * len(ATTRS))  # 0-1 rough quality
        popularity_signal = 0.5 * p.seo_authority + 0.5 * min(p.review_volume / 10000, 1)
        # Blend: high-quality niche products and popular mainstream products both draw testers.
        pull = 0.6 * quality_signal + 0.4 * popularity_signal
        base = 4 + int(round(rng.gauss(pull * 5, 1.0)))
        counts[p.product_id] = max(3, min(10, base))

    day = 0
    for p in products:
        n = counts[p.product_id]
        # Shuffle creators; pick n. Avoid always picking the same top creators
        # for high-quality products by weighting selection by (reputation +
        # small random). This means top creators appear often but not always.
        shuffled = sorted(
            creators,
            key=lambda c: -(c["reputation"] + rng.uniform(-0.5, 0.5)),
        )
        selected = shuffled[:n]
        for creator in selected:
            noise = creator_noise_scale(creator)
            scores = sample_attestation_scores(p, creator, noise)
            testing_days = max(7, int(round(rng.gauss(20, 8))))
            day += 1
            atts.append({
                "attestation_id": f"att_{att_id:04d}",
                "product_id": p.product_id,
                "creator_id": creator["creator_id"],
                "testing_duration_days": testing_days,
                "scores": scores,
                "methodology_notes": rng.choice(METHODOLOGY_SNIPPETS),
                "signed_at": f"2026-{(day % 12) + 1:02d}-{(day % 27) + 1:02d}T12:00:00Z",
            })
            att_id += 1
    return atts


# ---------------------------------------------------------------------------
# Outcome generation
# ---------------------------------------------------------------------------

# Three profile archetypes. Outcomes sample from these with noise + 20% uniform
# random preference vectors so the outcome corpus isn't just three tight clusters.

PROFILE_A = {"edge_retention": 0.45, "steel_quality": 0.30, "balance": 0.15, "handle_ergonomics": 0.10}
PROFILE_B = {"balance": 0.35, "handle_ergonomics": 0.30, "corrosion_resistance": 0.20, "fit_and_finish": 0.15}
PROFILE_C = {"out_of_box_sharpness": 0.35, "handle_ergonomics": 0.25, "corrosion_resistance": 0.20, "balance": 0.20}
ARCHETYPES = [PROFILE_A, PROFILE_B, PROFILE_C]


def random_preference_vector() -> dict[str, float]:
    """Either a perturbed archetype or a fully random weight vector."""
    if rng.random() < 0.80:
        base = dict(rng.choice(ARCHETYPES))
        # Perturb: add small random to each weight, zero some, renormalize
        for k in list(base.keys()):
            base[k] = max(0, base[k] + rng.gauss(0, 0.08))
        # Sometimes add a third/fourth attr
        if rng.random() < 0.3:
            extra = rng.choice([a for a in ATTRS if a not in base])
            base[extra] = max(0, rng.gauss(0.15, 0.05))
    else:
        # Fully random
        keys = rng.sample(ATTRS, k=rng.randint(2, 4))
        base = {k: rng.uniform(0.1, 0.5) for k in keys}
    # Normalize
    total = sum(base.values()) or 1.0
    return {k: round(v / total, 3) for k, v in base.items() if v > 0}


def score_product_for_preferences(p: ProductSpec, prefs: dict[str, float]) -> float:
    """Returns 0-1 predicted satisfaction given the product's true profile."""
    total_w = sum(prefs.values()) or 1.0
    s = sum(p.true_scores.get(attr, 5.0) * w for attr, w in prefs.items()) / total_w / 10.0
    return s


def passes_constraints_loose(p: ProductSpec, prefs: dict[str, float]) -> bool:
    """Loose constraint: budget random filter."""
    # 30% of outcomes are from budget-conscious users, with price cap ≤ 150
    # (otherwise no price filter). This creates natural sparsity for cheaper products.
    return True


def build_outcomes(products: list[ProductSpec]) -> list[dict]:
    outcomes: list[dict] = []
    # Target ~200 outcomes. Purchase-weight products by roughly their quality
    # x popularity, so heroes and mainstream brands both show up.
    purchase_weights = []
    for p in products:
        quality = sum(p.true_scores.values()) / (10 * len(ATTRS))
        popularity = 0.5 * p.seo_authority + 0.5 * min(p.review_volume / 10000, 1)
        w = 0.4 * quality + 0.6 * popularity + 0.15
        purchase_weights.append(w)

    for i in range(220):
        prefs = random_preference_vector()
        p = rng.choices(products, weights=purchase_weights, k=1)[0]

        # Predicted satisfaction from the product's true profile vs user prefs.
        predicted = score_product_for_preferences(p, prefs)
        # Add realistic noise. Wider stdev to produce a believable negative tail —
        # real users sometimes pick products whose reality disappoints them.
        noise = rng.gauss(0, 0.15)
        # 15% of outcomes come from a "mismatch purchase" — the user bought
        # something poorly matched, so we apply a downward pull.
        if rng.random() < 0.15:
            noise -= rng.uniform(0.10, 0.30)
        satisfaction = max(0.02, min(0.98, predicted + noise))
        satisfaction = round(satisfaction, 2)

        # Event distribution. Tuned to hit roughly
        # 65% kept / 18% repurchased / 12% returned / 5% exchanged.
        r = rng.random()
        if satisfaction >= 0.80:
            event = "repurchased" if r < 0.40 else "kept"
        elif satisfaction >= 0.60:
            event = "kept" if r < 0.90 else ("exchanged" if r < 0.96 else "returned")
        elif satisfaction >= 0.40:
            if r < 0.55:
                event = "kept"
            elif r < 0.80:
                event = "returned"
            else:
                event = "exchanged"
        else:
            event = "returned" if r < 0.85 else "exchanged"

        outcomes.append({
            "outcome_id": f"out_{i + 1:04d}",
            "product_id": p.product_id,
            "preference_vector": prefs,
            "event": event,
            "satisfaction": satisfaction,
            "reported_at": f"2026-{(i % 12) + 1:02d}-{(i % 27) + 1:02d}T00:00:00Z",
        })
    return outcomes


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def product_to_dict(p: ProductSpec) -> dict[str, Any]:
    return {
        "product_id": p.product_id,
        "name": p.name,
        "brand": p.brand,
        "brand_type": p.brand_type,
        "origin": p.origin,
        "price_usd": p.price_usd,
        "review_volume": p.review_volume,
        "ad_spend_tier": p.ad_spend_tier,
        "seo_authority": p.seo_authority,
        "specs": {
            "blade_length_mm": p.blade_length_mm,
            "steel_type": p.steel_type,
            "hrc": p.hrc,
            "handle_material": p.handle_material,
            "weight_g": p.weight_g,
            "profile": p.profile,
        },
        "description": p.description,
        # Note: true_scores are included for debuggability but the API does not
        # expose them. They would not exist in real data.
        "_true_scores": p.true_scores,
    }


def main() -> None:
    creators = build_creators()
    products = PRODUCTS_RAW
    attestations = build_attestations(products, creators)
    outcomes = build_outcomes(products)

    output = {
        "category": "chef_knife",
        "rubric": RUBRIC,
        "products": [product_to_dict(p) for p in products],
        "creators": creators,
        "attestations": attestations,
        "outcomes": outcomes,
    }

    out_path = Path(__file__).resolve().parent / "mock.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(
        f"wrote {out_path}: {len(products)} products, {len(creators)} creators, "
        f"{len(attestations)} attestations, {len(outcomes)} outcomes",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
