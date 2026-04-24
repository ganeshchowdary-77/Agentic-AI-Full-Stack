"""
User Profile Store
===================
JSON file-backed SIU investigator profile persistence.
One file per investigator at fraud_data_store/user_profiles/{user_id}.json.

Spec § 12.5 — Implements:
  - get_or_create(user_id)     — loads or initializes a new profile
  - save_profile(user_id, ...)  — persists with last_interaction timestamp
  - get_profile(user_id)        — load existing profile (None if not found)
  - increment_session(user_id)  — call at session start; tracks session_count
  - mark_profiling_complete()   — called after all 4 onboarding Q&A questions answered

Design: JSON files over SQLite eliminates DB setup while demonstrating profile
persistence across sessions. Production would swap this for a database repository
by implementing the same interface with a different storage backend.

Profile attributes (spec § 12.2):
  user_id             — unique identifier
  name                — first name for greetings
  experience_level    — "junior" | "mid" | "senior"  (from Q1)
  specialization      — "staged_accidents" | "provider_fraud" | "billing_inflation" | "general" (Q2)
  preferred_output_mode — "full_report" | "exceptions_only" | "evidence_summary" (Q3)
  preferred_detail_level — "verbose" | "concise" (Q4)
  profiling_complete  — True after all 4 questions answered
  session_count       — incremented each session
  last_interaction    — ISO timestamp updated on save
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional


# Aliases for backward compatibility with siu_query_service.py
_EXPERIENCE_MAP = {
    "junior":  "junior",
    "mid":     "junior",   # treat mid as junior for response formatting
    "senior":  "senior",
    "unknown": "junior",   # default to verbose for unknown profiles
}


class UserProfileStore:
    """
    JSON file-backed profile store.
    Swap the implementation (not the interface) for database-backed production use.
    """

    def __init__(self, profiles_dir: str = None):
        if profiles_dir is None:
            # Default: fraud_data_store/user_profiles/ relative to project root
            here = os.path.dirname(__file__)
            profiles_dir = os.path.normpath(
                os.path.join(here, "..", "..", "..", "..", "fraud_data_store", "user_profiles")
            )
        self.profiles_dir = profiles_dir
        os.makedirs(profiles_dir, exist_ok=True)

    def _path(self, user_id: str) -> str:
        return os.path.join(self.profiles_dir, f"{user_id}.json")

    def get_profile(self, user_id: str) -> Optional[dict]:
        """Load profile by user_id. Returns None if not found."""
        path = self._path(user_id)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return None

    def save_profile(self, user_id: str, profile: dict) -> dict:
        """Persist profile, updating last_interaction to now."""
        profile["last_interaction"] = datetime.now(timezone.utc).isoformat()
        profile.setdefault("user_id", user_id)
        with open(self._path(user_id), "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2)
        return profile

    def get_or_create(self, user_id: str) -> dict:
        """
        Load existing profile or initialize a blank one for a new investigator.
        New profiles have profiling_complete=False — triggers onboarding Q&A flow.
        """
        profile = self.get_profile(user_id)
        if profile:
            return profile
        # Default profile for a new investigator (spec § 12.5)
        profile = {
            "user_id":               user_id,
            "name":                  "",
            "role":                  "SIU Investigator",
            "experience":            "junior",        # backward compat with siu_query_service
            "experience_level":      "unknown",       # set by Q1
            "specialization":        "general",       # set by Q2
            "preferred_output_mode": "full_report",   # set by Q3
            "preferred_detail_level": "verbose",      # set by Q4
            "profiling_complete":    False,
            "session_count":         0,
            "response_style": {
                "use_definitions":    True,
                "include_next_steps": True,
                "use_examples":       True,
                "verbose_evidence":   True,
                "explain_scores":     True,
                "threshold_filter":   0,
            },
        }
        return self.save_profile(user_id, profile)

    def increment_session(self, user_id: str) -> dict:
        """Increment session_count at the start of each interaction."""
        profile = self.get_or_create(user_id)
        profile["session_count"] = profile.get("session_count", 0) + 1
        return self.save_profile(user_id, profile)

    def update_from_onboarding(self, user_id: str, answers: dict) -> dict:
        """
        Called after the 4 onboarding Q&A questions complete (spec § 12.3).
        answers = {
          "name":                  "Kevin Park",
          "experience_level":      "junior",      # from Q1
          "specialization":        "general",     # from Q2
          "preferred_output_mode": "full_report", # from Q3
          "preferred_detail_level": "verbose",    # from Q4
        }
        """
        profile = self.get_or_create(user_id)
        profile.update(answers)
        # Keep backward-compat 'experience' key in sync
        profile["experience"] = _EXPERIENCE_MAP.get(
            answers.get("experience_level", "unknown"), "junior"
        )
        # Update response_style from detail preferences
        is_verbose = answers.get("preferred_detail_level", "verbose") == "verbose"
        profile["response_style"].update({
            "use_definitions":    is_verbose,
            "include_next_steps": is_verbose,
            "verbose_evidence":   is_verbose,
            "explain_scores":     is_verbose,
            "threshold_filter":   0 if is_verbose else 60,
        })
        profile["profiling_complete"] = True
        return self.save_profile(user_id, profile)

    def needs_onboarding(self, user_id: str) -> bool:
        """True if this investigator has never completed the 4 profiling questions."""
        profile = self.get_profile(user_id)
        if not profile:
            return True
        return not profile.get("profiling_complete", False)


# Module-level singleton — import this in siu_query_service and web/app.py
profile_store = UserProfileStore()
