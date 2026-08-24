from fastapi import APIRouter, Depends
from app.schemas.chat import ChatRequest, ChatResponse
from app.assistant.orchestrator import Orchestrator
from app.api.dependencies import get_orchestrator
from app.core.logging_config import logger

router = APIRouter(tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    orch: Orchestrator = Depends(get_orchestrator),
):
    logger.info(f"Chat request received: '{request.message[:50]}...'")
    try:
        response = await orch.handle_message(
            message=request.message,
            session_id=request.session_id,
        )
        return response
    except Exception as e:
        logger.error(f"Chat processing error: {e}", exc_info=True)
        return ChatResponse(
            message="I'm sorry, something went wrong while processing your request. Please try again.",
            status="error",
            session_id=request.session_id,
        )
