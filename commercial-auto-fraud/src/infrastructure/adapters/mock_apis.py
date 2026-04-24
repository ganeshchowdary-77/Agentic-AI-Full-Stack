"""
Mock Enrichment Provider
=========================
Simulates 4 external data APIs for the fraud detection pipeline.
Each method returns claim-specific data keyed by ID, not a binary suspicious/clean flag.

Data is designed to hit the exact thresholds from the fraud pattern specs:
  Pattern 1 (Duplicate)   : same VIN, same claimant, overlapping loss dates
  Pattern 2 (Timing)      : days_since_inception < 30, coverage change within 72h
  Pattern 3 (Inflated)    : claimed_amount > market_value, billing_ratio > 2.0
  Pattern 4 (Provider Net): billing_ratio > 2.0, circular referrals, expired license

Claim scenarios in weekly_auto_claims.json:
  CLM-001  C-4821 / PRV-0093 / POL-99-1234  → P1(dup) + P4(provider) + P2(timing)  → HIGH
  CLM-002  C-4821 / PRV-0093 / POL-99-5678  → P1(CRITICAL dup, same VIN 2 days)    → CRITICAL
  CLM-003  C-5502 / PRV-0200 / POL-99-7890  → P3(inflated medical) + P2(new policy) → HIGH
  CLM-004  C-201  / PRV-0301 / POL-200-4432 → P4(referral ring: 301→200→093→301)   → MEDIUM
  CLM-005  C-103  / PRV-0093 / POL-99-2211  → P3(repair > market) + P2(lapse+reinstate) → HIGH
  CLM-006  C-104  / PRV-0150 / POL-300-8821 → P2(Fri night/Mon report, minimal)    → LOW
  CLM-007  C-601  / PRV-0400 / POL-88-4411  → P3(repair > market) + P2(72h upgrade) → HIGH
  CLM-008  C-701  / PRV-0500 / POL-400-1122 → CLEAN                                → LOW
"""

from typing import Dict, Any
from src.core.ports.data_provider import IEnrichmentProvider


# ── Claimant History ──────────────────────────────────────────────────────────

