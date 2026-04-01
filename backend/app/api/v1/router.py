from fastapi import APIRouter

from app.api.v1.analytics import router as analytics_router
from app.api.v1.chat import router as chat_router
from app.api.v1.clearances import router as clearances_router
from app.api.v1.documents import router as documents_router
from app.api.v1.health import router as health_router
from app.api.v1.parcels import router as parcels_router
from app.api.v1.pathfinder import router as pathfinder_router
from app.api.v1.projects import router as projects_router
from app.api.v1.reports import router as reports_router
from app.api.v1.staff import router as staff_router
from app.api.v1.users import router as users_router
from app.api.v1.admin import router as admin_router
from app.api.v1.compliance import router as compliance_router
from app.api.v1.inspections import router as inspections_router
from app.api.v1.monitoring import router as monitoring_router
from app.api.v1.websocket import router as websocket_router
from app.api.v1.impact import router as impact_router

v1_router = APIRouter()

v1_router.include_router(health_router)
v1_router.include_router(projects_router)
v1_router.include_router(clearances_router)
v1_router.include_router(parcels_router)
v1_router.include_router(users_router)
v1_router.include_router(pathfinder_router)
v1_router.include_router(staff_router)
v1_router.include_router(chat_router)
v1_router.include_router(documents_router)
v1_router.include_router(analytics_router)
v1_router.include_router(reports_router)
v1_router.include_router(websocket_router)
v1_router.include_router(admin_router)
v1_router.include_router(compliance_router)
v1_router.include_router(monitoring_router)
v1_router.include_router(inspections_router)
v1_router.include_router(impact_router)
