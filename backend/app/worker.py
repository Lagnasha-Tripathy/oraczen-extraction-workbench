import asyncio
import re

from pydantic import ValidationError

from app.config import MAX_CONCURRENCY
from app.mock_provider import extract_ticket, get_confidence_scores
from app.schemas import ExtractedRecord
from app import store

CONFIDENCE_FIELDS = [
    "company",
    "product",
    "category",
    "severity",
    "requested_action",
    "refund_amount",
    "deadline",
    "escalated",
]


def _is_trivial(ticket) -> bool:
    """True when the body has too little real content to extract anything from."""
    body = ticket.get("body", "") if isinstance(ticket, dict) else ticket.body
    return len(re.sub(r"\W", "", body or "")) < 15


def _format_errors(err: ValidationError) -> list:
    return [
        f"{'.'.join(str(loc) for loc in e.get('loc', []))}: {e.get('msg')}"
        for e in err.errors()
    ]


def _update_job_progress_in_lock(job_id: str, item_final_status: str) -> None:
    """
    Helper function to update job metrics after a single ticket finishes.
    Must be called while holding store.lock.
    """
    job = store.get_job(job_id)
    if not job:
        return

    # Decrement running count as this item finished
    job["running"] = max(0, job["running"] - 1)

    # Increment status count
    if item_final_status == "done":
        job["completed"] += 1
        job["done"] += 1
    elif item_final_status == "needs_review":
        job["needs_review"] += 1
    elif item_final_status == "failed":
        job["failed"] += 1

    # Total processed so far: completed + needs_review + failed
    processed_count = job["completed"] + job["needs_review"] + job["failed"]
    total = job["total"]

    if total > 0:
        job["progress_percent"] = round((processed_count / total) * 100.0, 1)
    else:
        job["progress_percent"] = 100.0

    # Once every item is processed, flip job status to completed
    if processed_count >= total:
        job["status"] = "completed"


async def process_ticket(job_id: str, ticket_id: str, semaphore: asyncio.Semaphore) -> dict:
    """
    Processes a single ticket with concurrency control and exactly one retry.

    Flow:
    1. Acquire semaphore (capped by MAX_CONCURRENCY).
    2. If the body has nothing to extract -> needs_review, model not called.
    3. Attempt 1: call mock provider and validate with ExtractedRecord.
    4. If invalid -> retry once (attempt 2).
       - Valid on attempt 2 -> status = "done", retry_count = 1.
       - Invalid on attempt 2 -> status = "needs_review", retry_count = 1.
    5. Unexpected exception -> status = "failed".
    6. Save record and update job progress under the lock.
    """
    ticket = store.get_ticket(ticket_id)
    if not ticket:
        # Ticket ID does not exist in store
        record = {
            "id": ticket_id,
            "job_id": job_id,
            "ticket_id": ticket_id,
            "status": "failed",
            "extracted": None,
            "raw_output": None,
            "validation_errors": [f"Ticket '{ticket_id}' not found in store"],
            "retry_count": 0,
            "confidence": {},
            "edited_fields": [],
        }
        async with store.lock:
            store.save_record(ticket_id, record)
            _update_job_progress_in_lock(job_id, "failed")
        return record

    async with semaphore:
        # Move ticket from queued to running
        async with store.lock:
            job = store.get_job(job_id)
            if job:
                job["queued"] = max(0, job["queued"] - 1)
                job["running"] += 1

        # Skip the model entirely for tickets with nothing to extract
        # (the lock above is already released, so taking it again is safe)
        if _is_trivial(ticket):
            record = {
                "id": ticket_id,
                "job_id": job_id,
                "ticket_id": ticket_id,
                "status": "needs_review",
                "extracted": None,
                "raw_output": None,
                "validation_errors": [
                    "Ticket body has no extractable content; model not called."
                ],
                "retry_count": 0,
                "confidence": {},
                "edited_fields": [],
            }
            async with store.lock:
                store.save_record(ticket_id, record)
                _update_job_progress_in_lock(job_id, "needs_review")
            return record

        status = "failed"
        retry_count = 0
        extracted_data = None
        raw_output = None
        validation_errors = None

        try:
            # ----------------------------------------------------
            # ATTEMPT 1: Initial extraction
            # ----------------------------------------------------
            raw_output = await extract_ticket(ticket, attempt=1)
            try:
                validated = ExtractedRecord(**raw_output)
                status = "done"
                retry_count = 0
                extracted_data = validated.model_dump()
            except ValidationError as err1:
                # Attempt 1 failed schema validation -> retry once
                retry_count = 1
                validation_errors = _format_errors(err1)

                # ------------------------------------------------
                # ATTEMPT 2: Exactly one retry
                # ------------------------------------------------
                second_output = await extract_ticket(ticket, attempt=2)
                raw_output = second_output
                try:
                    validated = ExtractedRecord(**second_output)
                    status = "done"
                    extracted_data = validated.model_dump()
                    validation_errors = None
                except ValidationError as err2:
                    # Attempt 2 failed as well -> needs_review
                    status = "needs_review"
                    extracted_data = None
                    validation_errors = _format_errors(err2)

        except Exception as unexpected_err:
            # One bad ticket must never crash the job
            status = "failed"
            validation_errors = [f"Unexpected error: {str(unexpected_err)}"]

        # Calculate per-field confidence scores
        if extracted_data:
            confidence = get_confidence_scores(ticket, extracted_data)
        else:
            confidence = {field: 0.0 for field in CONFIDENCE_FIELDS}

        record = {
            "id": ticket_id,
            "job_id": job_id,
            "ticket_id": ticket_id,
            "status": status,
            "extracted": extracted_data,
            "raw_output": raw_output,
            "validation_errors": validation_errors,
            "retry_count": retry_count,
            "confidence": confidence,
            "edited_fields": [],
        }

        # Save record and update job counters safely
        async with store.lock:
            store.save_record(ticket_id, record)
            _update_job_progress_in_lock(job_id, status)

        return record


async def process_job(job_id: str) -> dict:
    """
    Processes all tickets belonging to a job concurrently up to MAX_CONCURRENCY.
    """
    job = store.get_job(job_id)
    if not job:
        raise ValueError(f"Job '{job_id}' not found")

    job["status"] = "running"
    ticket_ids = job["ticket_ids"]

    # Limit concurrency to MAX_CONCURRENCY tasks at a time
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

    tasks = [
        asyncio.create_task(process_ticket(job_id, t_id, semaphore))
        for t_id in ticket_ids
    ]

    await asyncio.gather(*tasks)

    # Mark the job completed
    async with store.lock:
        job["status"] = "completed"

    return job