_CLAIMANT_HISTORY: Dict[str, Dict] = {
    # Marcus Rivera — 4 prior claims, 2 fraud flags, high frequency, same VIN appears again
    "C-4821": {
        "total_prior_claims": 4,
        "prior_fraud_flags": 2,
        "claim_frequency_per_year": 2.4,
        "total_prior_payouts": 87000.0,
        "known_addresses": ["412 Maple St, Chicago IL", "88 Oak Ave, Evanston IL"],
        "associated_vehicles": [
            {"vin": "1HGCM82633A004352", "year": 2022, "make": "Honda", "model": "Accord"},
            {"vin": "5NMSH13E48H100001", "year": 2021, "make": "Hyundai", "model": "Tucson"},
        ],
        "associated_policies": ["POL-99-1234", "POL-99-5678", "POL-99-0011"],
        "prior_claims": [
            {
                "claim_id": "CLM-2025-088",
                "loss_date": "2025-09-14",
                "loss_type": "major_collision",
                "claimed_amount": 41000.0,
                "outcome": "paid",
                "fraud_flag": True,
            },
            {
                "claim_id": "CLM-2025-012",
                "loss_date": "2025-02-20",
                "loss_type": "major_collision",
                "claimed_amount": 38000.0,
                "outcome": "paid",
                "fraud_flag": False,
            },
            {
                "claim_id": "CLM-2024-441",
                "loss_date": "2024-07-05",
                "loss_type": "major_collision",
                "claimed_amount": 29500.0,
                "outcome": "denied",
                "fraud_flag": True,
            },
        ],
    },

    # Diana Kowalski — 2 prior claims, 1 fraud flag, medical pattern
    "C-5502": {
        "total_prior_claims": 2,
        "prior_fraud_flags": 1,
        "claim_frequency_per_year": 1.1,
        "total_prior_payouts": 62000.0,
        "known_addresses": ["77 Park Ave, Detroit MI"],
        "associated_vehicles": [
            {"vin": "2T1BR32E61C002711", "year": 2019, "make": "Toyota", "model": "Camry"},
        ],
        "associated_policies": ["POL-99-7890"],
        "prior_claims": [
            {
                "claim_id": "CLM-2025-199",
                "loss_date": "2025-03-12",
                "loss_type": "comprehensive",
                "claimed_amount": 48000.0,
                "outcome": "paid",
                "fraud_flag": True,
            },
        ],
    },

    # Thomas Bennett — thin history, referral ring clue
    "C-201": {
        "total_prior_claims": 1,
        "prior_fraud_flags": 0,
        "claim_frequency_per_year": 0.5,
        "total_prior_payouts": 6200.0,
        "known_addresses": ["330 Elm St, Indianapolis IN"],
        "associated_vehicles": [
            {"vin": "3VWFE21C04M000001", "year": 2021, "make": "Volkswagen", "model": "Jetta"},
        ],
        "associated_policies": ["POL-200-4432"],
        "prior_claims": [],
    },

    # Priya Menon — lapse history, medium prior claims
    "C-103": {
        "total_prior_claims": 2,
        "prior_fraud_flags": 0,
        "claim_frequency_per_year": 0.9,
        "total_prior_payouts": 15000.0,
        "known_addresses": ["5511 Lakeview Dr, Milwaukee WI"],
        "associated_vehicles": [
            {"vin": "5XYKT3A62DG143001", "year": 2020, "make": "Kia", "model": "Sorento"},
        ],
        "associated_policies": ["POL-99-2211"],
        "prior_claims": [],
    },

    # Robert Kim — clean
    "C-104": {
        "total_prior_claims": 0,
        "prior_fraud_flags": 0,
        "claim_frequency_per_year": 0.2,
        "total_prior_payouts": 0.0,
        "known_addresses": ["210 Cedar Ave, Columbus OH"],
        "associated_vehicles": [
            {"vin": "1N4AL3AP4EC123456", "year": 2023, "make": "Nissan", "model": "Altima"},
        ],
        "associated_policies": ["POL-300-8821"],
        "prior_claims": [],
    },

    # Elena Vasquez — commercial fleet, new claimant
    "C-601": {
        "total_prior_claims": 1,
        "prior_fraud_flags": 0,
        "claim_frequency_per_year": 0.5,
        "total_prior_payouts": 12000.0,
        "known_addresses": ["9 Commerce Blvd, Houston TX"],
        "associated_vehicles": [
            {"vin": "1FTBW2CM4JKA12345", "year": 2018, "make": "Ford", "model": "Transit"},
        ],
        "associated_policies": ["POL-88-4411"],
        "prior_claims": [],
    },

    # Sarah Chen — clean
    "C-701": {
        "total_prior_claims": 0,
        "prior_fraud_flags": 0,
        "claim_frequency_per_year": 0.1,
        "total_prior_payouts": 0.0,
        "known_addresses": ["888 Willow Way, Portland OR"],
        "associated_vehicles": [
            {"vin": "4T1BF1FK5GU123456", "year": 2024, "make": "Toyota", "model": "Camry"},
        ],
        "associated_policies": ["POL-400-1122"],
        "prior_claims": [],
    },

    # James Okafor — 2 prior claims, 1 fraud flag, PRV-0093 used before (CLM-009)
    "C-802": {
        "total_prior_claims": 2,
        "prior_fraud_flags": 1,
        "claim_frequency_per_year": 1.3,
        "total_prior_payouts": 62000.0,
        "known_addresses": ["22 Riverside Dr, Chicago IL"],
        "associated_vehicles": [
            {"vin": "WBA3A5C50DF000109", "year": 2020, "make": "BMW", "model": "3 Series"},
        ],
        "associated_policies": ["POL-99-8844"],
        "prior_claims": [
            {
                "claim_id": "CLM-2025-301",
                "loss_date": "2025-07-18",
                "loss_type": "major_collision",
                "claimed_amount": 33000.0,
                "outcome": "paid",
                "fraud_flag": True,
            },
        ],
    },

    # Linda Park — clean, first claim (CLM-010)
    "C-901": {
        "total_prior_claims": 0,
        "prior_fraud_flags": 0,
        "claim_frequency_per_year": 0.1,
        "total_prior_payouts": 0.0,
        "known_addresses": ["440 Pine Rd, Minneapolis MN"],
        "associated_vehicles": [
            {"vin": "1G1ZD5ST8JF100010", "year": 2021, "make": "Chevrolet", "model": "Malibu"},
        ],
        "associated_policies": ["POL-500-3310"],
        "prior_claims": [],
    },

    # David Torres — 1 prior claim, clean (CLM-011)
    "C-902": {
        "total_prior_claims": 1,
        "prior_fraud_flags": 0,
        "claim_frequency_per_year": 0.4,
        "total_prior_payouts": 7800.0,
        "known_addresses": ["615 Market St, Denver CO"],
        "associated_vehicles": [
            {"vin": "3FADP4BJ7BM100011", "year": 2022, "make": "Ford", "model": "Fusion"},
        ],
        "associated_policies": ["POL-600-7721"],
        "prior_claims": [],
    },

    # Amy Johnson — 1 prior claim with fraud flag, medical ring link via PRV-0200 (CLM-012)
    "C-903": {
        "total_prior_claims": 1,
        "prior_fraud_flags": 1,
        "claim_frequency_per_year": 0.8,
        "total_prior_payouts": 39000.0,
        "known_addresses": ["3301 Oak Park Blvd, Detroit MI"],
        "associated_vehicles": [
            {"vin": "5J8TB3H56GL100012", "year": 2023, "make": "Acura", "model": "RDX"},
        ],
        "associated_policies": ["POL-99-0012"],
        "prior_claims": [
            {
                "claim_id": "CLM-2025-422",
                "loss_date": "2025-10-03",
                "loss_type": "comprehensive",
                "claimed_amount": 36500.0,
                "outcome": "paid",
                "fraud_flag": True,
            },
        ],
    },
}


