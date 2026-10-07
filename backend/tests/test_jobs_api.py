import asyncio
import pytest
from httpx import AsyncClient, ASGITransport

from app.config import TICKETS_FILE_PATH
from app import store
from app.main import app


@pytest.fixture(autouse=True)
def setup_store():
    """Ensure tickets are loaded in store before running tests."""
    if not store.tickets:
        store.load_tickets(TICKETS_FILE_PATH)


@pytest.mark.asyncio
async def test_create_job_returns_202_immediately():
    """
    Verifies that POST /api/jobs returns HTTP 202 Accepted immediately
    with a generated job_id and initial queued state.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"ticket_ids": ["tkt_0001", "tkt_0002"]}
        response = await client.post("/api/jobs", json=payload)

        assert response.status_code == 202, f"Expected 202 but got {response.status_code}"
        data = response.json()
        assert "id" in data, "Response must include job id"
        assert data["id"].startswith("job_")
        assert data["total"] == 2
        assert data["status"] in ["queued", "running"]


@pytest.mark.asyncio
async def test_create_job_empty_tickets_returns_400():
    """
    Verifies that POST /api/jobs returns HTTP 400 Bad Request
    when ticket_ids is empty.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/jobs", json={"ticket_ids": []})
        assert response.status_code == 400
        assert "ticket_ids cannot be empty" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_job_progress_and_completion():
    """
    Verifies that GET /api/jobs/{id} tracks progress as background worker runs,
    and completes successfully.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Start a job with 2 tickets
        start_res = await client.post("/api/jobs", json={"ticket_ids": ["tkt_0001", "tkt_0002"]})
        assert start_res.status_code == 202
        job_id = start_res.json()["id"]

        # Poll GET /api/jobs/{job_id} until completed (or timeout)
        completed = False
        for _ in range(20):  # max 4 seconds
            status_res = await client.get(f"/api/jobs/{job_id}")
            assert status_res.status_code == 200
            job_data = status_res.json()
            assert "progress_percent" in job_data
            assert "status" in job_data

            if job_data["status"] == "completed":
                completed = True
                assert job_data["progress_percent"] == 100.0
                assert job_data["completed"] == 2
                break

            await asyncio.sleep(0.1)

        assert completed, "Background job did not finish in time"


@pytest.mark.asyncio
async def test_get_job_results():
    """
    Verifies that GET /api/jobs/{id}/results returns extracted records
    with the attached raw ticket for reviewer display.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Start a job
        start_res = await client.post("/api/jobs", json={"ticket_ids": ["tkt_0001"]})
        job_id = start_res.json()["id"]

        # Wait for the single ticket to finish
        for _ in range(20):
            status_res = await client.get(f"/api/jobs/{job_id}")
            if status_res.json()["status"] == "completed":
                break
            await asyncio.sleep(0.1)

        # Fetch results
        results_res = await client.get(f"/api/jobs/{job_id}/results")
        assert results_res.status_code == 200
        records = results_res.json()
        assert len(records) == 1

        rec = records[0]
        assert rec["ticket_id"] == "tkt_0001"
        assert rec["status"] == "done"
        assert rec["extracted"]["product"] == "Zen Orchestrator"
        assert "ticket" in rec
        assert rec["ticket"]["id"] == "tkt_0001"
        assert "Castlerock Mining" in rec["ticket"]["body"]


@pytest.mark.asyncio
async def test_unknown_job_returns_404():
    """
    Verifies that non-existent job IDs return HTTP 404 for both
    status and results endpoints.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res1 = await client.get("/api/jobs/job_nonexistent_123")
        assert res1.status_code == 404
        assert "not found" in res1.json()["detail"].lower()

        res2 = await client.get("/api/jobs/job_nonexistent_123/results")
        assert res2.status_code == 404
        assert "not found" in res2.json()["detail"].lower()
