import sys
import os
# Ensure the arthraksha package root is always on sys.path, regardless of
# how uvicorn is invoked (e.g. `uvicorn arthraksha.api.main:app` from project root
# or `uvicorn api.main:app` from inside arthraksha/).
_HERE = os.path.dirname(os.path.abspath(__file__))
_ARTHRAKSHA_ROOT = os.path.dirname(_HERE)  # arthraksha/
if _ARTHRAKSHA_ROOT not in sys.path:
    sys.path.insert(0, _ARTHRAKSHA_ROOT)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config.database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run before any other service starts
    init_db()
    yield
    # Cleanup on shutdown

app = FastAPI(
    title="ArthRaksha",
    description="Autonomous AI Revenue Recovery & Payment Defense Engine",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware to allow the Dashboard HTML to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
import os

from api.routes import webhook, dashboard, auth
from api.routes.demo import router as demo_router
app.include_router(webhook.router)
app.include_router(dashboard.router)
app.include_router(auth.router)
app.include_router(demo_router)   # demo payment pages + confirm endpoint

# Mount the React frontend (must be LAST — catch-all)
dist_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
if os.path.exists(dist_path):
    app.mount("/", StaticFiles(directory=dist_path, html=True), name="frontend")


# from api.routes import batch
# app.include_router(batch.router)
# app.include_router(batch.router)
