import uvicorn
from google.adk.a2a.server import to_a2a
from commercial_auto_fraud.agents.report_agent import report_agent

app = to_a2a(report_agent)

if __name__ == "__main__":
    uvicorn.run("commercial_auto_fraud.presentation.a2a_report:app", host="0.0.0.0", port=8004, reload=True)