# ── Provider Network ──────────────────────────────────────────────────────────
# PRV-0093 → PRV-0200 → PRV-0301 → PRV-0093 (circular ring)

_PROVIDER_NETWORK: Dict[str, Dict] = {
    # PRV-0093: Primary suspicious repair shop — billing 2.96x regional, under investigation
    "PRV-0093": {
        "provider_name": "FastFix Auto Body",
        "license_status": "under_investigation",
        "total_claims_served": 312,
        "average_billing_amount": 14800.0,
        "regional_average_billing": 5000.0,
        "billing_ratio": 2.96,
        "flagged_claims_count": 47,
        "geographic_service_area": "Chicago Metro",
        "claims_outside_service_area": 18,
        "referral_connections": [
            {"provider_id": "PRV-0200", "provider_name": "QuickMed Clinic", "shared_claims": 28},
            {"provider_id": "PRV-0301", "provider_name": "Speedy Parts & Service", "shared_claims": 14},
        ],
    },

    # PRV-0200: Medical provider in the ring — billing 3.1x regional
    "PRV-0200": {
        "provider_name": "QuickMed Injury Clinic",
        "license_status": "active",
        "total_claims_served": 198,
        "average_billing_amount": 15500.0,
        "regional_average_billing": 5000.0,
        "billing_ratio": 3.10,
        "flagged_claims_count": 31,
        "geographic_service_area": "Detroit Metro",
        "claims_outside_service_area": 22,
        "referral_connections": [
            {"provider_id": "PRV-0093", "provider_name": "FastFix Auto Body", "shared_claims": 28},
            {"provider_id": "PRV-0301", "provider_name": "Speedy Parts & Service", "shared_claims": 11},
        ],
    },

    # PRV-0301: Completes the circular ring
    "PRV-0301": {
        "provider_name": "Speedy Parts & Service",
        "license_status": "active",
        "total_claims_served": 87,
        "average_billing_amount": 7600.0,
        "regional_average_billing": 5000.0,
        "billing_ratio": 1.52,
        "flagged_claims_count": 8,
        "geographic_service_area": "Indianapolis Metro",
        "claims_outside_service_area": 3,
        "referral_connections": [
            {"provider_id": "PRV-0093", "provider_name": "FastFix Auto Body", "shared_claims": 14},
            {"provider_id": "PRV-0200", "provider_name": "QuickMed Injury Clinic", "shared_claims": 11},
        ],
    },

    # PRV-0150: Clean medical provider (CLM-006 — only timing flag)
    "PRV-0150": {
        "provider_name": "Eastside Family Medical",
        "license_status": "active",
        "total_claims_served": 204,
        "average_billing_amount": 5100.0,
        "regional_average_billing": 5000.0,
        "billing_ratio": 1.02,
        "flagged_claims_count": 1,
        "geographic_service_area": "Columbus Metro",
        "claims_outside_service_area": 0,
        "referral_connections": [],
    },

    # PRV-0400: Elevated billing for CLM-007, not in ring
    "PRV-0400": {
        "provider_name": "TexasTruck Repair Center",
        "license_status": "active",
        "total_claims_served": 144,
        "average_billing_amount": 12000.0,
        "regional_average_billing": 5000.0,
        "billing_ratio": 2.40,
        "flagged_claims_count": 9,
        "geographic_service_area": "Houston Metro",
        "claims_outside_service_area": 4,
        "referral_connections": [],
    },

    # PRV-0500: Clean (CLM-008)
    "PRV-0500": {
        "provider_name": "Pacific Auto Works",
        "license_status": "active",
        "total_claims_served": 312,
        "average_billing_amount": 4800.0,
        "regional_average_billing": 5000.0,
        "billing_ratio": 0.96,
        "flagged_claims_count": 0,
        "geographic_service_area": "Portland Metro",
        "claims_outside_service_area": 0,
        "referral_connections": [],
    },

    # PRV-0600: Clean independent (CLM-010)
    "PRV-0600": {
        "provider_name": "Northside Auto Repair",
        "license_status": "active",
        "total_claims_served": 88,
        "average_billing_amount": 5200.0,
        "regional_average_billing": 5000.0,
        "billing_ratio": 1.04,
        "flagged_claims_count": 0,
        "geographic_service_area": "Minneapolis Metro",
        "claims_outside_service_area": 0,
        "referral_connections": [],
    },

    # PRV-0700: Normal-billing shop (CLM-011)
    "PRV-0700": {
        "provider_name": "Mile High Collision Center",
        "license_status": "active",
        "total_claims_served": 155,
        "average_billing_amount": 11000.0,
        "regional_average_billing": 10000.0,
        "billing_ratio": 1.10,
        "flagged_claims_count": 2,
        "geographic_service_area": "Denver Metro",
        "claims_outside_service_area": 1,
        "referral_connections": [],
    },
}


