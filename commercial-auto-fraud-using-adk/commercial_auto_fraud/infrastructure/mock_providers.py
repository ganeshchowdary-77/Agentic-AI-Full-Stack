"""
Mock Domain Providers
Simulates external system data for all 12 claims in weekly_auto_claims.json.
"""

CLAIMANTS = {
    "C-4821": {
        "claimant_id": "C-4821", "total_prior_claims": 5, "prior_fraud_flags": 2,
        "claim_frequency_per_year": 3.3, "total_prior_payouts": 127000.0,
        "known_addresses": ["1420 W Division St, Chicago, IL"],
        "associated_vehicles": [{"vin": "1HGCM82633A004352", "year": 2022, "make": "Honda", "model": "Accord"}],
        "associated_policies": ["POL-99-1234", "POL-99-5678"],
        "prior_claims": [
            {"claim_id": "CLM-2025-801", "loss_date": "2025-11-03", "loss_type": "major_collision", "claimed_amount": 31000, "outcome": "paid", "fraud_flag": True},
            {"claim_id": "CLM-2025-422", "loss_date": "2025-07-18", "loss_type": "major_collision", "claimed_amount": 28000, "outcome": "paid", "fraud_flag": True},
            {"claim_id": "CLM-2025-110", "loss_date": "2025-02-05", "loss_type": "minor_collision", "claimed_amount": 9500, "outcome": "paid", "fraud_flag": False},
            {"claim_id": "CLM-2024-990", "loss_date": "2024-12-20", "loss_type": "comprehensive", "claimed_amount": 35000, "outcome": "denied", "fraud_flag": False},
            {"claim_id": "CLM-2024-601", "loss_date": "2024-08-14", "loss_type": "major_collision", "claimed_amount": 23500, "outcome": "paid", "fraud_flag": False},
        ],
    },
    "C-5502": {
        "claimant_id": "C-5502", "total_prior_claims": 3, "prior_fraud_flags": 0,
        "claim_frequency_per_year": 1.5, "total_prior_payouts": 18000.0,
        "known_addresses": ["890 Lake Shore Dr, Chicago, IL"],
        "associated_vehicles": [{"vin": "2T1BR32E61C002711", "year": 2019, "make": "Toyota", "model": "Camry"}],
        "associated_policies": ["POL-99-7890"],
        "prior_claims": [
            {"claim_id": "CLM-2025-300", "loss_date": "2025-06-10", "loss_type": "minor_collision", "claimed_amount": 6000, "outcome": "paid", "fraud_flag": False},
        ],
    },
    "C-201": {
        "claimant_id": "C-201", "total_prior_claims": 1, "prior_fraud_flags": 0,
        "claim_frequency_per_year": 0.3, "total_prior_payouts": 3200.0,
        "known_addresses": ["234 Elm St, Naperville, IL"],
        "associated_vehicles": [{"vin": "3VWFE21C04M000001", "year": 2021, "make": "Volkswagen", "model": "Jetta"}],
        "associated_policies": ["POL-200-4432"],
        "prior_claims": [],
    },
    "C-103": {
        "claimant_id": "C-103", "total_prior_claims": 4, "prior_fraud_flags": 1,
        "claim_frequency_per_year": 2.0, "total_prior_payouts": 67000.0,
        "known_addresses": ["567 Oak Ave, Evanston, IL"],
        "associated_vehicles": [{"vin": "5XYKT3A62DG143001", "year": 2020, "make": "Kia", "model": "Sorento"}],
        "associated_policies": ["POL-99-2211"],
        "prior_claims": [
            {"claim_id": "CLM-2025-200", "loss_date": "2025-05-20", "loss_type": "major_collision", "claimed_amount": 22000, "outcome": "paid", "fraud_flag": True},
        ],
    },
    "C-104": {
        "claimant_id": "C-104", "total_prior_claims": 0, "prior_fraud_flags": 0,
        "claim_frequency_per_year": 0.0, "total_prior_payouts": 0.0,
        "known_addresses": ["789 Pine Rd, Schaumburg, IL"],
        "associated_vehicles": [{"vin": "1N4AL3AP4EC123456", "year": 2023, "make": "Nissan", "model": "Altima"}],
        "associated_policies": ["POL-300-8821"],
        "prior_claims": [],
    },
    "C-601": {
        "claimant_id": "C-601", "total_prior_claims": 2, "prior_fraud_flags": 0,
        "claim_frequency_per_year": 1.0, "total_prior_payouts": 24000.0,
        "known_addresses": ["1200 Industrial Blvd, Joliet, IL"],
        "associated_vehicles": [{"vin": "1FTBW2CM4JKA12345", "year": 2018, "make": "Ford", "model": "Transit"}],
        "associated_policies": ["POL-88-4411"],
        "prior_claims": [],
    },
    "C-701": {
        "claimant_id": "C-701", "total_prior_claims": 0, "prior_fraud_flags": 0,
        "claim_frequency_per_year": 0.0, "total_prior_payouts": 0.0,
        "known_addresses": ["456 Maple Dr, Aurora, IL"],
        "associated_vehicles": [{"vin": "4T1BF1FK5GU123456", "year": 2024, "make": "Toyota", "model": "Camry"}],
        "associated_policies": ["POL-400-1122"],
        "prior_claims": [],
    },
    "C-802": {
        "claimant_id": "C-802", "total_prior_claims": 1, "prior_fraud_flags": 0,
        "claim_frequency_per_year": 0.5, "total_prior_payouts": 8500.0,
        "known_addresses": ["321 Birch Ln, Skokie, IL"],
        "associated_vehicles": [{"vin": "WBA3A5C50DF000109", "year": 2020, "make": "BMW", "model": "3 Series"}],
        "associated_policies": ["POL-99-8844"],
        "prior_claims": [],
    },
    "C-901": {
        "claimant_id": "C-901", "total_prior_claims": 0, "prior_fraud_flags": 0,
        "claim_frequency_per_year": 0.0, "total_prior_payouts": 0.0,
        "known_addresses": ["100 Cedar Ct, Wheaton, IL"],
        "associated_vehicles": [{"vin": "1G1ZD5ST8JF100010", "year": 2021, "make": "Chevrolet", "model": "Malibu"}],
        "associated_policies": ["POL-500-3310"],
        "prior_claims": [],
    },
    "C-902": {
        "claimant_id": "C-902", "total_prior_claims": 1, "prior_fraud_flags": 0,
        "claim_frequency_per_year": 0.5, "total_prior_payouts": 5200.0,
        "known_addresses": ["88 Willow Way, Bolingbrook, IL"],
        "associated_vehicles": [{"vin": "3FADP4BJ7BM100011", "year": 2022, "make": "Ford", "model": "Fusion"}],
        "associated_policies": ["POL-600-7721"],
        "prior_claims": [],
    },
    "C-903": {
        "claimant_id": "C-903", "total_prior_claims": 1, "prior_fraud_flags": 0,
        "claim_frequency_per_year": 0.5, "total_prior_payouts": 4800.0,
        "known_addresses": ["55 Spruce St, Downers Grove, IL"],
        "associated_vehicles": [{"vin": "5J8TB3H56GL100012", "year": 2023, "make": "Acura", "model": "RDX"}],
        "associated_policies": ["POL-99-0012"],
        "prior_claims": [],
    },
}

