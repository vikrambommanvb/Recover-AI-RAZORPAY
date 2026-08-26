# RecoverAI

RecoverAI is a closed-loop revenue recovery intelligence and safety execution gateway designed for Razorpay in Test Mode. It converts AI intervention recommendations into deterministic gateway actions under strict safety guardrails.

---

## Problem
In online commerce, payment failures are common. However, payment failure is not a single state; failures occur due to transient handshakes, expired cards, low balances, or network drops. Without automated, context-aware recovery paths, merchants lose recoverable transactions, resulting in customer churn and revenue leakage.

---

## Why This Matters
Merchants often lack granular, real-time insights to diagnose payment failures. Simple retry strategies are unsafe (e.g. risking double capture on slow responses), while human-driven recovery is too slow. RecoverAI bridges this gap by automatically classifying risk, deciding optimal recovery interventions using AI, and executing them safely.

---

## Solution
RecoverAI implements a multi-stage automated recovery engine following this closed-loop pipeline:
* **Detect**: Identifies failed payments and creates a structured recovery case with prior customer history context.
* **Diagnose**: Classifies the root cause (transient error, customer funds, declined card).
* **Decide**: An advisory AI agent proposes a recovery action (Retry, Remind, Escalate, Stop).
* **Guard**: A deterministic Policy Engine evaluates the recommendation against hard rules.
* **Execute**: Executed safely against Razorpay API in Test Mode.
* **Verify**: Verifies outcome state via signature-checked webhook events.
* **Measure**: Computes actual recovered revenue from verified captured outcomes.
* **Audit**: Persists complete, traceable correlation ID trails in database logs.

---

## Architecture

```
        Payment Fail Event (Gateway / Webhook)
                         ↓
               Revenue Risk Detector
                         ↓
               Recovery Case Builder
                         ↓
              AI Agent Recommendation (Mixtral / LLM)
                         ↓
            Deterministic Policy Engine (Hard Rules Gate)
               ├── ALLOW ➔ Execution Service ➔ Razorpay Test API
               ├── BLOCK ➔ Log Blocked Case ➔ Audit Trail
               └── ESCALATE ➔ Log Escalation Case ➔ Human Review
                         ↓
            Verification Webhook (HMAC SHA-256 Signature)
                         ↓
            Aggregated Evaluation Metrics & Dashboard
```

---

## AI Design
The AI is strictly advisory and is used where reasoning is valuable:
* **Failure Interpretation**: Diagnosing why the payment failed using context.
* **Intervention Recommendation**: Proposing whether to retry, send a reminder, stop, or escalate.
* **Risk Context Analysis**: Incorporating customer history to gauge trust.

The AI is **NOT** used for:
* **Authorization**: The AI cannot approve payment link generation or capture transactions.
* **Safety & Security Decisions**: The Policy Engine holds veto power.
* **Financial Accounting**: Deciding if money has been recovered is done programmatically by verifying gateway states.

---

## Safety Model
The system enforces deterministic guardrails that cannot be bypassed by the LLM:
* **Max Amount**: Block recovery if the amount exceeds ₹5,000 (`MAX_RECOVERY_AMOUNT_MINOR=500000`).
* **Attempt Limits**: Max 2 attempts (`MAX_RECOVERY_ATTEMPTS=2`). Reaching this limits escalates the case.
* **Cooldown Gates**: Cooldown of 5 minutes (`RECOVERY_COOLDOWN_SECONDS=300`) between attempts to prevent spamming the customer.
* **Gateway State Verification**: Before execution, payment status is checked on Razorpay. If already `captured`, skips execution to prevent double-captures.
* **Transition Checks**: Prevents invalid state machine transitions (e.g. executing on `RECOVERED` or `CLOSED` cases).

---

## Razorpay Integration
* **Strict Test Mode Checks**: The system parses key prefixes on startup and rejects keys starting with `rzp_live_`. Only `rzp_test_` keys are allowed.
* **Basic Auth**: Calls are made using Basic Auth securely over HTTPS.
* **Signature Verification**: Webhooks check `X-Razorpay-Signature` against the raw payload using `RAZORPAY_WEBHOOK_SECRET` and HMAC-SHA256 to ensure authenticity.

---