# ── Vehicle Valuation ─────────────────────────────────────────────────────────
# Market values set so specific VINs trigger inflated amount flags

_VIN_MARKET_VALUES: Dict[str, float] = {
    "1HGCM82633A004352": 29500.0,   # CLM-001/002: $42K/$38.5K claimed > $29.5K market value
    "2T1BR32E61C002711": 18000.0,   # CLM-003: $55K medical for $18K vehicle (fender-bender)
    "3VWFE21C04M000001": 22000.0,   # CLM-004: $8.2K repair on $22K vehicle — within range
    "5XYKT3A62DG143001": 21500.0,   # CLM-005: $29K claimed > $21.5K market value
    "1N4AL3AP4EC123456": 35000.0,   # CLM-006: $4.5K on $35K vehicle — clean
    "1FTBW2CM4JKA12345": 31000.0,   # CLM-007: $48K claimed > $31K market value (fleet truck)
    "4T1BF1FK5GU123456": 42000.0,   # CLM-008: $3.2K on $42K vehicle — clean
    "WBA3A5C50DF000109": 28000.0,   # CLM-009: $35.5K claimed > $28K market value (BMW)
    "1G1ZD5ST8JF100010": 24000.0,   # CLM-010: $5.8K on $24K vehicle — clean
    "3FADP4BJ7BM100011": 26000.0,   # CLM-011: $12.6K on $26K vehicle — within range
    "5J8TB3H56GL100012": 38000.0,   # CLM-012: $41K claimed > $38K market value (Acura)
}


