import asyncio
import pytest

from app.config import TICKETS_FILE_PATH
from app import store
from app.worker import process_ticket, process_job, _update_job_progress_in_lock


@pytest.fixture(autouse=True)
def ensure_tickets_loaded():
    """Ensure raw tickets are loaded into store before each test runs."""
    if not store.tickets:
        store.load_tickets(TICKETS_FILE_PATH)


@pytest.mark.asyncio
async def test_ticket_retry_recovers():
    """
    TEST 1: tkt_0010
    Attempt 1 fails schema validation.
    Attempt 2 succeeds.
    Final status should be 'done' with retry_count = 1.
    """
    job_id = "test_job_retry"
    store.create_job(job_id, ["tkt_0010"])
    semaphore = asyncio.Semaphore(5)

    record = await process_ticket(job_id, "tkt_0010", semaphore)

    # Assertions
    assert record["status"] == "done", f"Expected 'done' but got {record['status']}"
    assert record["retry_count"] == 1, f"Expected retry_count=1 but got {record['retry_count']}"
    assert record["extracted"] is not None, "Expected extracted data to be populated"
    assert record["extracted"]["company"] == "Bluepeak Retail"
    assert record["validation_errors"] is None, "Validation errors should be cleared upon successful retry"


@pytest.mark.asyncio
async def test_ticket_double_failure_needs_review():
    """
    TEST 2: tkt_0017
    Attempt 1 fails schema validation.
    Attempt 2 also fails schema validation.
    Final status should be 'needs_review' with retry_count = 1,
    retaining raw_output and validation_errors.
    """
    job_id = "test_job_needs_review"
    store.create_job(job_id, ["tkt_0017"])
    semaphore = asyncio.Semaphore(5)

    record = await process_ticket(job_id, "tkt_0017", semaphore)

    # Assertions
    assert record["status"] == "needs_review", f"Expected 'needs_review' but got {record['status']}"
    assert record["retry_count"] == 1, f"Expected retry_count=1 but got {record['retry_count']}"
    assert record["raw_output"] is not None, "Expected raw_output to be preserved"
    assert record["validation_errors"] is not None and len(record["validation_errors"]) > 0, (
        "Expected validation_errors to be preserved"
    )
    assert record["extracted"] is None, "Extracted should be None since schema validation failed"


@pytest.mark.asyncio
async def test_progress_arithmetic_and_completion():
    """
    TEST 3: Progress arithmetic
    Verifies that:
    - total = completed + needs_review + failed
    - progress_percent reaches 100.0%
    - job status flips to 'completed'
    """
    job_id = "test_job_progress"
    # Choose a batch of tickets:
    # - tkt_0001 (done on attempt 1)
    # - tkt_0002 (done on attempt 1)
    # - tkt_0003 (done on attempt 1)
    # - tkt_0010 (done on attempt 2)
    # - tkt_0017 (needs_review on attempt 2)
    ticket_ids = ["tkt_0001", "tkt_0002", "tkt_0003", "tkt_0010", "tkt_0017"]
    store.create_job(job_id, ticket_ids)

    # Execute the entire job using process_job
    job = await process_job(job_id)

    # Progress arithmetic assertions
    total = job["total"]
    completed = job["completed"]
    needs_review = job["needs_review"]
    failed = job["failed"]

    assert total == len(ticket_ids)
    assert completed == 4  # tkt_0001, tkt_0002, tkt_0003, tkt_0010
    assert needs_review == 1  # tkt_0017
    assert failed == 0

    # completed + needs_review + failed must equal total
    processed_count = completed + needs_review + failed
    assert processed_count == total

    # Progress percentage must be 100%
    assert job["progress_percent"] == 100.0

    # Job status must flip to 'completed'
    assert job["status"] == "completed"
    assert job["queued"] == 0
    assert job["running"] == 0


def test_progress_formula_standalone():
    """
    Unit test verifying the arithmetic formula in isolation:
    total = 10, completed = 7, needs_review = 2, failed = 1 -> progress = 100%, status = completed
    """
    job_id = "test_formula"
    store.create_job(job_id, [f"fake_{i}" for i in range(10)])
    job = store.get_job(job_id)

    # Manually simulate 7 completed, 2 needs_review, 1 failed
    for _ in range(7):
        _update_job_progress_in_lock(job_id, "done")
    for _ in range(2):
        _update_job_progress_in_lock(job_id, "needs_review")
    for _ in range(1):
        _update_job_progress_in_lock(job_id, "failed")

    assert job["completed"] == 7
    assert job["needs_review"] == 2
    assert job["failed"] == 1
    assert job["completed"] + job["needs_review"] + job["failed"] == 10
    assert job["progress_percent"] == 100.0
    assert job["status"] == "completed"
