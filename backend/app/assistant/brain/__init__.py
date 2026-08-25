"""
Zana AI Brain — Phase 4 Intelligence Layer.

This package adds intent understanding, context awareness,
short/long-term memory, task planning, and tool orchestration
on top of the existing Zana architecture.

Entry point: brain.py → AiBrain.process()
"""
from app.assistant.brain.brain import ai_brain

__all__ = ["ai_brain"]
