# API Reference - Commercial Auto Fraud Detection Pipeline

## Base URL

```
http://localhost:8001
```

## Authentication

Currently, no authentication is required for local development. For production deployment, implement API key authentication or OAuth 2.0.

---

## Endpoints

### 1. Submit Batch for Processing

Submit a batch of insurance claims for fraud detection analysis.

**Endpoint:** `POST /api/fraud-detection/batch`

**Request Body:**
```json
{
  "batch_id": "batch_2026_w16",
  "batch_name": "Weekly Auto Claims — Week 16, April 2026",
  "claims": [
    {
      "claim_id": "CLM-2026-001",
      "claimant": {
        "id": "C-4821",
        "name": "Marcus Rivera"
      },
      "provider": {
        "id": "PRV-0093",
        "type": "repair_shop"
      },
      "vehicle": {
        "vin": "1HGCM82633A004352",
        "year": 2022,
        "make": "Honda",
        "model": "Accord"
      },
      "policy_number": "POL-99-1234",
      "claimed_amount": 42000.00,
      "loss_date": "2026-04-11",
      "loss_type": "major_collision",
      "description": "Rear-end collision on I-94 northbound..."
    }
  ]
}
```

**Response (200 OK):**
```json
{
  "status": "complete",
  "batch_id": "batch_2026_w16",
  "summary": {
    "total_claims": 12,
    "processed_claims": 12,
    "failed_claims": 0,
    "tier_distribution": {
      "critical": 2,
      "high": 3,
      "medium": 4,
      "low": 3
    },
    "processing_time_ms": 45230.5
  }
}
```

**Response (400 Bad Request):**
```json
{
  "error": "Invalid JSON body"
}
```

**Response (500 Internal Server Error):**
```json
{
  "status": "error",
  "batch_id": "batch_2026_w16",
  "error": "Error message details"
}
```

**Example:**
```bash
curl -X POST http://localhost:8001/api/fraud-detection/batch \
  -H "Content-Type: application/json" \
  -d @weekly_auto_claims.json
```

---

### 2. Get Batch Results

Retrieve complete results for a processed batch.

**Endpoint:** `GET /api/batch/{batch_id}/results`

**Path Parameters:**
- `batch_id` (string, required): The unique identifier of the batch

**Response (200 OK):**
```json
{
  "batch_id": "batch_2026_w16",
  "batch_name": "Weekly Auto Claims — Week 16, April 2026",
  "total_claims": 12,
  "processed_claims": 12,
  "failed_claims": 0,
  "results": [
    {
      "claim_id": "CLM-2026-001",
      "claimant_name": "Marcus Rivera",
      "claimed_amount": 42000.0,
      "composite_score": 87.5,
      "priority_tier": "critical",
      "confidence": "high",
      "patterns_flagged": 4,
      "top_pattern": "duplicate_similar",
      "top_pattern_score": 95.0,
      "has_report": true,
      "processing_time_ms": 3245.2
    }
  ],
  "tier_distribution": {
    "critical": 2,
    "high": 3,
    "medium": 4,
    "low": 3
  },
  "top_triggered_patterns": [
    {
      "pattern": "duplicate_similar",
      "count": 5
    },
    {
      "pattern": "provider_network",
      "count": 4
    }
  ],
  "processing_time_ms": 45230.5,
  "timestamp": "2026-04-30T14:23:45.123456"
}
```

**Response (404 Not Found):**
```json
{
  "error": "Batch not found"
}
```

**Example:**
```bash
curl http://localhost:8001/api/batch/batch_2026_w16/results
```

---

### 3. Get Claim Detail

Retrieve detailed results for a specific claim within a batch.

**Endpoint:** `GET /api/batch/{batch_id}/claims/{claim_id}`

**Path Parameters:**
- `batch_id` (string, required): The unique identifier of the batch
- `claim_id` (string, required): The unique identifier of the claim

