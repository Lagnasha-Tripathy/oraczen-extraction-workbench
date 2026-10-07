from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app import store
from app.config import ALLOWED_ORIGINS, TICKETS_FILE_PATH
from app.routes.jobs import router as jobs_router
from app.routes.records import router as records_router
from app.schemas import Ticket, TicketListResponse




@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Loads raw tickets from JSONL into memory on startup.
    """
    count = store.load_tickets(TICKETS_FILE_PATH)
    print(f"[STARTUP] Successfully loaded {count} tickets into in-memory store from {TICKETS_FILE_PATH}")
    yield


app = FastAPI(
    title="Oraczen Extraction Workbench API",
    description="API for processing, reviewing, and correcting support ticket extractions",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for Next.js frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(jobs_router)
app.include_router(records_router)




@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint to verify backend status and loaded ticket count."""
    return {
        "status": "healthy",
        "tickets_count": len(store.tickets),
    }


@app.get("/api/tickets", response_model=TicketListResponse, tags=["Tickets"])
async def list_tickets(
    search: Optional[str] = Query(
        default=None,
        description="Search term matching id, subject, body, or from_email",
    ),
    channel: Optional[str] = Query(
        default=None,
        description="Filter by ticket channel: email, web_form, chat, phone_transcript",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=150,
        description="Maximum number of records to return",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of records to skip for pagination",
    ),
):
    """
    Lists raw tickets with optional search, channel filtering, and pagination.
    Used by the workbench UI to display and select tickets.
    """
    items, total = store.query_tickets(
        search=search,
        channel=channel,
        limit=limit,
        offset=offset,
    )
    return TicketListResponse(
        tickets=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@app.get("/api/tickets/{ticket_id}", response_model=Ticket, tags=["Tickets"])
async def get_single_ticket(ticket_id: str):
    """
    Fetches a single raw ticket by ID.
    Returns HTTP 404 if the ticket ID does not exist.
    """
    ticket = store.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=404,
            detail=f"Ticket '{ticket_id}' not found",
        )
    return ticket
