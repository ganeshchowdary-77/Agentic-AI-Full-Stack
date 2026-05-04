# Setup Guide - Commercial Auto Fraud Detection Pipeline

## Prerequisites

Before you begin, ensure you have:

1. **Python 3.10 or higher**
   ```bash
   python --version
   ```

2. **Google Gemini API Key**
   - Get your API key from: https://aistudio.google.com/app/apikey
   - Or use Google Cloud Vertex AI credentials

3. **Package Manager** (choose one):
   - `uv` (recommended, faster): https://docs.astral.sh/uv/
   - `pip` (standard)

## Step-by-Step Installation

### 1. Clone or Download the Project

```bash
cd commercial-auto-fraud-using-adk
```

### 2. Install Dependencies

#### Option A: Using `uv` (Recommended)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync
```

#### Option B: Using `pip`

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -e .
```

### 3. Configure Environment Variables

Create or edit the `.env` file in the project root:

```bash
# Required: Your Gemini API key
GEMINI_API_KEY=your_actual_gemini_api_key_here

# Optional: Redis URL (defaults to localhost)
REDIS_URL=redis://localhost:6379/0

# Optional: A2A Remote URLs (defaults shown)
ENRICHMENT_A2A_URL=http://localhost:8002
ANALYZER_A2A_URL=http://localhost:8003
REPORT_A2A_URL=http://localhost:8004
```

**Important**: Replace `your_actual_gemini_api_key_here` with your real API key!

### 4. Verify Installation

Check that all dependencies are installed:

```bash
# If using uv
uv run python -c "import google.adk; import fastapi; print('✅ All dependencies installed!')"

# If using pip
python -c "import google.adk; import fastapi; print('✅ All dependencies installed!')"
```

## Running the System

### Quick Start (All Services)

The easiest way to run the entire system:

```bash
# If using uv
uv run python main.py

# If using pip (with activated venv)
python main.py
```

This starts all 4 services:
- ✅ Web API / Dashboard: http://localhost:8001/dashboard
- ✅ Enrichment A2A Agent: http://localhost:8002
- ✅ Analyzer A2A Agent: http://localhost:8003
- ✅ Report A2A Agent: http://localhost:8004

### Testing the System

Once all services are running, open a new terminal and run:

```bash
# If using uv
uv run python test_pipeline.py

# If using pip
python test_pipeline.py
```

This will:
1. Submit the sample batch (`weekly_auto_claims.json`)
2. Process all 12 claims through the pipeline
3. Display fraud scores and priority tiers
4. Generate investigation reports for flagged claims

### Using the Web Dashboard

1. Open your browser to: http://localhost:8001/dashboard
2. Click "Choose JSON File" and select `weekly_auto_claims.json`
3. Click "Analyze Batch"
4. View real-time results with fraud scores and priority distribution

## Troubleshooting

### Issue: "Module not found" errors

**Solution**: Make sure you've installed dependencies and activated the virtual environment

```bash
# Check if virtual environment is activated
which python  # Should show path to .venv/bin/python

# Reinstall dependencies
uv sync  # or pip install -e .
```

### Issue: "Connection refused" when testing

**Solution**: Make sure all services are running

```bash
# Check if services are running
curl http://localhost:8001/
curl http://localhost:8002/
curl http://localhost:8003/
curl http://localhost:8004/

# If any fail, restart with: python main.py
```

### Issue: "Invalid API key" or authentication errors

**Solution**: Verify your Gemini API key

```bash
# Check .env file
cat .env | grep GEMINI_API_KEY

# Test API key
curl -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Hello"}]}]}' \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=YOUR_API_KEY"
```

### Issue: Services start but processing fails

**Solution**: Check the logs for specific errors

```bash
# Look for error messages in the terminal where you ran main.py
# Common issues:
# - API rate limits (wait a few seconds and retry)
# - Network connectivity (check internet connection)
# - Invalid JSON format (validate your batch file)
```

### Issue: Port already in use

**Solution**: Change the ports or kill existing processes

```bash
# Find process using port 8001
# On Windows:
netstat -ano | findstr :8001
taskkill /PID <process_id> /F

# On macOS/Linux:
lsof -ti:8001 | xargs kill -9

# Or change ports in main.py
```

## Development Setup

### Running Individual Services (for development)

```bash
# Terminal 1: Web API
uvicorn commercial_auto_fraud.presentation.web_api:app --reload --port 8001

# Terminal 2: Enrichment Agent
uvicorn commercial_auto_fraud.presentation.a2a_server:enrichment_app --reload --port 8002

# Terminal 3: Analyzer Agent
uvicorn commercial_auto_fraud.presentation.a2a_server:analyzer_app --reload --port 8003

# Terminal 4: Report Agent
uvicorn commercial_auto_fraud.presentation.a2a_server:report_app --reload --port 8004
```

The `--reload` flag enables auto-reload on code changes.

### Running Tests

```bash
# Run the test pipeline
python test_pipeline.py

# Test individual endpoints
curl -X POST http://localhost:8001/api/fraud-detection/batch \
  -H "Content-Type: application/json" \
  -d @weekly_auto_claims.json
```

### Viewing Generated Reports

Investigation reports are saved to:
```
artifacts/reports/CLM-2026-XXX_investigation.md
```

Open these files to see detailed fraud analysis for flagged claims.

## Next Steps

1. **Explore the Dashboard**: http://localhost:8001/dashboard
2. **Read the API Documentation**: See README.md for API endpoints
3. **Customize Fraud Patterns**: Edit `tools/analysis_tools.py`
4. **Add New Prompts**: Create YAML files in `prompts/storage/`
5. **Integrate Real Data**: Replace mock providers in `infrastructure/mock_providers.py`

## Getting Help

- Check the main README.md for detailed documentation
- Review the code comments in each module
- Examine the sample data in `weekly_auto_claims.json`
- Look at the prompt templates in `prompts/storage/`

## Production Deployment

For production deployment, see the "Production Deployment" section in README.md.

Key considerations:
- Use environment-specific configuration
- Set up proper logging and monitoring
- Implement rate limiting and authentication
- Use a production-grade database (PostgreSQL, MongoDB)
- Deploy with container orchestration (Kubernetes, Docker Swarm)
- Set up CI/CD pipelines

---

**Ready to detect fraud? Start the services and run the test!**

```bash
python main.py
# In another terminal:
python test_pipeline.py
```
