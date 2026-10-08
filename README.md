# Oraczen Extraction Workbench

A review tool for LLM-extracted support-ticket records. Raw tickets are turned into structured records, every output is validated against a strict schema, a failed extraction is retried once, and anything still doubtful goes to a human reviewer.

**Stack:** FastAPI (Python) backend · Next.js (App Router, TypeScript) frontend · No external API key required.

---

## 🚀 Live Deployment

| | URL |
|--|--|
| 🌐 **Frontend (Vercel)** | **https://frontend-woad-chi-lb8qq4qx8a.vercel.app** |
| ⚙️ **Backend API (Render)** | **https://oraczen-backend-ugoa.onrender.com** |
| 🏥 **Health Check** | https://oraczen-backend-ugoa.onrender.com/health |
| 📖 **API Docs** | https://oraczen-backend-ugoa.onrender.com/docs |

> ⚠️ The Render free tier sleeps after 15 min of inactivity. The first request after sleep takes ~30 seconds to wake up — subsequent requests are instant.

---

## Setup

**Prerequisites:** Python 3.11+, Node.js 18+, npm.

### 1. Clone

```bash
git clone https://github.com/Lagnasha-Tripathy/oraczen-extraction-workbench.git
cd oraczen-extraction-workbench
```

### 2. Backend (terminal 1)

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- Health check: http://localhost:8000/health
- API docs: http://localhost:8000/docs

### 3. Frontend (terminal 2)

```bash
cd oraczen-extraction-workbench/frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

Open http://localhost:3000.

---

## Configuration

All variables are listed in `.env.example`. No API key is needed.

| Variable | Default | Purpose |
| --- | --- | --- |
| `LLM_PROVIDER` | `mock` | Extraction provider (deterministic mock) |
| `MAX_CONCURRENCY` | `5` | Maximum tickets processed at the same time |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend URL used by the frontend |

---

## How it works

```text
Raw ticket
   │
   ├─ empty body ──────────────► needs_review (model not called)
   │
   ▼
Mock provider ──► Pydantic validation
                     │
          valid ─────┴───── invalid
            │                  │
          done            retry once
                               │
                    valid ─────┴───── invalid
                      │                  │
                    done            needs_review
                                         │
                                  human correction
                                         │
                              same validation ──► done
```

Each ticket is processed independently, so one bad ticket never fails the batch.

### Application flow

1. **Select tickets.** The home page lists all 150 tickets with search and a channel filter. Select any subset.
2. **Start a job.** `POST /api/jobs` returns `202` with a job id immediately, and extraction runs in the background.
3. **Extract and validate.** Each ticket goes to the provider and the output is validated against the Pydantic schema.
4. **Retry once.** If validation fails, extraction is attempted one more time. A second failure sends the item to `needs_review`, keeps the raw output and validation errors, and the rest of the batch continues.
5. **Review.** The raw ticket is shown next to the editable extracted fields. Items needing review are highlighted and sorted to the top. Edits are validated with the same schema, and errors are shown against the field.
6. **Export.** One click downloads the records as CSV.

### Concurrency

An `asyncio.Semaphore` limits how many tickets run at once (`MAX_CONCURRENCY`, default 5).

### Progress updates

The frontend polls the job endpoint, so progress and per-item results appear while the job is still running.

### Human edits

Each record has an `edited_fields` list. Only fields whose value actually changed are marked as human-edited. The UI shows a "Human edited" badge, and the CSV includes the same column.

---

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/tickets` | List, search and filter tickets |
| `POST` | `/api/jobs` | Start an extraction job (returns `202`) |
| `GET` | `/api/jobs/{job_id}` | Job state and progress |
| `GET` | `/api/jobs/{job_id}/results` | Extracted records |
| `PATCH` | `/api/records/{record_id}` | Human correction (validated and tracked) |
| `GET` | `/api/jobs/{job_id}/export.csv` | Export records as CSV |
| `GET` | `/health` | Health check |

---

## Mock provider

The mock provider needs no API key, simulates latency, and gives the same output for the same input. It deliberately returns invalid output for a few tickets so the retry paths run:

| Ticket | Behaviour | Expected result |
| --- | --- | --- |
| `tkt_0010`, `tkt_0042` | Invalid on attempt 1, valid on attempt 2 | `done`, retry count 1 |
| `tkt_0017` | Invalid on both attempts | `needs_review`, raw output kept |
| `tkt_0004`, `tkt_0020` | Bodies are `please advise` and `?` | `needs_review`, model not called |

Other tickets worth opening: `tkt_0058` (French, amount in EUR), `tkt_0089` (three problems and a renewal threat), `tkt_0105` (typos), `tkt_0131` (phone transcript with a spoken amount).

---

