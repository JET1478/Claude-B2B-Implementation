# B2B Office Workflow Automation Kit

A productized, multi-tenant automation platform that automates repetitive office workflows with AI + integrations. Deployable as a fixed-scope package — all customization is YAML/config-driven.

## Workflows

### 1. Customer Support Triage + Draft Replies
- **Input:** Webhook payload (or email) with subject/body/from
- **Pipeline:** Normalize → 7B Classify (category, priority, sentiment) → Claude Draft Reply → Routing Rules (YAML) → Slack Notification
- **Output:** Draft reply, tags, team assignment, SLA timer. Auto-send only if explicitly enabled AND confidence above threshold.

### 2. Sales Lead Intake + Qualification
- **Input:** Webhook from form (name/email/company/message/UTM)
- **Pipeline:** Normalize → 7B Extract (intent, urgency, spam) → Claude Qualify (score, questions, next step) → CRM Update → Email Drafts → Slack Notification
- **Output:** Lead score, qualification summary, CRM contact+deal, follow-up email drafts.

## Architecture

```
Webhooks/Email → FastAPI API → Redis Queue → RQ Workers → Model Router → Output Adapters
                     ↕                            ↕
                 PostgreSQL                   Local 7B (cheap)
                 (multi-tenant)               Claude API (quality)
```

**Model Orchestration:** Local 7B model handles classification/extraction (cheap). Claude handles drafting/reasoning (quality). Budget enforcer tracks per-tenant limits with circuit breakers.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- (Optional) Anthropic API key for Claude features

### 1. Clone and configure

```bash
git clone <repo-url>
cd Claude-B2B-Implementation

# Copy environment template
cp infra/.env.example infra/.env
# Edit infra/.env with your settings (at minimum, set BWFA_SECRET_KEY)
```

### 2. Start the stack

```bash
cd infra
docker compose up -d
```

This starts: PostgreSQL, Redis, API server, 2 RQ workers, and the admin frontend.

- **API:** http://localhost:8000 (docs at /docs)
- **Admin UI:** http://localhost:3000
- **Health:** http://localhost:8000/api/v1/health

### 3. Seed demo data

```bash
docker compose exec api python /app/../scripts/seed.py
```

### 4. Login to admin UI

Open http://localhost:3000 and login with:
- Email: `admin@example.com`
- Password: `admin123`

## Adding a Tenant

### Via Admin UI
1. Go to **Tenants** → **+ New Tenant**
2. Fill in name, slug, and API key
3. Enable desired workflows

### Via API
```bash
# Login first
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' | jq -r .token)

# Create tenant
curl -X POST http://localhost:8000/api/v1/tenants \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corp",
    "slug": "acme-corp",
    "anthropic_api_key": "sk-ant-your-key-here",
    "max_runs_per_day": 200,
    "max_tokens_per_day": 200000,
    "support_workflow_enabled": true,
    "sales_workflow_enabled": true,
    "autosend_enabled": false
  }'
```

## Configuring Workflows

Each tenant has YAML configs for support and sales workflows. Edit via Admin UI (Config page) or API.

See `samples/support.yaml` and `samples/sales.yaml` for full examples.

Key settings:
- **Routing rules:** Map categories to teams, set SLA timers, auto-tags
- **Autosend:** `enabled: false` by default. Set `confidence_threshold` (e.g., 0.90)
- **Escalation:** Auto-escalate when classification confidence is below threshold
- **CRM:** Enable/disable contact and deal creation

## Testing with Sample Payloads

### Submit a support ticket
```bash
curl -X POST http://localhost:8000/api/v1/webhooks/support \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Slug: demo-company" \
  -d '{
    "subject": "Cannot access my account",
    "body": "I have been trying to login for 2 hours after resetting my password. I get Invalid credentials each time. I have a client presentation tomorrow. Please help ASAP.",
    "from_email": "john@acmecorp.com",
    "from_name": "John Smith"
  }'
```

### Submit a sales lead
```bash
curl -X POST http://localhost:8000/api/v1/webhooks/leads \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Slug: demo-company" \
  -d '{
    "name": "Sarah Johnson",
    "email": "sarah@techstartup.io",
    "company": "TechStartup Inc.",
    "phone": "+1-555-0123",
    "message": "We are a 50-person SaaS company looking to automate customer support. We handle 200 tickets/day. Want a demo and annual pricing.",
    "utm_source": "google",
    "utm_medium": "cpc"
  }'
```

