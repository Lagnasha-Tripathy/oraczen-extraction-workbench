import asyncio
import csv
import io
import pytest
from httpx import AsyncClient, ASGITransport

from app.config import TICKETS_FILE_PATH
from app import store
from app.main import app


@pytest.fixture(autouse=True)
def setup_store():
    """Ensure tickets are loaded into memory before running tests."""
    if not store.tickets:
        store.load_tickets(TICKETS_FILE_PATH)


@pytest.mark.asyncio
async def test_patch_valid_human_edit():
    """
    TEST 1: Valid human correction.
    - Process a record (tkt_0001).
    - Send PATCH to modify severity and requested_action.
    - Assert HTTP 200.
    - Assert updated values are saved.
    - Assert updated fields are tracked in edited_fields.
    - Assert untouched fields remain unchanged.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Start a job to produce a record
        start_res = await client.post("/api/jobs", json={"ticket_ids": ["tkt_0001"]})
        assert start_res.status_code == 202
        job_id = start_res.json()["id"]

        # Wait for ticket to complete
        for _ in range(20):
            status_res = await client.get(f"/api/jobs/{job_id}")
            if status_res.json()["status"] == "completed":
                break
            await asyncio.sleep(0.1)

        # Verify initial extracted state
        initial_record = store.get_record("tkt_0001")
        assert initial_record is not None
        assert initial_record["extracted"]["severity"] == "low"
        assert initial_record["extracted"]["requested_action"] == "none"
        assert "severity" not in initial_record.get("edited_fields", [])

        # 2. Apply human correction
        patch_payload = {
            "severity": "high",
            "requested_action": "callback",
        }
        patch_res = await client.patch("/api/records/tkt_0001", json=patch_payload)
        assert patch_res.status_code == 200
        updated = patch_res.json()

        # 3. Assertions
        assert updated["extracted"]["severity"] == "high"
        assert updated["extracted"]["requested_action"] == "callback"
        assert "severity" in updated["edited_fields"]
        assert "requested_action" in updated["edited_fields"]

        # Assert untouched fields (e.g. company, product) are preserved
        assert updated["extracted"]["company"] == initial_record["extracted"]["company"]
        assert updated["extracted"]["product"] == initial_record["extracted"]["product"]


@pytest.mark.asyncio
async def test_patch_invalid_edit_rejected_and_unchanged():
    """
    TEST 2: Invalid human edit.
    - Send an invalid enum value (e.g. severity: 'extreme').
    - Verify validation failure (HTTP 422).
    - Verify original record remains completely unchanged.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Ensure record exists
        await client.post("/api/jobs", json={"ticket_ids": ["tkt_0001"]})
        await asyncio.sleep(0.3)

        before_record = store.get_record("tkt_0001")
        original_severity = before_record["extracted"]["severity"]

        # Attempt to patch with invalid enum
        invalid_payload = {"severity": "extreme"}
        patch_res = await client.patch("/api/records/tkt_0001", json=invalid_payload)
        assert patch_res.status_code == 422

        # Verify original record remained unchanged
        after_record = store.get_record("tkt_0001")
        assert after_record["extracted"]["severity"] == original_severity
        assert "severity" not in after_record.get("edited_fields", [])


@pytest.mark.asyncio
async def test_patch_unknown_record_returns_404():
    """
    TEST 3: Unknown record ID returns HTTP 404.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        patch_res = await client.patch(
            "/api/records/tkt_nonexistent_9999",
            json={"severity": "high"},
        )
        assert patch_res.status_code == 404
        assert "not found" in patch_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_csv_export_valid_job():
    """
    TEST 4: CSV Export for a completed job.
    - Verifies HTTP 200.
    - Verifies text/csv content type and Content-Disposition header.
    - Verifies header row and content rows.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Start a job with 2 tickets
        start_res = await client.post("/api/jobs", json={"ticket_ids": ["tkt_0001", "tkt_0002"]})
        job_id = start_res.json()["id"]

        for _ in range(20):
            status_res = await client.get(f"/api/jobs/{job_id}")
            if status_res.json()["status"] == "completed":
                break
            await asyncio.sleep(0.1)

        # Call export endpoint
        export_res = await client.get(f"/api/jobs/{job_id}/export.csv")
        assert export_res.status_code == 200
        assert "text/csv" in export_res.headers.get("content-type", "")
        assert f"job_{job_id}_export.csv" in export_res.headers.get("content-disposition", "")

        # Parse CSV text
        csv_text = export_res.text
        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)

        # Verify headers
        headers = rows[0]
        expected_headers = [
            "ticket_id",
            "status",
            "company",
            "product",
            "category",
            "severity",
            "requested_action",
            "refund_amount",
            "deadline",
            "escalated",
            "retry_count",
            "edited_fields",
        ]
        assert headers == expected_headers

        # Verify data rows
        data_rows = rows[1:]
        assert len(data_rows) == 2
        ticket_ids_in_csv = [r[0] for r in data_rows]
        assert "tkt_0001" in ticket_ids_in_csv
        assert "tkt_0002" in ticket_ids_in_csv