PROVIDERS = {
    "PRV-0093": {
        "provider_id": "PRV-0093", "provider_name": "FastFix Auto Body", "provider_type": "repair_shop",
        "license_status": "active", "total_claims_served": 187, "average_billing_amount": 32000.0,
        "regional_average_billing": 12500.0, "billing_ratio": 2.56, "network_risk": "HIGH",
        "geographic_service_area": "Chicago Metro", "claims_outside_service_area": 3, "flagged_claims_count": 47,
        "referral_connections": [
            {"provider_id": "PRV-0800", "provider_name": "Metro Towing LLC", "shared_claims": 23},
        ],
    },
    "PRV-0200": {
        "provider_id": "PRV-0200", "provider_name": "QuickMed Injury Clinic", "provider_type": "medical",
        "license_status": "under_investigation", "total_claims_served": 312, "average_billing_amount": 45000.0,
        "regional_average_billing": 11000.0, "billing_ratio": 4.09, "network_risk": "CRITICAL",
        "geographic_service_area": "Chicago Metro", "claims_outside_service_area": 8, "flagged_claims_count": 89,
        "referral_connections": [
            {"provider_id": "PRV-0093", "provider_name": "FastFix Auto Body", "shared_claims": 15},
        ],
    },
    "PRV-0301": {
        "provider_id": "PRV-0301", "provider_name": "Naperville Auto Care", "provider_type": "repair_shop",
        "license_status": "active", "total_claims_served": 45, "average_billing_amount": 7800.0,
        "regional_average_billing": 7200.0, "billing_ratio": 1.08, "network_risk": "LOW",
        "geographic_service_area": "DuPage County", "claims_outside_service_area": 0, "flagged_claims_count": 2,
        "referral_connections": [],
    },
    "PRV-0400": {
        "provider_id": "PRV-0400", "provider_name": "Joliet Fleet Repair", "provider_type": "repair_shop",
        "license_status": "active", "total_claims_served": 78, "average_billing_amount": 18000.0,
        "regional_average_billing": 10000.0, "billing_ratio": 1.80, "network_risk": "MEDIUM",
        "geographic_service_area": "Will County", "claims_outside_service_area": 1, "flagged_claims_count": 5,
        "referral_connections": [],
    },
    "PRV-0500": {
        "provider_id": "PRV-0500", "provider_name": "Aurora Body Works", "provider_type": "repair_shop",
        "license_status": "active", "total_claims_served": 32, "average_billing_amount": 6500.0,
        "regional_average_billing": 7200.0, "billing_ratio": 0.90, "network_risk": "LOW",
        "geographic_service_area": "Kane County", "claims_outside_service_area": 0, "flagged_claims_count": 0,
        "referral_connections": [],
    },
    "PRV-0600": {
        "provider_id": "PRV-0600", "provider_name": "Wheaton Collision Center", "provider_type": "repair_shop",
        "license_status": "active", "total_claims_served": 28, "average_billing_amount": 5800.0,
        "regional_average_billing": 7200.0, "billing_ratio": 0.81, "network_risk": "LOW",
        "geographic_service_area": "DuPage County", "claims_outside_service_area": 0, "flagged_claims_count": 0,
        "referral_connections": [],
    },
    "PRV-0700": {
        "provider_id": "PRV-0700", "provider_name": "Bolingbrook Auto Repair", "provider_type": "repair_shop",
        "license_status": "active", "total_claims_served": 41, "average_billing_amount": 9200.0,
        "regional_average_billing": 7200.0, "billing_ratio": 1.28, "network_risk": "LOW",
        "geographic_service_area": "Will County", "claims_outside_service_area": 0, "flagged_claims_count": 1,
        "referral_connections": [],
    },
}

