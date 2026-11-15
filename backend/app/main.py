import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import ai, analytics, chat, documents, system
from app.core.config import settings
from app.db.database import init_db
from app.services.errors import AiGenerationError, OllamaError

logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO)
log = logging.getLogger("studymate")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.ensure_dirs()
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=system.VERSION,
    description="Local AI study assistant: RAG over your own PDFs. Interactive docs below.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)


@app.exception_handler(OllamaError)
async def _ollama_error(_request: Request, exc: OllamaError):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(AiGenerationError)
async def _generation_error(_request: Request, exc: AiGenerationError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def _unexpected(_request: Request, exc: Exception):
    log.exception("Unhandled error")  # the stack trace goes to the log, never to the browser
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


for router in (system.router, documents.router, chat.router, ai.router, analytics.router):
    app.include_router(router)
