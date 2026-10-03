from fastapi import APIRouter

from app.api import ai, auth, dashboard, documents, escalations, events, grievances, notifications
from app.core.config import settings

api_router = APIRouter(prefix=settings.API_V1_PREFIX)
for module in (auth, dashboard, grievances, events, documents, notifications, escalations, ai):
    api_router.include_router(module.router)
