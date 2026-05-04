"""
Multi-process Entry Point
Launches the Main Web API and the 3 A2A Agents in parallel using uvicorn.
"""

import multiprocessing
import uvicorn
from dotenv import load_dotenv

# Ensure env vars are loaded
load_dotenv()

def run_enrichment_a2a():
    uvicorn.run("commercial_auto_fraud.presentation.a2a_server:enrichment_app", host="0.0.0.0", port=8002)

def run_analyzer_a2a():
    uvicorn.run("commercial_auto_fraud.presentation.a2a_server:analyzer_app", host="0.0.0.0", port=8003)

def run_report_a2a():
    uvicorn.run("commercial_auto_fraud.presentation.a2a_server:report_app", host="0.0.0.0", port=8004)

def run_web_api():
    uvicorn.run("commercial_auto_fraud.presentation.web_api:app", host="0.0.0.0", port=8001, reload=True)

if __name__ == "__main__":
    print("Starting Enterprise Commercial Auto Fraud Pipeline...")
    
    # We use spawn to ensure clean cross-platform behavior
    multiprocessing.set_start_method("spawn", force=True)

    processes = [
        multiprocessing.Process(target=run_enrichment_a2a, name="Enrichment_A2A"),
        multiprocessing.Process(target=run_analyzer_a2a, name="Analyzer_A2A"),
        multiprocessing.Process(target=run_report_a2a, name="Report_A2A"),
        multiprocessing.Process(target=run_web_api, name="Web_API")
    ]

    for p in processes:
        p.start()
        
    print("All services launched:")
    print("- Web API / Dashboard : http://localhost:8001/dashboard")
    print("- Enrichment A2A      : http://localhost:8002")
    print("- Analyzer A2A        : http://localhost:8003")
    print("- Report A2A          : http://localhost:8004")

    for p in processes:
        p.join()