**Response (200 OK):**
```json
{
  "claim_id": "CLM-2026-001",
  "claimant_name": "Marcus Rivera",
  "claimed_amount": 42000.0,
  "composite_score": 87.5,
  "priority_tier": "critical",
  "confidence": "high",
  "patterns_flagged": 4,
  "top_pattern": "duplicate_similar",
  "top_pattern_score": 95.0,
  "has_report": true,
  "processing_time_ms": 3245.2
}
```

**Response (404 Not Found):**
```json
{
  "error": "Batch not found"
}
```
or
```json
{
  "error": "Claim not found"
}
```

**Example:**
```bash
curl http://localhost:8001/api/batch/batch_2026_w16/claims/CLM-2026-001
```

---

### 4. SIU Chat Interface

Query batch results using natural language.

**Endpoint:** `POST /api/siu/chat`

**Request Body:**
```json
{
  "query": "Show me all critical priority claims",
  "batch_id": "batch_2026_w16"
}
```

**Request Fields:**
- `query` (string, required): Natural language query
- `batch_id` (string, optional): Batch ID for context

**Response (200 OK):**
```json
{
  "response": "Based on the batch results, there are 2 claims flagged as critical priority:\n\n1. CLM-2026-001 - Marcus Rivera ($42,000) - Fraud Score: 87.5\n   - Multiple duplicate claims detected\n   - Same claimant filed on two policies within 2 days\n   \n2. CLM-2026-002 - Marcus Rivera ($38,500) - Fraud Score: 85.2\n   - Duplicate claim on same vehicle\n   - Filed 2 days after CLM-2026-001"
}
```

**Response (500 Internal Server Error):**
```json
{
  "error": "Error message details"
}
```

**Example Queries:**
- "How many claims were flagged as critical priority?"
- "Which provider appears most frequently in high-risk claims?"
- "Show me claims with duplicate pattern scores above 50"
- "What's the average fraud score for this batch?"
- "List all claims involving provider PRV-0093"

**Example:**
```bash
curl -X POST http://localhost:8001/api/siu/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me all critical priority claims",
    "batch_id": "batch_2026_w16"
  }'
```

---

### 5. Dashboard UI

Access the web-based dashboard for visual analysis.

**Endpoint:** `GET /dashboard`

**Response:** HTML page with interactive dashboard

**Features:**
- Upload batch JSON files
- Real-time processing status
- Visual statistics (tier distribution, processing time)
- Sortable claims table
- Fraud score visualization

**Example:**
Open in browser: http://localhost:8001/dashboard

---

### 6. Root Endpoint

Redirects to the dashboard.

**Endpoint:** `GET /`

**Response:** Redirect to `/dashboard`

---

## Data Models

### Claim Input

```typescript
{
  claim_id: string;
  claimant: {
    id: string;
    name: string;
  };
  provider: {
    id: string;
    type: "repair_shop" | "medical" | "attorney" | "towing";
  };
  vehicle: {
    vin: string;
    year: number;
    make: string;
    model: string;
  };
  policy_number: string;
  claimed_amount: number;
  loss_date: string;  // ISO 8601 date
  loss_type: "minor_collision" | "major_collision" | "comprehensive";
  description: string;
}
```

### Claim Result

```typescript
{
  claim_id: string;
  claimant_name: string;
  claimed_amount: number;
  composite_score: number;  // 0-100
  priority_tier: "critical" | "high" | "medium" | "low";
  confidence: "high" | "medium" | "low";
  patterns_flagged: number;
  top_pattern: string;
  top_pattern_score: number;
  has_report: boolean;
  processing_time_ms: number;
}
```

### Priority Tiers

| Tier | Score Range | Description |
|------|-------------|-------------|
| Critical | ≥80 | Immediate investigation required |
| High | 60-79 | Priority review recommended |
| Medium | 40-59 | Standard review process |
| Low | <40 | Routine processing |

### Confidence Levels

