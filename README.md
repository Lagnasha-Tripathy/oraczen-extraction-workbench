
# Oraczen Extraction Workbench

A simple Human-in-the-Loop extraction system for processing customer support tickets.

The application takes raw support tickets, extracts structured information using a deterministic mock provider, validates the result, retries once if validation fails, and sends records that still fail to `needs_review` for human correction.

## Tech Stack

- **Backend:** Python, FastAPI, Pydantic, asyncio
- **Frontend:** Next.js, React, TypeScript, Tailwind CSS
- **Testing:** Pytest
- **Storage:** In-memory storage
- **Provider:** Deterministic mock provider

No database, API key, Redis, Docker, or external LLM is required.

## Main Features

- Browse, search, and filter 150 support tickets
- Select multiple tickets and start an extraction job
- Background processing with configurable concurrency
- Strict Pydantic validation
- Exactly one retry after validation failure
- `needs_review` handling for records that fail twice
- Per-field confidence and grounding information
- Human editing with validation
- Tracks model-generated and human-edited fields
- Live job progress through polling
- CSV export of results
- Deterministic failure cases for testing

## Project Structure

```text
oraczen-extraction-workbench/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── schemas.py
│   │   ├── store.py
│   │   ├── worker.py
│   │   ├── mock_provider.py
│   │   └── routes/
│   ├── tests/
│   └── requirements.txt
├── frontend/
├── data/
│   └── tickets.jsonl
├── DECISIONS.md
└── README.md
```
Setup
Prerequisites

Make sure you have:

Python 3.11+
Node.js 18+
npm
1. Clone the repository
git clone https://github.com/Lagnasha-Tripathy/oraczen-extraction-workbench.git
cd oraczen-extraction-workbench
2. Start the Backend

Create and activate a virtual environment:

python3 -m venv .venv
source .venv/bin/activate

Install the dependencies:

cd backend
pip install -r requirements.txt

Start the server:

uvicorn app.main:app --reload --port 8000

The backend will run at:

http://localhost:8000

You can check that it is running at:

http://localhost:8000/health

FastAPI documentation is available at:

http://localhost:8000/docs
3. Start the Frontend

Open a new terminal and go to the frontend:

cd oraczen-extraction-workbench/frontend
npm install

Create a .env.local file:

NEXT_PUBLIC_API_URL=http://localhost:8000

Start the frontend:

npm run dev

The frontend will run at:

http://localhost:3000

Open that URL in your browser to use the application.

Configuration

The application uses the deterministic mock provider by default.

LLM_PROVIDER=mock
MAX_CONCURRENCY=5

MAX_CONCURRENCY controls how many tickets can be processed at the same time.

No external API key is needed.

Application Flow
1. Select Tickets

The home page displays the available support tickets.

Users can search, filter by channel, select individual tickets, or select multiple tickets.

2. Start a Job

When the user starts extraction, the backend immediately creates a job and returns a job ID with HTTP 202.

The actual processing continues in the background.

3. Extract and Validate

Each ticket is sent to the mock provider.

The returned data is validated against the required Pydantic schema.

4. Retry Failed Extraction

If validation fails, the system retries the extraction exactly once and provides the validation error as feedback.

If the second attempt succeeds, the record is marked as done.

If it fails again, the record is marked as needs_review.

5. Human Review

Records requiring review are highlighted in the UI.

The reviewer can see:

Original ticket content
Extracted fields
Validation errors
Model-generated fields
Human-edited fields

The reviewer can correct the fields and save the record.

The edited data goes through the same validation process before being accepted.

6. Export

Once processing is complete, the user can export the results as a CSV file.

API Endpoints
GET    /api/tickets
POST   /api/jobs
GET    /api/jobs/{job_id}
GET    /api/jobs/{job_id}/results
PATCH  /api/records/{record_id}
GET    /api/jobs/{job_id}/export.csv
Testing
Backend Tests

From the backend directory:

pytest -q

The tests cover validation, retry behavior, job processing, human edits, and CSV export.

Frontend Build

From the frontend directory:

npm run build

This checks that the Next.js application builds successfully.

Important Test Cases

The dataset contains specific tickets for testing different scenarios:

tkt_0020: First extraction fails validation, second attempt succeeds.
tkt_0004: Both attempts fail, so the record goes to needs_review.
tkt_0058: French-language ticket with EUR information.
tkt_0089: Ticket containing multiple issues.
tkt_0105: Ticket containing typing errors.
tkt_0131: Phone transcript with verbal amounts.
Design Decisions

The project intentionally uses a simple architecture because the assignment focuses on extraction, validation, retries, and human review.

In-memory storage: Sufficient for the 150-ticket dataset and keeps setup simple.
Mock provider: Makes the application deterministic and removes the need for external API keys.
Polling: Used for job progress instead of adding WebSocket infrastructure.
Pydantic: Provides consistent validation for both model output and human edits.
One retry: Follows the assignment requirement and prevents endless retries.
Configurable concurrency: Prevents unlimited extraction tasks from running simultaneously.

Additional decisions and trade-offs are documented in DECISIONS.md.

Deployment

The frontend and backend can be deployed separately.

For the deployed frontend, set:

NEXT_PUBLIC_API_URL=https://YOUR-BACKEND-URL

The backend can continue using:

LLM_PROVIDER=mock

No external AI service or API key is required.

Limitations
Job and record data is stored in memory, so it is cleared when the backend restarts.
The extraction provider is a deterministic mock provider rather than a real LLM.
Authentication is not included because it is outside the scope of the assignment.
Polling is used for progress updates instead of WebSockets.
Assignment Coverage
 Background extraction jobs
 HTTP 202 job creation
 Configurable concurrency
 Strict Pydantic validation
 One retry on validation failure
 Validation error feedback
 needs_review handling
 Confidence and grounding
 Human editing
 Model vs human field tracking
 Search and filtering
 Job progress
 CSV export
 Deterministic mock provider
 Backend tests
 Frontend production build
Author

Lagnasha Tripathy
B.Tech CSE, ITER, SOA University
