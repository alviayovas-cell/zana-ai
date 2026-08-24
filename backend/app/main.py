from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging_config import setup_logging, logger
from app.api.routes import health, chat, spotify, music


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info(f"🚀 {settings.APP_NAME} starting up ({settings.ENVIRONMENT})")
    yield
    logger.info(f"👋 {settings.APP_NAME} shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(spotify.router, prefix="/api")
app.include_router(music.router, prefix="/api")



@app.get("/")
async def root():
    return {"message": f"{settings.APP_NAME} is running", "docs": "/docs"}
