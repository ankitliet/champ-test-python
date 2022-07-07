#IMPORTING ROUTER
from fastapi import APIRouter
from core.app.api import orchestrator_API, dashboard_API, infracost, cloud_master, sso, reports

#DECLARING BASE ROUTER
router = APIRouter()

router.include_router(sso.subapi)
router.include_router(sso.oauthapi)
router.include_router(reports.subapi)
router.include_router(orchestrator_API.subapi)
router.include_router(infracost.cost_api)
router.include_router(cloud_master.subapi)
router.include_router(orchestrator_API.notification_subapi)
router.include_router(orchestrator_API.freshservice_subapi)
router.include_router(orchestrator_API.admin_subapi)
router.include_router(dashboard_API.subapi)