| Level | Criteria | Description |
|-------|----------|-------------|
| High | 3+ patterns flagged | Strong evidence of fraud |
| Medium | 2 patterns flagged | Moderate evidence |
| Low | 0-1 patterns flagged | Weak or insufficient evidence |

---

## Fraud Patterns

### 1. Duplicate/Similar Claims (30% weight)

Detects:
- Same claimant filing multiple claims
- Same VIN across claims
- Prior fraud flags
- High claim frequency

**Score Factors:**
- Prior fraud flags: +20 per flag (max 40)
- High claim frequency: +15 per claim/year above 1.0 (max 25)
- Multiple prior claims: +15
- Multiple policies: +10
- High prior payouts: +10

### 2. Suspicious Timing (20% weight)

Detects:
- Claims near policy inception
- Recent coverage changes
- Policy modifications before loss

**Score Factors:**
- Claim within 7 days of inception: +40
- Claim within 30 days of inception: +25
- Recent coverage upgrade: +30
- Recent policy modification: +10
- Policy status anomalies: +15

### 3. Inflated Amounts (25% weight)

Detects:
- Claimed amount exceeds vehicle value
- Repair costs above benchmarks
- Prior total loss history

**Score Factors:**
- Claim >1.3x market value: +50
- Claim >1.0x market value: +15
- Claim exceeds regional high: +30
- Claim >1.3x regional median: +15
- Prior total loss: +15
- Salvage/rebuilt title: +10

### 4. Provider Network (25% weight)

Detects:
- High billing ratios
- Excessive flagged claims
- Referral ring patterns
- License issues

**Score Factors:**
- Network risk CRITICAL: +40
- Network risk HIGH: +30
- Network risk MEDIUM: +15
- Billing >2.0x regional avg: +25
- Billing >1.5x regional avg: +10
- Flagged claims >20: +20
- Flagged claims >5: +10
- License issues: +15
- Referral ring (>10 shared): +10

---

## Error Codes

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid input |
| 404 | Not Found - Resource doesn't exist |
| 500 | Internal Server Error - Processing failed |

---

## Rate Limits

Currently no rate limits for local development. For production:
- Recommended: 100 requests per minute per IP
- Batch size limit: 1000 claims per batch
- Concurrent batches: 5 per user

---

## Webhooks (Future)

Future versions will support webhooks for async processing:

```json
{
  "webhook_url": "https://your-domain.com/webhook",
  "events": ["batch.complete", "batch.failed"]
}
```

---

## SDK Examples

### Python

```python
import httpx
import json

async def submit_batch(batch_file_path):
    with open(batch_file_path, 'r') as f:
        batch_data = json.load(f)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8001/api/fraud-detection/batch",
            json=batch_data,
            timeout=300.0
        )
        return response.json()

# Usage
result = await submit_batch("weekly_auto_claims.json")
print(f"Batch {result['batch_id']} processed: {result['summary']}")
```

### JavaScript

```javascript
async function submitBatch(batchData) {
  const response = await fetch('http://localhost:8001/api/fraud-detection/batch', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(batchData),
  });
  
  return await response.json();
}

// Usage
const batchData = require('./weekly_auto_claims.json');
const result = await submitBatch(batchData);
console.log(`Batch ${result.batch_id} processed:`, result.summary);
```

### cURL

```bash
# Submit batch
curl -X POST http://localhost:8001/api/fraud-detection/batch \
  -H "Content-Type: application/json" \
  -d @weekly_auto_claims.json

# Get results
curl http://localhost:8001/api/batch/batch_2026_w16/results

# Query with SIU chat
curl -X POST http://localhost:8001/api/siu/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Show critical claims", "batch_id": "batch_2026_w16"}'
```

---

## Support

For issues or questions:
- Check the main README.md
- Review SETUP.md for troubleshooting
- Examine code comments in the source
- Run `python quickstart.py` to verify setup