## Tests

```bash
cd backend
pytest -q
```

The backend tests cover the retry behaviour, an item failing twice landing in `needs_review` while the job still completes, the progress arithmetic and job completion, human edits and CSV export.

Frontend production build check:

```bash
cd frontend
npm run build
```

---

## Design decisions

The decisions and trade-offs are written up in [DECISIONS.md](DECISIONS.md). In short:

- **Empty tickets** (`please advise`, `?`) are not sent to a model. There is nothing to extract, so a call would only cost money and invent values.
- **EUR amounts** are not converted, because no exchange rate is defined. `refund_amount` stays empty and the reviewer reads the amount in the raw ticket.
- **Multi-issue tickets** stay as one record with one primary category, and churn risk takes priority.
- **Progress** uses polling rather than streaming, for simplicity and reliability on free hosting.
- **Storage** is in memory, which is enough for this assignment.

---

## Deployment

The frontend and backend are deployed separately.

- **Backend (Render):** root directory `backend`, build command `pip install -r requirements.txt`, start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Set `LLM_PROVIDER=mock` and the allowed frontend origin.
- **Frontend (Vercel):** root directory `frontend`, with `NEXT_PUBLIC_API_URL` set to the backend URL.

---

## Known limitations

- Jobs, records and human edits are stored in memory and are lost when the backend restarts.
- The provider is a rule-based mock, not a real LLM, so its company, severity and category rules are simple heuristics.
- When a ticket gives no severity signal, the mock falls back to `medium` with low confidence instead of leaving the field empty. A production system should leave it empty and flag the record.
- The retry does not pass the validation error back to the mock provider. A real LLM provider should receive it.
- When a human edit resolves a `needs_review` record, the job's `needs_review` counter is not decremented.
- No authentication, since it is outside the scope of the assignment.

---

## 🔮 Future Improvements (Scaling to a Commercial Platform)

This section describes every improvement that would be needed to take this project from a working prototype to a production-grade commercial system.

---

### 1. Replace the Mock Provider with a Real LLM

The current mock uses regex and keyword rules. A real system would call an LLM API.

- Swap `mock_provider.py` with a client for **OpenAI GPT-4o**, **Google Gemini**, or **Anthropic Claude**.
- Send the raw ticket text in a structured prompt and ask for a JSON response matching the `ExtractedRecord` schema.
- On retry, include the validation errors in the prompt so the model knows exactly what it got wrong and can self-correct.
- Add **prompt versioning** so prompts can be updated and tested without changing code.
- Track **token usage and cost per ticket** so you can monitor spending.

---

### 2. Persistent Database Storage

All jobs, records, and edits are currently in memory and are lost on restart.

- Replace `store.py` with a **PostgreSQL** database (via SQLAlchemy or the `databases` library).
- Add a proper **migration tool** like Alembic so the schema can evolve without data loss.
- Store every extraction attempt, both raw and validated, for auditability.
- Keep a full **edit history** per record so you can see what a human changed and when.
- Use **UUIDs** as primary keys instead of ticket IDs.

---

### 3. Async Task Queue (Replace asyncio with Celery + Redis)

The current background processing uses `asyncio.create_task()` inside a single Python process. This works for small batches but breaks under load.

- Use **Celery** with a **Redis** or **RabbitMQ** broker to push each ticket as an independent task.
- Workers can run on **separate machines**, allowing true horizontal scaling.
- Failed tasks can be **retried automatically** with exponential backoff.
- Use **Flower** (Celery monitoring UI) to see queue depth and worker health in real time.
- Separate the API server (FastAPI) from the worker processes so a slow extraction job never slows down API responses.

---

### 4. Authentication and Role-Based Access Control

There is currently no login or access control.

- Add **JWT-based authentication** so only authorised users can access the API.
- Define roles: `admin` (can create jobs, manage users), `reviewer` (can edit records), `viewer` (read-only).
- Use **OAuth2 / SSO** (Google, Microsoft, Okta) for enterprise login.
- Log every action (who launched a job, who edited which field, when) in an **audit trail** table.

---

### 5. Real-Time Progress with WebSockets

The frontend currently polls every second. For large batches this is wasteful.

- Replace polling with a **WebSocket** or **Server-Sent Events (SSE)** connection.
- The backend pushes progress updates to the frontend the instant each ticket completes.
- This reduces server load and makes the UI feel instant even on batches of 10,000+ tickets.

---

### 6. Confidence Score Thresholds and Routing

The mock provider already generates per-field confidence scores. A commercial system would act on them.

- If confidence for any field is below a configurable threshold (e.g. 0.5), automatically route the record to `needs_review` even if it passes schema validation.
- Show confidence scores as a visual indicator in the UI (colour-coded bars or percentages).
- Allow admins to configure thresholds per field via a settings page.
- Use low-confidence signals to decide whether to call a second, more expensive model for verification.

