from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError

from app import store
from app.schemas import ExtractedRecord, RecordPatch

router = APIRouter(tags=["Records"])


@router.patch("/api/records/{record_id}")
async def patch_record(record_id: str, patch: RecordPatch):
    """
    Applies human corrections to any extracted field.

    1. Looks up the existing record (returns 404 if not found).
    2. Merges human-provided fields with existing values.
    3. Validates the complete merged result against ExtractedRecord.
    4. If invalid, rejects with 422 and leaves original record untouched.
    5. If valid, saves changes and marks only fields whose value
       actually changed in edited_fields.
    """
    record = store.get_record(record_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Record '{record_id}' not found",
        )

    # Only inspect fields explicitly supplied in the request body
    patch_data = patch.model_dump(exclude_unset=True)
    if not patch_data:
        return record

    # Base dictionary: current extracted values, or empty dict if previously failed/skipped
    current_extracted = record.get("extracted") or {}
    merged_data = {**current_extracted, **patch_data}

    # Validate the merged result against the exact same schema used for model output
    try:
        validated_record = ExtractedRecord(**merged_data)
    except ValidationError as err:
        error_messages = [
            f"{'.'.join(str(loc) for loc in e.get('loc', []))}: {e.get('msg')}"
            for e in err.errors()
        ]
        # Reject the edit and leave the original record completely unchanged
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"errors": error_messages},
        )

    # Save changes under lock
    async with store.lock:
        new_extracted = validated_record.model_dump()
        record["extracted"] = new_extracted

        if "edited_fields" not in record:
            record["edited_fields"] = []

        # Compare validated values on both sides so types match (e.g. dates),
        # and only mark fields whose value really changed
        for field_name in patch_data.keys():
            if new_extracted.get(field_name) != current_extracted.get(field_name):
                if field_name not in record["edited_fields"]:
                    record["edited_fields"].append(field_name)

        # A successful human correction resolves a needs_review record to 'done'
        if record.get("status") == "needs_review":
            record["status"] = "done"
            record["validation_errors"] = None

        store.save_record(record["id"], record)

    return record