### Run the full integration test suite
```bash
cd scripts
bash test_integration.sh
```

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/webhooks/support` | Tenant slug header | Ingest support ticket |
| POST | `/api/v1/webhooks/leads` | Tenant slug header | Ingest sales lead |
| POST | `/api/v1/auth/login` | None | Admin login |
| GET | `/api/v1/tenants` | Admin JWT | List tenants |
| POST | `/api/v1/tenants` | Admin JWT | Create tenant |
| PATCH | `/api/v1/tenants/{id}` | Admin JWT | Update tenant |
| DELETE | `/api/v1/tenants/{id}` | Admin JWT | Deactivate tenant |
| GET | `/api/v1/runs` | Admin JWT | List pipeline runs |
| GET | `/api/v1/tickets` | Admin JWT | List support tickets |
| GET | `/api/v1/leads` | Admin JWT | List sales leads |
| GET | `/api/v1/audit` | Admin JWT | View audit logs |
| GET | `/api/v1/usage/{tenant_id}` | Admin JWT | Get usage stats |
| GET | `/api/v1/health` | None | Health check |
| GET | `/api/v1/metrics` | None | Prometheus metrics |

## BYOK (Bring Your Own Key)

Each tenant provides their own Anthropic API key, stored encrypted at rest using Fernet encryption. The master encryption key is set via `BWFA_MASTER_ENCRYPTION_KEY` env var.

For internal testing, set `BWFA_PLATFORM_KEY_MODE=true` and provide `BWFA_PLATFORM_ANTHROPIC_KEY`.

## Local 7B Model Setup (Optional)

The platform routes cheap tasks (classification, extraction) to a local 7B model to reduce costs. To enable:

1. Download a GGUF model (e.g., Mistral 7B Instruct):
   ```bash
   # Place in infra/models/
   wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.3-GGUF/resolve/main/mistral-7b-instruct-v0.3.Q4_K_M.gguf
   ```

2. Uncomment the `llama` service in `docker-compose.prod.yml`

3. Set in `.env`:
   ```
   BWFA_LOCAL_MODEL_ENABLED=true
   BWFA_LOCAL_MODEL_URL=http://llama:8081/completion
   ```

Without a local model, cheap tasks fall back to Claude Haiku (still cost-effective).

## Safety Features

- **Autosend OFF by default:** Never auto-sends external emails unless explicitly enabled per-tenant
- **Confidence thresholds:** Configurable per-workflow; drafts below threshold go to human review
- **Budget enforcement:** Per-tenant rate limits, daily run/token quotas, circuit breakers
- **Audit trail:** Every action logged with timestamps, model used, cost estimate, reason codes
- **API key encryption:** Tenant keys encrypted at rest with Fernet
- **No raw secret logging:** Sensitive fields redacted in structured logs

## Production Deployment

```bash
cd infra
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Key production checklist:
1. Set strong `BWFA_SECRET_KEY` and `BWFA_MASTER_ENCRYPTION_KEY`
2. Change `BWFA_ADMIN_PASSWORD`
3. Configure real SMTP settings for email delivery
4. Set up Slack webhook URLs per-tenant
5. Configure HubSpot API keys for CRM integration
6. Set `BWFA_LOCAL_MODEL_ENABLED=true` if using local inference
7. Point `NEXT_PUBLIC_API_URL` to your API domain

## Running Tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

## Project Structure

```
├── backend/           # FastAPI + RQ workers
│   ├── app/
│   │   ├── api/       # Route handlers
│   │   ├── models/    # SQLAlchemy models
│   │   ├── schemas/   # Pydantic v2 schemas
│   │   ├── services/  # Router, budget, crypto
│   │   ├── workers/   # RQ task handlers
│   │   ├── adapters/  # Email, CRM, Slack
│   │   └── middleware/ # Auth, tenant resolution
│   ├── alembic/       # DB migrations
│   └── tests/         # Unit tests
├── frontend/          # Next.js admin UI
├── prompts/           # Versioned prompt templates
├── samples/           # YAML configs + test payloads
├── infra/             # Docker Compose + env config
└── scripts/           # Seed data + integration tests
```
