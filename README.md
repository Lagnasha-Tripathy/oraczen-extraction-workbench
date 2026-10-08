# Oraczen Extraction Workbench

A review tool for LLM-extracted support-ticket records. Raw tickets are turned into structured records, every output is validated against a strict schema, a failed extraction is retried once, and anything still doubtful goes to a human reviewer.

**Stack:** FastAPI (Python) backend and Next.js (App Router, TypeScript) frontend. Runs with **no API key** using a deterministic mock provider.

**Live demo:** https://frontend-woad-chi-lb8qq4qx8a.vercel.app
**Backend API:** https://oraczen-backend-ugoa.onrender.com (the free instance sleeps when idle, so the first request after inactivity can take ~30 seconds)

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
