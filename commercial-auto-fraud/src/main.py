import threading
import os
import sys
import time
import uvicorn
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.presentation.a2a.server_enrichment import start_server as start_enrichment
from src.presentation.a2a.server_analyzer import start_server as start_analyzer
from src.presentation.a2a.server_report import start_server as start_report

load_dotenv()

if __name__ == "__main__":
    # Boot the A2A sub-agent servers
    threading.Thread(target=start_enrichment, daemon=True).start()
    threading.Thread(target=start_analyzer, daemon=True).start()
    threading.Thread(target=start_report, daemon=True).start()
    
    # Wait briefly for servers to spin up
    time.sleep(2)
    
    print("[OK] All sub-agent servers started.")
    print()
    print("Starting Fraud Pipeline Dashboard -> http://localhost:8001")
    print("   A2A Enrichment Agent            -> http://localhost:8002")
    print("   A2A Pattern Analyzer            -> http://localhost:8003")
    print("   A2A Report Generator            -> http://localhost:8004")
    print()

    # Run the Orchestrator's Web Dashboard on port 8001 in the main thread
    uvicorn.run("src.presentation.web.app:app", host="127.0.0.1", port=8001, reload=False)