VEHICLES = {
    "1HGCM82633A004352": {"vin": "1HGCM82633A004352", "market_value": 29500.0, "salvage_value": 7375.0, "prior_total_loss": True, "title_history": ["clean", "rebuilt"], "prior_claims_on_vin": [{"claim_id": "CLM-2025-801", "date": "2025-11-03", "amount": 31000}]},
    "2T1BR32E61C002711": {"vin": "2T1BR32E61C002711", "market_value": 18000.0, "salvage_value": 4500.0, "prior_total_loss": False, "title_history": ["clean"], "prior_claims_on_vin": []},
    "3VWFE21C04M000001": {"vin": "3VWFE21C04M000001", "market_value": 22000.0, "salvage_value": 5500.0, "prior_total_loss": False, "title_history": ["clean"], "prior_claims_on_vin": []},
    "5XYKT3A62DG143001": {"vin": "5XYKT3A62DG143001", "market_value": 21000.0, "salvage_value": 5250.0, "prior_total_loss": False, "title_history": ["clean"], "prior_claims_on_vin": []},
    "1N4AL3AP4EC123456": {"vin": "1N4AL3AP4EC123456", "market_value": 28000.0, "salvage_value": 7000.0, "prior_total_loss": False, "title_history": ["clean"], "prior_claims_on_vin": []},
    "1FTBW2CM4JKA12345": {"vin": "1FTBW2CM4JKA12345", "market_value": 32000.0, "salvage_value": 8000.0, "prior_total_loss": False, "title_history": ["clean"], "prior_claims_on_vin": []},
    "4T1BF1FK5GU123456": {"vin": "4T1BF1FK5GU123456", "market_value": 30000.0, "salvage_value": 7500.0, "prior_total_loss": False, "title_history": ["clean"], "prior_claims_on_vin": []},
    "WBA3A5C50DF000109": {"vin": "WBA3A5C50DF000109", "market_value": 35000.0, "salvage_value": 8750.0, "prior_total_loss": False, "title_history": ["clean"], "prior_claims_on_vin": []},
    "1G1ZD5ST8JF100010": {"vin": "1G1ZD5ST8JF100010", "market_value": 23000.0, "salvage_value": 5750.0, "prior_total_loss": False, "title_history": ["clean"], "prior_claims_on_vin": []},
    "3FADP4BJ7BM100011": {"vin": "3FADP4BJ7BM100011", "market_value": 21500.0, "salvage_value": 5375.0, "prior_total_loss": False, "title_history": ["clean"], "prior_claims_on_vin": []},
    "5J8TB3H56GL100012": {"vin": "5J8TB3H56GL100012", "market_value": 38000.0, "salvage_value": 9500.0, "prior_total_loss": False, "title_history": ["clean"], "prior_claims_on_vin": []},
}

