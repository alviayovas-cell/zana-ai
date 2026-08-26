import json
import asyncio
import time
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.schemas.chat import ChatRequest, ChatResponse
from app.assistant.orchestrator import Orchestrator
from app.api.dependencies import get_orchestrator
from app.core.logging_config import logger
from app.services.llm_service import llm_service

router = APIRouter(tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    orch: Orchestrator = Depends(get_orchestrator),
):
    logger.info(f"Chat request received: '{request.message[:50]}...'")
    started_at = time.perf_counter()
    try:
        response = await orch.handle_message(
            message=request.message,
            session_id=request.session_id,
        )
        logger.info(f"[PERF] chat total_ms={(time.perf_counter() - started_at) * 1000:.1f}")
        return response
    except Exception as e:
        logger.error(f"Chat processing error: {e}", exc_info=True)
        return ChatResponse(
            message="I'm sorry, something went wrong while processing your request. Please try again.",
            status="error",
            session_id=request.session_id,
        )


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    orch: Orchestrator = Depends(get_orchestrator),
):
    """
    Phase 6A SSE streaming endpoint.
    Yields event: metadata (structured track/action payload) followed by event: delta (text tokens) and event: done.
    """
    logger.info(f"Streaming chat request received: '{request.message[:50]}...'")

    async def event_generator():
        try:
            # 1. Process message through Orchestrator / Brain
            response = await orch.handle_message(
                message=request.message,
                session_id=request.session_id,
            )

            # 2. Emit metadata event (session_id, track, action, suggestions)
            meta = {
                "session_id": response.session_id,
                "status": response.status,
                "action": response.action,
                "action_value": response.action_value,
                "track": response.track.dict() if response.track else None,
                "suggestions": [s.dict() for s in response.suggestions] if response.suggestions else [],
            }
            yield f"event: metadata\ndata: {json.dumps(meta)}\n\n"

            # 3. Emit text message content
            text = response.message or ""
            # Chunk response text for smooth UI rendering
            words = text.split(" ")
            for i in range(0, len(words), 3):
                chunk = " ".join(words[i:i+3]) + (" " if i+3 < len(words) else "")
                yield f"event: delta\ndata: {json.dumps({'content': chunk})}\n\n"
                await asyncio.sleep(0.02)

            # 4. Emit done event
            yield "event: done\ndata: {}\n\n"

        except Exception as exc:
            logger.error(f"Streaming error: {exc}", exc_info=True)
            err_payload = {"content": "I'm sorry, an error occurred during streaming."}
            yield f"event: delta\ndata: {json.dumps(err_payload)}\n\n"
            yield "event: done\ndata: {}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