@pytest.mark.asyncio
async def test_csv_export_handles_needs_review_and_failed_without_crash():
    """
    TEST 5: CSV export for jobs containing needs_review (tkt_0004) and failed records.
    - Verifies missing extracted fields output as empty cells without throwing errors.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # tkt_0004 is designed to fail validation twice and land in needs_review
        start_res = await client.post("/api/jobs", json={"ticket_ids": ["tkt_0004"]})
        job_id = start_res.json()["id"]

        for _ in range(20):
            status_res = await client.get(f"/api/jobs/{job_id}")
            if status_res.json()["status"] == "completed":
                break
            await asyncio.sleep(0.1)

        export_res = await client.get(f"/api/jobs/{job_id}/export.csv")
        assert export_res.status_code == 200

        reader = csv.reader(io.StringIO(export_res.text))
        rows = list(reader)
        assert len(rows) == 2  # header + 1 record

        row = rows[1]
        assert row[0] == "tkt_0004"
        assert row[1] == "needs_review"
        # Extracted fields should be empty strings without crashing
        assert row[2] == ""  # company
        assert row[3] == ""  # product


@pytest.mark.asyncio
async def test_patch_needs_review_partial_edit_and_resolution():
    """
    TEST 6: Human editing on a needs_review record (e.g. tkt_0004).
    1. Verify initial status is needs_review.
    2. Edit ONE valid field (company="Sunbelt") while other required fields are still missing.
       - Assert HTTP 200.
       - Assert company is saved.
       - Assert status remains needs_review.
       - Assert edited_fields contains only ['company'].
    3. Send an invalid field edit (severity="extreme").
       - Assert HTTP 422.
       - Assert invalid value is not saved.
    4. Provide the remaining required fields.
       - Assert HTTP 200.
       - Assert record status flips from needs_review to done.
       - Assert validation_errors is cleared to None.
       - Assert all human-edited fields are in edited_fields.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create job with tkt_0004 (designed to fail validation twice and land in needs_review)
        start_res = await client.post("/api/jobs", json={"ticket_ids": ["tkt_0004"]})
        job_id = start_res.json()["id"]

        for _ in range(20):
            status_res = await client.get(f"/api/jobs/{job_id}")
            if status_res.json()["status"] == "completed":
                break
            await asyncio.sleep(0.1)

        # 1. Verify initial status is needs_review
        rec = store.get_record("tkt_0004")
        assert rec is not None
        assert rec["status"] == "needs_review"

        # 2. Edit ONLY one valid field ('company')
        patch1_res = await client.patch(
            "/api/records/tkt_0004",
            json={"company": "Sunbelt"}
        )
        assert patch1_res.status_code == 200
        data1 = patch1_res.json()
        assert data1["extracted"]["company"] == "Sunbelt"
        assert data1["status"] == "needs_review"
        assert data1["edited_fields"] == ["company"]
        assert data1["validation_errors"] is not None

        # 3. Try invalid edit ('severity': 'extreme') -> rejected with 422
        bad_patch_res = await client.patch(
            "/api/records/tkt_0004",
            json={"severity": "extreme"}
        )
        assert bad_patch_res.status_code == 422
        # Verify company is still 'Sunbelt' and severity was not saved
        rec_after_bad = store.get_record("tkt_0004")
        assert rec_after_bad["extracted"]["company"] == "Sunbelt"
        assert "severity" not in rec_after_bad.get("edited_fields", [])

        # 4. Fill in remaining required fields to resolve the record
        patch2_res = await client.patch(
            "/api/records/tkt_0004",
            json={
                "product": "Zen Connect",
                "category": "bug",
                "severity": "low",
                "requested_action": "none",
                "escalated": False,
            }
        )
        assert patch2_res.status_code == 200
        data2 = patch2_res.json()
        assert data2["status"] == "done"
        assert data2["validation_errors"] is None
        assert data2["extracted"]["company"] == "Sunbelt"
        assert data2["extracted"]["product"] == "Zen Connect"
        assert set(data2["edited_fields"]) == {
            "company",
            "product",
            "category",
            "severity",
            "requested_action",
            "escalated",
        }