POLICIES = {
    "POL-99-1234": {"policy_number": "POL-99-1234", "inception_date": "2026-04-06", "days_since_inception": 5, "coverage_type": "full", "premium_amount": 2400.0, "policy_status": "active", "recent_policy_changes": [{"change_date": "2026-04-05", "change_type": "increased_coverage_limit", "details": "Liability limit raised from $50K to $250K"}]},
    "POL-99-5678": {"policy_number": "POL-99-5678", "inception_date": "2026-04-06", "days_since_inception": 7, "coverage_type": "full", "premium_amount": 2200.0, "policy_status": "active", "recent_policy_changes": []},
    "POL-99-7890": {"policy_number": "POL-99-7890", "inception_date": "2026-03-08", "days_since_inception": 30, "coverage_type": "comprehensive", "premium_amount": 1800.0, "policy_status": "active", "recent_policy_changes": [{"change_date": "2026-03-25", "change_type": "added_additional_driver", "details": "Added driver with poor driving record"}]},
    "POL-200-4432": {"policy_number": "POL-200-4432", "inception_date": "2025-06-15", "days_since_inception": 299, "coverage_type": "basic", "premium_amount": 1200.0, "policy_status": "active", "recent_policy_changes": []},
    "POL-99-2211": {"policy_number": "POL-99-2211", "inception_date": "2025-10-01", "days_since_inception": 186, "coverage_type": "full", "premium_amount": 1600.0, "policy_status": "active", "recent_policy_changes": []},
    "POL-300-8821": {"policy_number": "POL-300-8821", "inception_date": "2025-01-15", "days_since_inception": 452, "coverage_type": "basic", "premium_amount": 900.0, "policy_status": "active", "recent_policy_changes": []},
    "POL-88-4411": {"policy_number": "POL-88-4411", "inception_date": "2025-11-21", "days_since_inception": 140, "coverage_type": "commercial_fleet", "premium_amount": 4800.0, "policy_status": "active", "recent_policy_changes": [{"change_date": "2026-04-07", "change_type": "added_comprehensive_coverage", "details": "Comprehensive coverage added 68 hours before reported loss"}]},
    "POL-400-1122": {"policy_number": "POL-400-1122", "inception_date": "2024-08-01", "days_since_inception": 631, "coverage_type": "full", "premium_amount": 1400.0, "policy_status": "active", "recent_policy_changes": []},
    "POL-99-8844": {"policy_number": "POL-99-8844", "inception_date": "2025-09-01", "days_since_inception": 216, "coverage_type": "full", "premium_amount": 2000.0, "policy_status": "active", "recent_policy_changes": []},
    "POL-500-3310": {"policy_number": "POL-500-3310", "inception_date": "2025-03-01", "days_since_inception": 399, "coverage_type": "basic", "premium_amount": 1100.0, "policy_status": "active", "recent_policy_changes": []},
    "POL-600-7721": {"policy_number": "POL-600-7721", "inception_date": "2025-05-01", "days_since_inception": 358, "coverage_type": "full", "premium_amount": 1500.0, "policy_status": "active", "recent_policy_changes": []},
    "POL-99-0012": {"policy_number": "POL-99-0012", "inception_date": "2025-12-01", "days_since_inception": 114, "coverage_type": "comprehensive", "premium_amount": 2600.0, "policy_status": "active", "recent_policy_changes": []},
}

