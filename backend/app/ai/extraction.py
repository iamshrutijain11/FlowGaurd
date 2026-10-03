"""Document extraction – Person 4.

Reads uploaded PDFs/images and extracts structured data.
Call `services.document_service.update_extraction_result` to persist
the result and update `extraction_status`.

Signature to implement:
    async def extract(document_id: uuid.UUID, db: Session) -> dict
"""
