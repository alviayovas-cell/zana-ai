import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging_config import setup_logging, logger
from app.api.routes import health, chat, spotify, music, voice, brain
from app.api.routes import memory as memory_route
from app.api.routes import metrics, profile, reminders


async def reminder_polling_loop():
    """Background task checking due reminders every 10 seconds."""
    from app.services.reminder_service import reminder_service
    while True:
        try:
            await asyncio.sleep(10)
            await reminder_service.check_due_reminders()
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning(f"[REMINDER-LOOP] Polling warning: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info(f"🚀 {settings.APP_NAME} starting up ({settings.ENVIRONMENT})")

    # Phase 5: Attempt MongoDB connection (graceful fallback if offline)
    from app.services.mongo_service import mongo_service
    await mongo_service.connect()

    # Phase 6A: Start background reminder polling loop
    reminder_task = asyncio.create_task(reminder_polling_loop())

    yield

    reminder_task.cancel()
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
app.include_router(voice.router, prefix="/api")
app.include_router(brain.router, prefix="/api")
app.include_router(memory_route.router, prefix="/api")

# Phase 6A Routes
app.include_router(metrics.router, prefix="/api")
app.include_router(profile.router, prefix="/api")
app.include_router(reminders.router, prefix="/api")


@app.get("/")
async def root():
    return {"message": f"{settings.APP_NAME} is running", "docs": "/docs"}
