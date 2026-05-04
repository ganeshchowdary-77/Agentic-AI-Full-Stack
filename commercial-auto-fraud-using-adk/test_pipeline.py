"""
Test script for the Commercial Auto Fraud Detection Pipeline
Run this after starting the services with: python main.py
"""

import asyncio
import json
import httpx
from pathlib import Path


async def test_batch_submission():
    """Test submitting a batch and getting results."""
    
    print("🔍 Commercial Auto Fraud Detection - Pipeline Test\n")
    print("=" * 60)
    
    # Load the sample batch
    batch_file = Path("weekly_auto_claims.json")
    if not batch_file.exists():
        print("❌ Error: weekly_auto_claims.json not found")
        return
    
    with open(batch_file, "r") as f:
        batch_data = json.load(f)
    
    print(f"📄 Loaded batch: {batch_data['batch_id']}")
    print(f"📊 Total claims: {len(batch_data['claims'])}\n")
    
    # Submit the batch
    print("🚀 Submitting batch to fraud detection pipeline...")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            response = await client.post(
                "http://localhost:8001/api/fraud-detection/batch",
                json=batch_data
            )
            
            if response.status_code != 200:
                print(f"❌ Error: {response.status_code} - {response.text}")
                return
            
            result = response.json()
            
            if result["status"] == "complete":
                print("✅ Batch processing complete!\n")
                print_summary(result["summary"])
                
                # Fetch full results
                batch_id = result["batch_id"]
                print(f"\n📥 Fetching detailed results for batch {batch_id}...")
                
                results_response = await client.get(
                    f"http://localhost:8001/api/batch/{batch_id}/results"
                )
                
                if results_response.status_code == 200:
                    full_results = results_response.json()
                    print_detailed_results(full_results)
                else:
                    print(f"⚠️  Could not fetch detailed results: {results_response.status_code}")
            
            else:
                print(f"❌ Processing failed: {result.get('error', 'Unknown error')}")
        
        except httpx.ConnectError:
            print("❌ Error: Could not connect to the API server.")
            print("   Make sure the services are running with: python main.py")
        except Exception as e:
            print(f"❌ Error: {str(e)}")


def print_summary(summary):
    """Print batch summary statistics."""
    print("📊 BATCH SUMMARY")
    print("-" * 60)
    print(f"Total Claims:      {summary['total_claims']}")
    print(f"Processed:         {summary['processed_claims']}")
    print(f"Failed:            {summary['failed_claims']}")
    print(f"Processing Time:   {summary['processing_time_ms'] / 1000:.2f}s")
    print("\n🎯 PRIORITY TIER DISTRIBUTION")
    print("-" * 60)
    
    tier_dist = summary['tier_distribution']
    print(f"🔴 Critical:       {tier_dist.get('critical', 0)}")
    print(f"🟠 High:           {tier_dist.get('high', 0)}")
    print(f"🟡 Medium:         {tier_dist.get('medium', 0)}")
    print(f"🟢 Low:            {tier_dist.get('low', 0)}")


def print_detailed_results(results):
    """Print detailed claim results."""
    print("\n📋 DETAILED CLAIM RESULTS")
    print("=" * 60)
    
    claims = results.get("results", [])
    
    # Sort by composite score (highest first)
    claims_sorted = sorted(claims, key=lambda x: x["composite_score"], reverse=True)
    
    for claim in claims_sorted:
        tier_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢"
        }.get(claim["priority_tier"], "⚪")
        
        print(f"\n{tier_emoji} {claim['claim_id']} - {claim['claimant_name']}")
        print(f"   Amount: ${claim['claimed_amount']:,.2f}")
        print(f"   Fraud Score: {claim['composite_score']:.1f}/100")
        print(f"   Priority: {claim['priority_tier'].upper()}")
        print(f"   Confidence: {claim['confidence']}")
        print(f"   Patterns Flagged: {claim['patterns_flagged']}")
        if claim['top_pattern']:
            print(f"   Top Pattern: {claim['top_pattern']} ({claim['top_pattern_score']:.1f})")
        print(f"   Report Generated: {'✅ Yes' if claim['has_report'] else '❌ No'}")
        print(f"   Processing Time: {claim['processing_time_ms']:.0f}ms")
    
    print("\n" + "=" * 60)
    print("✅ Test completed successfully!")
    print("\n💡 Next steps:")
    print("   1. Open http://localhost:8001/dashboard to view the web UI")
    print("   2. Check artifacts/reports/ for generated investigation reports")
    print("   3. Try the SIU chat API to query results")


async def test_siu_chat():
    """Test the SIU chat interface."""
    print("\n\n🤖 Testing SIU Chat Interface...")
    print("=" * 60)
    
    queries = [
        "How many claims were flagged as critical priority?",
        "Which provider appears most frequently in high-risk claims?",
        "Show me claims with duplicate pattern scores above 50"
    ]
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for query in queries:
            print(f"\n❓ Query: {query}")
            try:
                response = await client.post(
                    "http://localhost:8001/api/siu/chat",
                    json={"query": query, "batch_id": "batch_2026_w16"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"💬 Response: {result.get('response', 'No response')}")
                else:
                    print(f"⚠️  Error: {response.status_code}")
            except Exception as e:
                print(f"⚠️  Error: {str(e)}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  COMMERCIAL AUTO FRAUD DETECTION - PIPELINE TEST")
    print("=" * 60 + "\n")
    
    asyncio.run(test_batch_submission())
    
    # Uncomment to test SIU chat
    # asyncio.run(test_siu_chat())
