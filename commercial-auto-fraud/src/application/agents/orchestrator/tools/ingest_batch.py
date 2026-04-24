"""
Tool 1: ingest_claim_batch
Validates N claims from a batch JSON against Pydantic schemas.
"""

import json
from datetime import date, datetime
from typing import Any, Dict, List
from pydantic import ValidationError
from src.infrastructure.tools.base_tool import BaseTool
from src.application.agents.orchestrator.schemas import BatchIngestionOutput


class _ClaimValidator:
    """Internal schema-based validator for a single raw claim dict."""

    REQUIRED = ["claim_id", "claimant", "provider", "vehicle",
                "policy_number", "claimed_amount", "loss_date"]

    @classmethod
    def validate(cls, claim: dict, idx: int) -> List[str]:
        errors = []
        for f in cls.REQUIRED:
            if f not in claim or claim[f] is None:
                errors.append(f"Missing required field: '{f}'")

        amount = claim.get("claimed_amount")
        if amount is not None:
            try:
                if float(amount) <= 0:
                    errors.append(f"claimed_amount must be > 0, got {amount}")
            except (TypeError, ValueError):
                errors.append(f"claimed_amount must be numeric, got '{amount}'")

        loss_str = claim.get("loss_date", "")
        if loss_str:
            try:
                parsed = datetime.strptime(loss_str, "%Y-%m-%d").date()
                if parsed > date.today():
                    errors.append(f"loss_date '{loss_str}' is in the future")
            except ValueError:
                errors.append(f"loss_date '{loss_str}' must be YYYY-MM-DD")
        else:
            errors.append("loss_date is empty")

        claimant = claim.get("claimant", {})
        if not isinstance(claimant, dict) or not claimant.get("id") or not claimant.get("name"):
            errors.append("claimant must have 'id' and 'name'")

        vehicle = claim.get("vehicle", {})
        if not isinstance(vehicle, dict) or not vehicle.get("vin"):
            errors.append("vehicle must have a 'vin'")

        provider = claim.get("provider", {})
        if not isinstance(provider, dict) or not provider.get("id"):
            errors.append("provider must have an 'id'")

        return errors


class IngestBatchTool(BaseTool):
    name = "ingest_claim_batch"
    description = (
        "Parses a JSON string containing a batch of commercial auto claims. "
        "Validates each claim for required fields (claim_id, claimant.id, claimant.name, "
        "provider.id, vehicle.vin, policy_number, claimed_amount > 0, loss_date YYYY-MM-DD). "
        "Returns valid_claims list and invalid_claims list with per-claim error detail."
    )

    async def execute(self, batch_json: str) -> dict:
        try:
            raw = json.loads(batch_json)
        except json.JSONDecodeError as e:
            return BatchIngestionOutput(
                batch_id="unknown", batch_name="Unknown",
                total_claims=0, valid_claims=[],
                invalid_claims=[],
                validation_summary=f"❌ Invalid JSON: {e}",
            ).model_dump()

        batch_id   = raw.get("batch_id", "batch_unknown")
        batch_name = raw.get("batch_name", "Weekly Auto Claims")
        claims     = raw.get("claims", [])

        valid, invalid = [], []
        for idx, claim in enumerate(claims):
            errs = _ClaimValidator.validate(claim, idx)
            if errs:
                invalid.append({"claim_id": claim.get("claim_id", f"CLAIM_{idx}"),
                                 "errors": errs})
            else:
                valid.append(claim)

        summary = (
            f"Batch '{batch_id}': {len(claims)} claims received — "
            f"{len(valid)} valid, {len(invalid)} invalid."
            + (" Invalid claims skipped." if invalid else "")
        )
        return BatchIngestionOutput(
            batch_id=batch_id, batch_name=batch_name,
            total_claims=len(claims), valid_claims=valid,
            invalid_claims=invalid, validation_summary=summary,
        ).model_dump()