# Regional repair benchmarks by loss type
REPAIR_BENCHMARKS = {
    "minor_collision": {"low": 1500.0, "median": 4500.0, "high": 8000.0},
    "major_collision": {"low": 8000.0, "median": 18000.0, "high": 35000.0},
    "comprehensive": {"low": 5000.0, "median": 15000.0, "high": 30000.0},
}


class MockEnrichmentProvider:
    """Mock external data provider for enrichment tools."""

    async def get_claimant_history(self, claimant_id: str) -> dict:
        default = {"claimant_id": claimant_id, "total_prior_claims": 0, "prior_fraud_flags": 0, "claim_frequency_per_year": 0.0, "total_prior_payouts": 0.0, "known_addresses": [], "associated_vehicles": [], "associated_policies": [], "prior_claims": []}
        return CLAIMANTS.get(claimant_id, default)

    async def get_provider_network(self, provider_id: str, provider_type: str) -> dict:
        default = {"provider_id": provider_id, "provider_name": f"Unknown Provider {provider_id}", "provider_type": provider_type, "license_status": "active", "total_claims_served": 0, "average_billing_amount": 0.0, "regional_average_billing": 7200.0, "billing_ratio": 1.0, "network_risk": "LOW", "geographic_service_area": "Unknown", "claims_outside_service_area": 0, "flagged_claims_count": 0, "referral_connections": []}
        return PROVIDERS.get(provider_id, default)

    async def get_vehicle_valuation(self, vin: str, year: int, make: str, model: str) -> dict:
        default = {"vin": vin, "market_value": 25000.0, "salvage_value": 6250.0, "prior_total_loss": False, "title_history": ["clean"], "prior_claims_on_vin": []}
        data = VEHICLES.get(vin, default)
        data["year"] = year
        data["make"] = make
        data["model"] = model
        data["total_loss_threshold"] = round(data["market_value"] * 0.75, 2)
        data["regional_repair_benchmarks"] = REPAIR_BENCHMARKS
        return data

    async def get_policy_details(self, policy_number: str) -> dict:
        default = {"policy_number": policy_number, "inception_date": "2025-01-01", "days_since_inception": 365, "coverage_type": "basic", "premium_amount": 1200.0, "policy_status": "active", "recent_policy_changes": []}
        return POLICIES.get(policy_number, default)


provider = MockEnrichmentProvider()
