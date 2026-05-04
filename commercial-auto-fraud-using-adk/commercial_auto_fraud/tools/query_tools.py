"""
Query Tools — Used by the SIU Chat Agent to access batch state and claims.
"""

import json
from typing import Dict, Any
from google.adk.tools import ToolContext
import redis

# Use an env var for redis, default to localhost
REDIS_URL = "redis://localhost:6379/0"

def get_redis_client():
    return redis.Redis.from_url(REDIS_URL, decode_responses=True)

async def read_batch_results(batch_id: str, tool_context: ToolContext) -> str:
    """
    Retrieves the aggregated batch summary from Redis.
    Contains statistics, tier distribution, and rankings.
    """
    r = get_redis_client()
    data = r.get(f"batch:{batch_id}:summary")
    if data:
        return data
    return json.dumps({"error": f"Batch {batch_id} not found."})

async def get_claim_detail(claim_id: str, tool_context: ToolContext) -> str:
    """
    Retrieves the full, detailed results (enrichment + fraud analysis) 
    for a specific claim from Redis.
    """
    r = get_redis_client()
    data = r.get(f"claim:{claim_id}:result")
    if data:
        return data
    return json.dumps({"error": f"Claim {claim_id} not found."})
