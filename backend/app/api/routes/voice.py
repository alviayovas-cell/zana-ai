from fastapi import APIRouter, File, UploadFile, HTTPException
from app.services.stt_service import stt_service
from app.core.logging_config import logger

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Accept audio blob recorded via browser MediaRecorder,
    transcribe via configured STT provider, and return transcript.
    """
    try:
        audio_bytes = await file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file received.")

        logger.info(
            f"[VOICE API] Received audio: {file.filename}, content-type: {file.content_type}, size: {len(audio_bytes)} bytes"
        )
        transcript = await stt_service.transcribe(audio_bytes, filename=file.filename or "audio.webm")
        return {"transcript": transcript, "bytes_received": len(audio_bytes)}
    except Exception as e:
        logger.error(f"[VOICE API] Transcription failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")
