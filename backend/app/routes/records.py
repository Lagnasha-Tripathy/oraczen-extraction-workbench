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
    3. Validates against ExtractedRecord.
       - For done records: must remain fully valid.
       - For needs_review records: valid supplied fields are saved even if other
         required fields are not yet complete, remaining needs_review until all
         required fields are provided and valid.
    4. Marks only fields whose value actually changed in edited_fields.
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
    current_extracted = dict(record.get("extracted") or {})
    merged_data = {**current_extracted, **patch_data}

    # Validate the merged result against ExtractedRecord
    is_fully_valid = False
    full_errors = []
    try:
        validated_record = ExtractedRecord(**merged_data)
        is_fully_valid = True
    except ValidationError as err:
        full_errors = [
            f"{'.'.join(str(loc) for loc in e.get('loc', []))}: {e.get('msg')}"
            for e in err.errors()
        ]

    # For valid (done) records, do NOT weaken validation: the merged record must be fully valid
    if record.get("status") != "needs_review" and not is_fully_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"errors": full_errors},
        )

    # Save changes under lock
    async with store.lock:
        if is_fully_valid:
            new_extracted = validated_record.model_dump()
            record["extracted"] = new_extracted
            if record.get("status") == "needs_review":
                record["status"] = "done"
                record["validation_errors"] = None
        else:
            # Record is in needs_review: save the valid supplied fields, but remain needs_review
            new_extracted = merged_data
            record["extracted"] = new_extracted
            record["validation_errors"] = full_errors

        if "edited_fields" not in record:
            record["edited_fields"] = []

        # Compare values on both sides, only mark fields whose value really changed
        for field_name, new_val in patch_data.items():
            if new_val != current_extracted.get(field_name):
                if field_name not in record["edited_fields"]:
                    record["edited_fields"].append(field_name)

        store.save_record(record["id"], record)

    return record