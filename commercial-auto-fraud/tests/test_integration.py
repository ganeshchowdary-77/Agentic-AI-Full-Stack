import asyncio
import json
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.container import Container
from src.presentation.a2a.server_enrichment import start_server as start_enrichment
from src.presentation.a2a.server_analyzer import start_server as start_analyzer
from src.presentation.a2a.server_report import start_server as start_report

async def test_pipeline():
    container = Container()
    
    with open("weekly_auto_claims.json", "r") as f:
        batch_json = f.read()
        
    print("Testing pipeline with full A2A...")
    
    summary = await container.orchestrator.process_claim_batch(batch_json)
    print("\nPIPELINE RESULT:")
    print(summary)

if __name__ == "__main__":
    threading.Thread(target=start_enrichment, daemon=True).start()
    threading.Thread(target=start_analyzer, daemon=True).start()
    threading.Thread(target=start_report, daemon=True).start()
    time.sleep(2)
    
    asyncio.run(test_pipeline())
