"""
Settings — Environment Configuration
======================================
Single source of truth for all configuration values.
Load order: .env file → environment variables → defaults below.

To switch models, change default_model here (or set FRAUD_DEFAULT_MODEL env var).
To swap to real Gemini API, set GEMINI_API_KEY in .env.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # LLM models
    default_model:       str = os.getenv("FRAUD_DEFAULT_MODEL", "gemini-2.5-pro")
    orchestrator_model:  str = os.getenv("FRAUD_ORCHESTRATOR_MODEL", "gemini-2.5-pro")
    enrichment_model:    str = os.getenv("FRAUD_ENRICHMENT_MODEL", "gemini-2.5-flash")
    analyzer_model:      str = os.getenv("FRAUD_ANALYZER_MODEL", "gemini-2.5-pro")
    report_model:        str = os.getenv("FRAUD_REPORT_MODEL", "gemini-2.5-flash")

    # API keys
    gemini_api_key:  str = os.getenv("GEMINI_API_KEY", "")
    arize_space_id:  str = os.getenv("ARIZE_SPACE_ID", "")
    arize_api_key:   str = os.getenv("ARIZE_API_KEY", "")

    # A2A service ports
    orchestrator_port: int = int(os.getenv("ORCHESTRATOR_PORT", "8001"))
    enrichment_port:   int = int(os.getenv("ENRICHMENT_PORT", "8002"))
    analyzer_port:     int = int(os.getenv("ANALYZER_PORT", "8003"))
    report_port:       int = int(os.getenv("REPORT_PORT", "8004"))

    # Pipeline thresholds
    report_score_threshold: float = float(os.getenv("REPORT_SCORE_THRESHOLD", "40.0"))
    high_tier_threshold:    float = float(os.getenv("HIGH_TIER_THRESHOLD", "60.0"))
    critical_tier_threshold: float = float(os.getenv("CRITICAL_TIER_THRESHOLD", "80.0"))


settings = Settings()

