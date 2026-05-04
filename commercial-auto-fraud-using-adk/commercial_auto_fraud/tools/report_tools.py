"""
Report Tools — Used by the Report Generator Agent.
"""

import os
from typing import Dict, Any
from google.adk.tools import ToolContext

async def save_report_artifact(claim_id: str, markdown_content: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Saves the generated investigation report to the filesystem as an artifact.
    """
    os.makedirs("artifacts/reports", exist_ok=True)
    file_path = f"artifacts/reports/{claim_id}_investigation.md"
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
        
    return {
        "status": "success",
        "file_path": file_path,
        "bytes_written": len(markdown_content)
    }
