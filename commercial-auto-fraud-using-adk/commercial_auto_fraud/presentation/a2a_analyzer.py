import uvicorn
from google.adk.a2a.server import to_a2a
from commercial_auto_fraud.agents.analyzer_agent import analyzer_agent

app = to_a2a(analyzer_agent)

if __name__ == "__main__":
    uvicorn.run("commercial_auto_fraud.presentation.a2a_analyzer:app", host="0.0.0.0", port=8003, reload=True)