## Revenue Recovery Measurement
* **Revenue Recovered**: Programmatically computed as the sum of payment amounts for cases where a verified payment capture webhook (`payment.captured`) was processed.
* **Bypassed Attempts**: Failed attempts, blocked cases, or policy escalations do **not** contribute to recovered revenue.

---

## Failure Handling
* **API Timeout**: If the Razorpay API times out or returns an error, the attempt is marked as `FAILED`, and the case remains open/escalated.
* **AI Provider Outage**: If the AI provider is unavailable, the pipeline falls back to `ESCALATE`, ensuring safe operations.
* **Webhook Duplication**: Double webhook events are caught using a unique index constraint on `event_id` in the `webhook_events` collection.

---

## Demo

Execute the deterministic console demo showcasing canonical success cases, safety blocks, API timeouts, and a 500-record batch simulation:
```bash
PYTHONPATH=. python scripts/final_demo.py
```

---

## Setup

### 1. Set up virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment
Create a `.env` file in the root directory:
```env
APP_NAME=RecoverAI
APP_ENV=development
APP_MODE=demo
DEBUG=true

MONGODB_URI=mongodb+srv://recovery:<db_password>@cluster0.kpvcp2f.mongodb.net/?appName=Cluster0
MONGODB_DATABASE=recoverai

AI_PROVIDER=mock
GROQ_API_KEY=
GROQ_MODEL=mixtral-8x7b-32768

RAZORPAY_KEY_ID=rzp_test_TUOltC7Y41TnAV
RAZORPAY_KEY_SECRET=d6lNv2aGIV057A9MHv05Gdoe
RAZORPAY_WEBHOOK_SECRET=super_secret_webhook_token
```

### 3. Start Backend Server
```bash
uvicorn app.main:app --reload
```
API Documentation will be available at: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Start React Frontend Dashboard
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser to explore the dashboard.

---

## Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `APP_MODE` | Application Mode (`demo` or `test`) | `demo` |
| `AI_PROVIDER` | AI provider abstraction (`mock` or `groq`) | `mock` |
| `MONGODB_URI` | MongoDB Atlas Connection string | `mongodb+srv://...` |
| `RAZORPAY_KEY_ID` | Razorpay Test Key ID | `rzp_test_...` |
| `RAZORPAY_KEY_SECRET` | Razorpay Test Key Secret | `d6lN...` |

---

## Project Structure
```
app/
    api/         # Routers and dependency injectors
    core/        # Configuration and logging configurations
    db/          # MongoDB configurations and in-memory fallbacks
    guardrails/  # Policy Engine and deterministic safety rules
    models/      # Pydantic schemas (Payment, Case, Action, Webhook)
    services/    # Logic (Risk Service, Executor, Evaluation Service)
scripts/         # Demo runners and manual test tools
tests/           # Pytest unit and integration test suite
frontend/        # React + Vite dashboard frontend application
```

---

## Design Decisions
* **Minor Financial Units**: All financial computations are done in minor units (paise) to prevent floating-point representation bugs.
* **Advisory AI**: Designed as an advisor to the Policy Engine. This prevents AI hallucination or malicious injection from compromising gateway authorizations.
* **Offline Mock Database**: We implement a production-grade in-memory database mock fallback. If the network or credentials fail on MongoDB Atlas, the system automatically runs locally without raising crashes.

---

## What Broke
* **Database TLS Handshake Failure**: During local testing, corporate firewalls or missing OS Python certificates caused TLS alert handshake failures. We solved this by implementing an automatic `MockDatabase` fallback on connection failure.
* **Shared Test client overrides**: The FastAPI `TestClient` uses a global dependency override mapping. When tests ran in parallel, overrides from one file bled into another. We resolved this by standardizing and importing DRY `MockDatabase` instances across the test suite.

---

## Limitations
* **Test Mode Only**: Designed strictly for Test Mode (`rzp_test_`). Real payment transactions (`rzp_live_`) are blocked at the code level.
* **Simulated Checkouts**: Customer payment links are simulated. Real-world recovery rates will depend on customer behavior and latency.

---

## Future Improvements
* **Active SMS/Email Routing**: Integrate Twilio or SendGrid to send actual retry payment links directly to customers.
* **Real-time Webhook Tunneling**: Set up local webhook tunnels (e.g. ngrok) to test automated captured state transitions directly from Razorpay dashboard webhooks.
