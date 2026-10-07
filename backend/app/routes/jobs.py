import asyncio
import uuid
from fastapi import APIRouter, HTTPException, status

from app import store
from app.schemas import JobCreateRequest
from app.worker import process_job

router = APIRouter(tags=["Jobs"])


@router.post("/api/jobs", status_code=status.HTTP_202_ACCEPTED)
async def create_job(request: JobCreateRequest):
    """
    Starts an extraction job for a list of ticket IDs.
    Returns HTTP 202 Accepted immediately and processes tickets in the background.
    """
    if not request.ticket_ids:
        raise HTTPException(
            status_code=400,
            detail="ticket_ids cannot be empty",
        )

    # Generate a unique job ID (e.g. job_a1b2c3d4)
    job_id = f"job_{uuid.uuid4().hex[:8]}"

    # Initialize the job in the in-memory store
    job = store.create_job(job_id, request.ticket_ids)

    # Launch processing in the background without awaiting
    asyncio.create_task(process_job(job_id))

    # Return HTTP 202 immediately with the initial job status
    return job


@router.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    """
    Retrieves current job status, counters, and progress percentage.
    Returns HTTP 404 if the job does not exist.
    """
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' not found",
        )
    return job


@router.get("/api/jobs/{job_id}/results")
async def get_job_results(job_id: str):
    """
    Retrieves all extracted records belonging to a job.
    Attaches the original raw ticket to each record for convenient reviewer display.
    Returns HTTP 404 if the job does not exist.
    """
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' not found",
        )

    records = store.get_records_for_job(job_id)

    # Attach raw ticket details so the UI can display ticket prose side-by-side with extracted fields
    results = []
    for r in records:
        record_copy = dict(r)
        ticket = store.get_ticket(r.get("ticket_id"))
        record_copy["ticket"] = ticket.model_dump() if ticket else None
        results.append(record_copy)

    return results
