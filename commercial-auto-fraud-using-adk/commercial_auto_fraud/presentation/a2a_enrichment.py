import uvicorn
from google.adk.a2a.server import to_a2a
from commercial_auto_fraud.agents.enrichment_agent import enrichment_agent

app = to_a2a(enrichment_agent)

if __name__ == "__main__":
    uvicorn.run("commercial_auto_fraud.presentation.a2a_enrichment:app", host="0.0.0.0", port=8002, reload=True)