# ── Policy Details ────────────────────────────────────────────────────────────

_POLICY_DETAILS: Dict[str, Dict] = {
    # POL-99-1234: New policy (14 days) + coverage upgrade 10 days before loss → Timing P2 major
    "POL-99-1234": {
        "inception_date": "2026-03-28",
        "expiration_date": "2027-03-28",
        "days_since_inception": 14,
        "days_until_expiration": 351,
        "coverage_type": "comprehensive",
        "coverage_limits": {"liability": 1000000.0, "collision": 50000.0, "medical": 100000.0},
        "premium_amount": 1800.0,
        "premium_payment_history": [{"date": "2026-03-28", "amount": 1800.0, "status": "paid"}],
        "recent_policy_changes": [
            {
                "change_date": "2026-04-01",
                "change_type": "coverage_upgrade",
                "details": "Collision limit increased from $25K to $50K — 10 days before loss date",
            }
        ],
        "vehicles_on_policy": [{"vin": "1HGCM82633A004352", "date_added": "2026-03-28"}],
        "policy_status": "active",
        "lapse_history": [{"lapse_date": "2025-12-01", "reinstate_date": "2026-01-15"}],
    },

    # POL-99-5678: Second policy (CLM-002, same claimant/VIN as CLM-001) → Duplicate P1 critical
    "POL-99-5678": {
        "inception_date": "2026-01-15",
        "expiration_date": "2027-01-15",
        "days_since_inception": 88,
        "days_until_expiration": 277,
        "coverage_type": "comprehensive",
        "coverage_limits": {"liability": 500000.0, "collision": 40000.0, "medical": 50000.0},
        "premium_amount": 1400.0,
        "premium_payment_history": [
            {"date": "2026-01-15", "amount": 1400.0, "status": "paid"},
            {"date": "2026-02-15", "amount": 1400.0, "status": "paid"},
            {"date": "2026-03-15", "amount": 1400.0, "status": "paid"},
        ],
        "recent_policy_changes": [],
        "vehicles_on_policy": [{"vin": "1HGCM82633A004352", "date_added": "2026-01-15"}],
        "policy_status": "active",
        "lapse_history": [],
    },

    # POL-99-7890: New policy (21 days) — Timing flag for CLM-003
    "POL-99-7890": {
        "inception_date": "2026-03-17",
        "expiration_date": "2027-03-17",
        "days_since_inception": 21,
        "days_until_expiration": 344,
        "coverage_type": "comprehensive",
        "coverage_limits": {"liability": 1000000.0, "collision": 60000.0, "medical": 150000.0},
        "premium_amount": 2100.0,
        "premium_payment_history": [{"date": "2026-03-17", "amount": 2100.0, "status": "paid"}],
        "recent_policy_changes": [
            {
                "change_date": "2026-03-20",
                "change_type": "medical_coverage_upgrade",
                "details": "Medical limit raised from $50K to $150K — 18 days before loss",
            }
        ],
        "vehicles_on_policy": [{"vin": "2T1BR32E61C002711", "date_added": "2026-03-17"}],
        "policy_status": "active",
        "lapse_history": [],
    },

    # POL-200-4432: Long-standing, clean — only referral ring triggers P4 for CLM-004
    "POL-200-4432": {
        "inception_date": "2023-06-01",
        "expiration_date": "2027-06-01",
        "days_since_inception": 1056,
        "days_until_expiration": 404,
        "coverage_type": "collision",
        "coverage_limits": {"liability": 300000.0, "collision": 25000.0, "medical": 30000.0},
        "premium_amount": 980.0,
        "premium_payment_history": [
            {"date": "2026-01-01", "amount": 980.0, "status": "paid"},
            {"date": "2026-04-01", "amount": 980.0, "status": "paid"},
        ],
        "recent_policy_changes": [],
        "vehicles_on_policy": [{"vin": "3VWFE21C04M000001", "date_added": "2023-06-01"}],
        "policy_status": "active",
        "lapse_history": [],
    },

    # POL-99-2211: Lapsed Dec 2025, reinstated Jan 2026 (25 days before loss) → Timing major
    "POL-99-2211": {
        "inception_date": "2024-01-10",
        "expiration_date": "2027-01-10",
        "days_since_inception": 814,
        "days_until_expiration": 281,
        "coverage_type": "comprehensive",
        "coverage_limits": {"liability": 500000.0, "collision": 30000.0, "medical": 50000.0},
        "premium_amount": 1350.0,
        "premium_payment_history": [
            {"date": "2026-01-10", "amount": 1350.0, "status": "paid"},
            {"date": "2026-04-10", "amount": 1350.0, "status": "paid"},
        ],
        "recent_policy_changes": [],
        "vehicles_on_policy": [{"vin": "5XYKT3A62DG143001", "date_added": "2024-01-10"}],
        "policy_status": "active",
        "lapse_history": [
            {"lapse_date": "2025-11-10", "reinstate_date": "2026-03-10"}  # 25 days before loss
        ],
    },

    # POL-300-8821: Long-standing, clean — only minor timing (Friday/Monday) for CLM-006
    "POL-300-8821": {
        "inception_date": "2024-07-01",
        "expiration_date": "2027-07-01",
        "days_since_inception": 296,
        "days_until_expiration": 435,
        "coverage_type": "collision",
        "coverage_limits": {"liability": 200000.0, "collision": 15000.0, "medical": 20000.0},
        "premium_amount": 750.0,
        "premium_payment_history": [
            {"date": "2026-01-01", "amount": 750.0, "status": "paid"},
            {"date": "2026-04-01", "amount": 750.0, "status": "paid"},
        ],
        "recent_policy_changes": [],
        "vehicles_on_policy": [{"vin": "1N4AL3AP4EC123456", "date_added": "2024-07-01"}],
        "policy_status": "active",
        "lapse_history": [],
    },

    # POL-88-4411: Coverage upgrade 68 hours before loss (CLM-007) → Timing major
    "POL-88-4411": {
        "inception_date": "2025-01-15",
        "expiration_date": "2027-01-15",
        "days_since_inception": 460,
        "days_until_expiration": 280,
        "coverage_type": "comprehensive",
        "coverage_limits": {"liability": 2000000.0, "collision": 100000.0, "medical": 200000.0},
        "premium_amount": 3200.0,
        "premium_payment_history": [
            {"date": "2026-01-15", "amount": 3200.0, "status": "paid"},
            {"date": "2026-04-15", "amount": 3200.0, "status": "paid"},
        ],
        "recent_policy_changes": [
            {
                "change_date": "2026-04-07",
                "change_type": "collision_coverage_upgrade",
                "details": "Fleet collision limit upgraded from $50K to $100K — 68 hours before loss on Apr 10",
            }
        ],
        "vehicles_on_policy": [{"vin": "1FTBW2CM4JKA12345", "date_added": "2025-01-15"}],
        "policy_status": "active",
        "lapse_history": [],
    },

    # POL-400-1122: Fully clean — CLM-008
    "POL-400-1122": {
        "inception_date": "2022-09-01",
        "expiration_date": "2027-09-01",
        "days_since_inception": 1330,
        "days_until_expiration": 861,
        "coverage_type": "collision",
        "coverage_limits": {"liability": 300000.0, "collision": 50000.0, "medical": 50000.0},
        "premium_amount": 1100.0,
        "premium_payment_history": [
            {"date": "2026-01-01", "amount": 1100.0, "status": "paid"},
            {"date": "2026-04-01", "amount": 1100.0, "status": "paid"},
        ],
        "recent_policy_changes": [],
        "vehicles_on_policy": [{"vin": "4T1BF1FK5GU123456", "date_added": "2022-09-01"}],
        "policy_status": "active",
        "lapse_history": [],
    },

    # POL-99-8844: New policy (18 days) + PRV-0093 again — CLM-009 timing + provider flags
    "POL-99-8844": {
        "inception_date": "2026-03-24",
        "expiration_date": "2027-03-24",
        "days_since_inception": 18,
        "days_until_expiration": 347,
        "coverage_type": "comprehensive",
        "coverage_limits": {"liability": 500000.0, "collision": 40000.0, "medical": 75000.0},
        "premium_amount": 1600.0,
        "premium_payment_history": [{"date": "2026-03-24", "amount": 1600.0, "status": "paid"}],
        "recent_policy_changes": [],
        "vehicles_on_policy": [{"vin": "WBA3A5C50DF000109", "date_added": "2026-03-24"}],
        "policy_status": "active",
        "lapse_history": [],
    },

    # POL-500-3310: Long-standing clean — CLM-010
    "POL-500-3310": {
        "inception_date": "2021-05-01",
        "expiration_date": "2027-05-01",
        "days_since_inception": 1087,
        "days_until_expiration": 373,
        "coverage_type": "collision",
        "coverage_limits": {"liability": 250000.0, "collision": 25000.0, "medical": 25000.0},
        "premium_amount": 850.0,
        "premium_payment_history": [
            {"date": "2026-01-01", "amount": 850.0, "status": "paid"},
            {"date": "2026-04-01", "amount": 850.0, "status": "paid"},
        ],
        "recent_policy_changes": [],
        "vehicles_on_policy": [{"vin": "1G1ZD5ST8JF100010", "date_added": "2021-05-01"}],
        "policy_status": "active",
        "lapse_history": [],
    },

    # POL-600-7721: 2-year policy, clean — CLM-011
    "POL-600-7721": {
        "inception_date": "2024-02-15",
        "expiration_date": "2027-02-15",
        "days_since_inception": 432,
        "days_until_expiration": 298,
        "coverage_type": "comprehensive",
        "coverage_limits": {"liability": 300000.0, "collision": 30000.0, "medical": 40000.0},
        "premium_amount": 1050.0,
        "premium_payment_history": [
            {"date": "2026-01-15", "amount": 1050.0, "status": "paid"},
            {"date": "2026-04-15", "amount": 1050.0, "status": "paid"},
        ],
        "recent_policy_changes": [],
        "vehicles_on_policy": [{"vin": "3FADP4BJ7BM100011", "date_added": "2024-02-15"}],
        "policy_status": "active",
        "lapse_history": [],
    },

    # POL-99-0012: New policy (19 days) + medical ring link — CLM-012 timing + provider flags
    "POL-99-0012": {
        "inception_date": "2026-03-23",
        "expiration_date": "2027-03-23",
        "days_since_inception": 19,
        "days_until_expiration": 346,
        "coverage_type": "comprehensive",
        "coverage_limits": {"liability": 750000.0, "collision": 45000.0, "medical": 150000.0},
        "premium_amount": 1950.0,
        "premium_payment_history": [{"date": "2026-03-23", "amount": 1950.0, "status": "paid"}],
        "recent_policy_changes": [
            {
                "change_date": "2026-03-26",
                "change_type": "medical_coverage_upgrade",
                "details": "Medical limit raised from $50K to $150K — 10 days before loss",
            }
        ],
        "vehicles_on_policy": [{"vin": "5J8TB3H56GL100012", "date_added": "2026-03-23"}],
        "policy_status": "active",
        "lapse_history": [],
    },
}


