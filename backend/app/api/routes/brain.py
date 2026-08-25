"""
brain.py — API route endpoints for Phase 4 AI Brain inspection and testing.

Endpoints:
  - GET  /api/brain/status — Returns AI Brain architecture status, modules, active sessions, LLM provider info
  - POST /api/brain/test   — Direct execution test against AI Brain with telemetry
"""
import time
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.assistant.brain.brain import ai_brain
from app.assistant.brain.context_manager import context_manager
from app.services.llm_service import llm_service
from app.schemas.chat import ChatResponse
from app.core.logging_config import logger


router = APIRouter(prefix="/brain", tags=["AI Brain"])


class BrainTestRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="Command to test against AI Brain")
    session_id: Optional[str] = Field(default="dev-test-session", description="Session ID for test")


class BrainStatusResponse(BaseModel):
    status: str = "active"
    architecture: str = "Zana Phase 4 AI Brain Orchestrator"
    modules: Dict[str, bool] = {
        "intent_analyzer": True,
        "context_manager": True,
        "memory_store": True,
        "tool_registry": True,
        "task_planner": True,
        "tool_executor": True,
        "response_generator": True,
    }
    active_sessions: int
    llm_configured: bool
    provider: str
    model: str


@router.get("/status", response_model=BrainStatusResponse)
async def get_brain_status():
    info = llm_service.get_provider_info()
    return BrainStatusResponse(
        status="active",
        architecture="Zana Phase 4 AI Brain Orchestrator",
        modules={
            "intent_analyzer": True,
            "context_manager": True,
            "memory_store": True,
            "tool_registry": True,
            "task_planner": True,
            "tool_executor": True,
            "response_generator": True,
        },
        active_sessions=context_manager.active_session_count(),
        llm_configured=info["configured"],
        provider=info["provider"],
        model=info["model"],
    )


@router.post("/test", response_model=ChatResponse)
async def test_brain(request: BrainTestRequest):
    """
    Directly run a message through the REAL AI Brain implementation
    and return response with full diagnostic telemetry.
    """
    logger.info(f"[BRAIN API] Direct test request: '{request.message}'")
    start = time.time()
    try:
        response = await ai_brain.process(
            message=request.message,
            session_id=request.session_id,
        )
        elapsed_ms = (time.time() - start) * 1000
        logger.info(f"[BRAIN API] Completed in {elapsed_ms:.1f}ms")
        return response
    except Exception as e:
        logger.error(f"[BRAIN API] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
