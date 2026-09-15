
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes.auth import router as auth_router
from backend.routes.projects import router as projects_router
from backend.routes.project_compensation import router as project_compensation_router
from backend.routes.land_records import router as land_router
from backend.routes.ml import router as ml_router
from backend.routes.dashboard import router as dashboard_router
from backend.routes.gis import router as gis_router
from backend.routes.documents import router as documents_router
from backend.routes.ocr import router as ocr_router
from backend.routes.alerts import router as alerts_router
from backend.routes.audit import router as audit_router
from backend.routes.citizen import router as citizen_router
from backend.routes.field import router as field_router
from backend.routes.analytics import router as analytics_router
from backend.routes.sla import router as sla_router
from backend.routes.reports import router as reports_router
from backend.routes.grievances import router as grievances_router
from backend.routes.compensation import router as compensation_router
from backend.routes.intelligence import router as intelligence_router
from backend.routes.rr import router as rr_router
from backend.routes.sms import router as sms_router
from backend.routes.privacy import router as privacy_router
from backend.routes.data_quality import router as data_quality_router
from backend.routes.dss import router as dss_router
import os
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIST = ROOT / "frontend" / "dist"

app = FastAPI(title="SURVI / LANDNEXUS — Land Acquisition Intelligence API", version="2.0.0")

raw_cors = os.getenv("CORS_ORIGINS", "*").strip()
if raw_cors == "*":
    origins = ["*"]
else:
    origins = [o.strip() for o in raw_cors.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router,prefix="/auth",tags=["Authentication"]); app.include_router(projects_router,prefix="/projects",tags=["Projects"]); app.include_router(project_compensation_router,prefix="/projects",tags=["Project Compensation"]); app.include_router(land_router,prefix="/land-records",tags=["Parcels"]); app.include_router(ml_router,prefix="/ml",tags=["ML"]); app.include_router(dashboard_router,prefix="/dashboard",tags=["Command Center"]); app.include_router(gis_router,prefix="/gis",tags=["GIS"]); app.include_router(documents_router,prefix="/documents",tags=["Documents"]); app.include_router(ocr_router,prefix="/ocr",tags=["OCR"]); app.include_router(alerts_router,prefix="/alerts",tags=["Alerts"]); app.include_router(audit_router,prefix="/audit",tags=["Audit"]); app.include_router(citizen_router,prefix="/citizen",tags=["Citizen"]); app.include_router(field_router,prefix="/field",tags=["Field Operations"]); app.include_router(analytics_router,prefix="/analytics",tags=["Analytics"])
app.include_router(sla_router, prefix="/sla", tags=["SLA & Timelines"])
app.include_router(reports_router, prefix="/reports", tags=["Reports"])
app.include_router(grievances_router, prefix="/grievances", tags=["Grievances"])
app.include_router(compensation_router, prefix="/compensation", tags=["Compensation"])
app.include_router(intelligence_router, prefix="/intelligence", tags=["Intelligence"])
app.include_router(rr_router, prefix="/rr", tags=["R&R — Rehabilitation & Resettlement"])
app.include_router(sms_router, prefix="/sms", tags=["SMS Notifications"])
app.include_router(sms_router, prefix="/api/sms", tags=["SMS API"])
app.include_router(privacy_router, prefix="/privacy", tags=["Purpose-Aware Acquisition Privacy Guard"])
app.include_router(privacy_router, prefix="/api/privacy", tags=["Purpose-Aware Acquisition Privacy Guard"])
app.include_router(data_quality_router, prefix="/data-quality", tags=["Data Quality & Verification"])
app.include_router(data_quality_router, prefix="/api/data-quality", tags=["Data Quality & Verification"])
app.include_router(dss_router, prefix="/dss", tags=["Decision Support System"])
app.include_router(dss_router, prefix="/api/dss", tags=["Decision Support System API"])

@app.get("/health")
def health(): return {"status":"ok"}

@app.get("/api/health")
def api_health(): return {"status": "ok", "message": "API connection successful"}

@app.get("/api/projects")
def api_projects():
    from backend.core import conn
    c = conn()
    rows = [dict(r) for r in c.execute("SELECT * FROM projects LIMIT 5").fetchall()]
    c.close()
    return {"items": rows}

if FRONTEND_DIST.exists():
    if (FRONTEND_DIST / "assets").exists():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = FRONTEND_DIST / full_path
        if full_path and file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        index_file = FRONTEND_DIST / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return JSONResponse({"status": "error", "message": "Frontend build not found"}, status_code=404)
else:
    @app.get("/")
    def root(): return {"name":"SURVI / LANDNEXUS","status":"running","version":"2.0.0","focus":"SIH 26016 with integrated intelligence layers"}