# ── Provider ──────────────────────────────────────────────────────────────────

class MockEnrichmentProvider(IEnrichmentProvider):
    """
    Returns claim-specific enrichment data designed to trigger spec-defined
    fraud pattern thresholds. Replace with real API clients in production
    (swap in container.py — no other changes needed).
    """

    async def get_claimant_history(self, claimant_id: str) -> Dict[str, Any]:
        data = _CLAIMANT_HISTORY.get(claimant_id, {})
        return {
            "claimant_id": claimant_id,
            "total_prior_claims": data.get("total_prior_claims", 0),
            "prior_fraud_flags":  data.get("prior_fraud_flags", 0),
            "claim_frequency_per_year": data.get("claim_frequency_per_year", 0.0),
            "total_prior_payouts": data.get("total_prior_payouts", 0.0),
            "prior_claims":        data.get("prior_claims", []),
            "known_addresses":     data.get("known_addresses", []),
            "associated_vehicles": data.get("associated_vehicles", []),
            "associated_policies": data.get("associated_policies", []),
        }

    async def get_provider_network(self, provider_id: str, provider_type: str) -> Dict[str, Any]:
        data = _PROVIDER_NETWORK.get(provider_id, {})
        return {
            "provider_id":   provider_id,
            "provider_type": provider_type,
            "provider_name": data.get("provider_name", f"Provider {provider_id}"),
            "license_status": data.get("license_status", "active"),
            "total_claims_served":    data.get("total_claims_served", 0),
            "average_billing_amount": data.get("average_billing_amount", 5000.0),
            "regional_average_billing": data.get("regional_average_billing", 5000.0),
            "billing_ratio":          data.get("billing_ratio", 1.0),
            "flagged_claims_count":   data.get("flagged_claims_count", 0),
            "geographic_service_area": data.get("geographic_service_area", "Local Metro"),
            "claims_outside_service_area": data.get("claims_outside_service_area", 0),
            "referral_connections":   data.get("referral_connections", []),
        }

    async def get_vehicle_valuation(self, vin: str, year: int, make: str, model: str) -> Dict[str, Any]:
        # Use VIN-specific market value if defined, else estimate by year
        market_value = _VIN_MARKET_VALUES.get(
            vin,
            round(max(8000.0, (2026 - year) * -2500 + 45000), 2)
        )
        has_prior_claim = vin in {"1HGCM82633A004352"}  # CLM-001/002 VIN reused

        return {
            "vin":   vin,
            "year":  year,
            "make":  make,
            "model": model,
            "market_value":         market_value,
            "salvage_value":        round(market_value * 0.25, 2),
            "total_loss_threshold": round(market_value * 0.75, 2),
            "regional_repair_benchmarks": {
                "minor_collision": {"low": 1500.0, "median": 4200.0,  "high": 8500.0},
                "major_collision": {"low": 8000.0, "median": 15000.0, "high": 28000.0},
                "comprehensive":   {"low": 5000.0, "median": 12000.0, "high": 25000.0},
            },
            "prior_claims_on_vin": [
                {"claim_id": "CLM-2025-088", "date": "2025-09-14", "amount": 41000.0}
            ] if has_prior_claim else [],
            "title_history": ["clean", "salvage", "rebuilt"] if has_prior_claim else ["clean"],
        }

    async def get_policy_details(self, policy_number: str) -> Dict[str, Any]:
        data = _POLICY_DETAILS.get(policy_number, {})
        return {
            "policy_number":   policy_number,
            "inception_date":  data.get("inception_date", "2023-01-01"),
            "expiration_date": data.get("expiration_date", "2027-01-01"),
            "days_since_inception":  data.get("days_since_inception", 999),
            "days_until_expiration": data.get("days_until_expiration", 999),
            "coverage_type":   data.get("coverage_type", "collision"),
            "coverage_limits": data.get("coverage_limits", {}),
            "premium_amount":  data.get("premium_amount", 1000.0),
            "premium_payment_history": data.get("premium_payment_history", []),
            "recent_policy_changes":  data.get("recent_policy_changes", []),
            "vehicles_on_policy":     data.get("vehicles_on_policy", []),
            "policy_status":          data.get("policy_status", "active"),
            "lapse_history":          data.get("lapse_history", []),
        }
