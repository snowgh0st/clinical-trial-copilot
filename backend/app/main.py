"""
backend/app/main.py

PURPOSE:
FastAPI application entry point. Configures middleware, routes, and CORS policy.

CALL STACK & INTEGRATION TRACE:
1. Entry point for Uvicorn ASGI server: `uvicorn backend.app.main:app --reload`
2. Mounts `router` from `backend/app/api/routes.py` under `/api/v1`.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import router as api_router

# Configure logging format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

app = FastAPI(
    title="Clinical Trial Copilot API",
    description="AI Engine for clinical trial matching using PyTorch BioBERT and pgvector RAG.",
    version="1.0.0"
)

# Enable CORS for Vite frontend (http://localhost:5173)
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Router
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Clinical Trial Copilot API is running. Access docs at /docs"}