---

### 7. Bulk Import and Multiple Input Formats

The current system only reads from `data/tickets.jsonl`.

- Support **CSV upload**, **JSON upload**, and **direct API ingestion** from Zendesk, Freshdesk, or Salesforce via webhooks.
- Add a file upload endpoint (`POST /api/ingest`) that validates the format, stores raw tickets in the database, and creates a job automatically.
- Support **pagination and cursor-based filtering** on the tickets list for datasets with millions of records.

---

### 8. Advanced Export and Scheduled Reports

The current CSV export is a flat one-page download.

- Add **filtered exports** (e.g. export only `needs_review` records, or only records edited by a specific reviewer).
- Support **Excel (.xlsx)** export with formatted headers and colour-coded status cells.
- Add a **summary statistics** endpoint: total tickets, done %, needs_review %, average confidence per field, average processing time.
- Schedule **automated daily/weekly email reports** using a cron job.

---

### 9. Admin Dashboard and Analytics

- Build an admin page showing live metrics: queue depth, average extraction latency, retry rate, needs_review rate by channel, human edit rate by field.
- Track which fields are most frequently corrected by humans — this signals where the prompt needs improvement or training data.
- Show **reviewer throughput** metrics (records reviewed per hour per user).
- Visualise extraction accuracy trends over time.

---

### 10. Model Evaluation and A/B Testing

- Store human-corrected final values as ground truth and compare them against original model outputs.
- Calculate per-field accuracy metrics (precision, recall, exact match rate).
- Run **A/B experiments** between two prompt versions or two models and compare accuracy and cost automatically.
- Use low-accuracy fields to identify exactly where the prompt needs improvement.

---

### 11. Fine-Tuned or Domain-Specific Model

- Collect the human-corrected records as a labelled dataset.
- Fine-tune a smaller, cheaper model (e.g. GPT-4o-mini or an open-source model like Mistral) specifically on this extraction task.
- A domain-specific fine-tuned model will outperform a general model on this exact task at significantly lower cost per ticket.

---

### 12. Caching and Rate Limiting

- Cache extraction results by a hash of the ticket body so identical tickets are never sent to the LLM twice.
- Use **Redis** as the cache store with a configurable TTL.
- Add **rate limiting** on the API (e.g. max 100 requests/minute per user) to prevent abuse.
- Implement an **LLM call budget** per organisation so one customer cannot exhaust the API quota.

---

### 13. Containerisation and CI/CD

- Write a **Dockerfile** for the backend so it runs identically in development, staging, and production.
- Write a **docker-compose.yml** for local development that starts the backend, frontend, PostgreSQL, and Redis together with a single command.
- Deploy to **Kubernetes** (AWS EKS, GCP GKE, or Azure AKS) for auto-scaling based on queue depth.
- Use **GitHub Actions** for CI/CD: run all tests on every pull request, deploy to staging automatically, deploy to production on a tagged release.

---

### 14. Multi-Tenancy

- Allow multiple organisations (tenants) to use the platform with complete data isolation.
- Each tenant has its own jobs, records, users, and API keys.
- Implement **row-level security** in the database so one tenant can never access another's data.
- Support per-tenant configuration: custom extraction schema, custom confidence thresholds, custom export templates.

---

### Summary Table

| Area | Current (Prototype) | Commercial Version |
|------|--------------------|--------------------|
| Extraction | Deterministic mock | Real LLM (GPT-4o, Gemini, Claude) |
| Storage | In-memory (lost on restart) | PostgreSQL + Alembic migrations |
| Task queue | `asyncio` in one process | Celery + Redis, multi-worker |
| Auth | None | JWT + OAuth2 + RBAC + audit log |
| Progress updates | 1-second polling | WebSockets / Server-Sent Events |
| Confidence scores | Generated but unused | Threshold-based routing + UI display |
| Input | Static JSONL file | API ingestion, CSV/JSON upload, webhooks |
| Export | Flat CSV | Filtered CSV, Excel, scheduled reports |
| Analytics | None | Admin dashboard, field accuracy metrics |
| Deployment | Single Render free instance | Docker + Kubernetes + CI/CD pipeline |
| Multi-tenancy | No | Full row-level isolation per organisation |

---

## Project structure

```text
backend/
  app/          FastAPI app, worker, mock provider, schemas, store, routes
  tests/        pytest suite
  requirements.txt
  pytest.ini
frontend/       Next.js App Router application
DECISIONS.md    Design decisions and trade-offs
.env.example    Environment variables
```

---

## Author

Lagnasha Tripathy
B.Tech CSE, ITER, SOA University
