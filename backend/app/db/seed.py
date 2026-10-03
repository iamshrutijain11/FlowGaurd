"""Idempotent demo seed. Run: python -m app.db.seed

Creates the ONE shared demo case used by every team member:
  user      demo@flowguard.app / Demo@12345
  grievance CMP-2026-DEMO-001, Demo Brokerage Pvt Ltd, stage AWAITING_RESPONSE
  events    Filed (20 Sep) -> Acknowledged (20 Sep) -> Awaiting Response (21 Sep); NO response event
No warning is seeded: the workflow engine (Person 3) generates the POTENTIAL_DELAY warning."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.document import Document
from app.models.enums import (
    DocumentType,
    EventSource,
    EventType,
    ExtractionStatus,
    GrievanceStage,
)
from app.models.grievance import Grievance
from app.models.user import User
from app.services import document_service, event_service

DEMO_EMAIL = "demo@flowguard.app"
DEMO_PASSWORD = "Demo@12345"
DEMO_COMPLAINT_ID = "CMP-2026-DEMO-001"

_MINI_PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 100]/Contents 4 0 R"
    b"/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
    b"4 0 obj<</Length 78>>stream\nBT /F1 12 Tf 10 60 Td (DEMO acknowledgement - CMP-2026-DEMO-001) Tj ET\nendstream endobj\n"
    b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"trailer<</Root 1 0 R/Size 6>>\n%%EOF\n"
)


def _dt(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 9, day, hour, minute, tzinfo=timezone.utc)


def seed_demo_data(db: Session) -> None:
    user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if not user:
        user = User(
            name="Demo Investor", email=DEMO_EMAIL,
            hashed_password=hash_password(DEMO_PASSWORD), preferred_language="en",
        )
        db.add(user)
        db.commit()

    grievance = db.scalar(
        select(Grievance).where(Grievance.user_id == user.id, Grievance.complaint_id == DEMO_COMPLAINT_ID)
    )
    if grievance:
        return

    grievance = Grievance(
        user_id=user.id,
        complaint_id=DEMO_COMPLAINT_ID,
        entity_name="Demo Brokerage Pvt Ltd",
        issue_type="Transaction related grievance",
        issue_description="Demo transaction grievance used for the FlowGuard walkthrough.",
        submission_date=_dt(20, 10),
        current_stage=GrievanceStage.AWAITING_RESPONSE,
        status_updated_at=_dt(21, 9),
    )
    db.add(grievance)
    db.flush()

    timeline = [
        (EventType.FILED, "Complaint filed.", EventSource.USER, _dt(20, 10)),
        (EventType.ACKNOWLEDGED, "Acknowledgement received.", EventSource.USER, _dt(20, 12)),
        (EventType.AWAITING_RESPONSE, "Status changed to Awaiting Response.", EventSource.SYSTEM, _dt(21, 9)),
    ]
    for etype, desc, source, when in timeline:
        event_service.create_event(
            db, grievance.id, etype, desc, source=source, event_time=when,
            metadata={"seed": True}, commit=False,
        )

    # Demo acknowledgement document (extraction PENDING -> Person 4's AI layer)
    rel = f"{grievance.id}/seed-acknowledgement.pdf"
    target = document_service.upload_root() / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(_MINI_PDF)
    db.add(Document(
        grievance_id=grievance.id, file_name="Acknowledgement.pdf", file_type="application/pdf",
        storage_path=rel, document_type=DocumentType.ACKNOWLEDGEMENT,
        uploaded_at=_dt(20, 12, 5), extraction_status=ExtractionStatus.PENDING,
    ))
    db.commit()


if __name__ == "__main__":
    with SessionLocal() as session:
        seed_demo_data(session)
    print(f"Seeded {DEMO_EMAIL} / {DEMO_PASSWORD} with {DEMO_COMPLAINT_ID}")
