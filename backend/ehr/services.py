from uuid import uuid4


def sync_ehr_record_stub(record):
    return {
        "accepted": True,
        "external_id": f"stub-ehr-{uuid4()}",
        "record_id": record.pk,
        "message": "Stubbed EHR sync completed. No real network call was made.",
    }
