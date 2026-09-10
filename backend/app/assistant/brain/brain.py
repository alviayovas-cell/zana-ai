"""
brain.py — Main entry point for the Zana AI Brain (Phase 4).

The AiBrain.process() method is called by the orchestrator when
the fast regex router returns CommandAction.UNKNOWN.

Pipeline:
    1. Load session context (context_manager)
    2. Load long-term memory (memory_store)
    3. Analyze intent (intent_analyzer) — fast-path or LLM
    4. Build execution plan (task_planner)
    5. Execute tools (tool_executor) — calls existing services
    6. Generate response (response_generator)
    7. Update session context
    8. Update long-term memory

All existing services (free_music_service, spotify_service) are
called through tool_executor — nothing is duplicated.
"""
from __future__ import annotations

from typing import Optional

from app.core.logging_config import logger
from app.schemas.chat import ChatResponse, SuggestionItem
from app.assistant.brain.context_manager import context_manager, ConversationContext
from app.assistant.brain.memory_store import memory_store
from app.assistant.brain.intent_analyzer import intent_analyzer
from app.assistant.brain.task_planner import task_planner, ExecutionPlan, TaskStep
from app.assistant.brain.tool_executor import tool_executor, ToolResult
from app.assistant.brain.response_generator import response_generator


class AiBrain:
    """
    The Zana AI Brain — Phase 4 intelligence layer.

    Called by the orchestrator when regex-based routing yields UNKNOWN.
    Also called directly for context-aware commands (music_next, etc.)
    when a brain-level upgrade is needed.
    """

    async def process(
        self,
        message: str,
        session_id: Optional[str] = None,
    ) -> ChatResponse:
        """
        Process a user message through the full AI Brain pipeline.

        Parameters
        ----------
        message:    The user's input text (already trimmed).
        session_id: Optional session identifier for context continuity.

        Returns
        -------
        ChatResponse ready to be returned to the frontend.
        """
        logger.info(f"[AI-BRAIN] ─────────────────────────────────────────")
        logger.info(f"[AI-BRAIN] Input: {message!r} (session={session_id})")

        # ── Step 1: Context retrieval ────────────────────────────────────────
        sid = session_id or "anonymous"
        ctx: ConversationContext = context_manager.get_or_create(sid)
        ctx.add_user_message(message)

        # Explicit "remember" requests bypass intent classification so they
        # are persisted even when no LLM provider is configured.
        normalized_message = message.strip()
        if normalized_message.lower().startswith(("remember ", "remember that ")):
            memory_content = normalized_message.split(" ", 1)[1]
            if memory_content.lower().startswith("that "):
                memory_content = memory_content[5:]
            await memory_store.save_explicit_memory(sid, memory_content.strip())
            reply = f"I’ll remember that {memory_content.strip()}."
            ctx.add_assistant_message(reply)
            return ChatResponse(
                message=reply,
                session_id=session_id,
                intent="memory_save",
                confidence=1.0,
                tool="memory_save",
                execution_status="success",
            )

        # ── Step 2: Long-term memory retrieval ──────────────────────────────
        mem = memory_store.get_or_create(sid)
        memory_context = mem.to_context_string()

        # ── Step 3: Intent analysis ──────────────────────────────────────────
        intent_result = await intent_analyzer.analyze(
            message=message,
            ctx=ctx,
            memory_context=memory_context,
        )
        logger.info(
            f"[AI-BRAIN] Intent: {intent_result.intent} "
            f"(conf={intent_result.confidence:.2f}, tool={intent_result.tool!r})"
        )

        # ── Clarification short-circuit ──────────────────────────────────────
        if intent_result.needs_clarification:
            q = intent_result.clarification_question or "Could you be more specific?"
            logger.info(f"[AI-BRAIN] Clarification requested: {q!r}")
            ctx.add_assistant_message(q)
            return ChatResponse(
                message=q,
                session_id=session_id,
                suggestions=[
                    SuggestionItem(label="Play Blinding Lights", action_type="music_play"),
                    SuggestionItem(label="What can you do?", action_type="help"),
                ],
            )

        # ── Step 4: Task planning ────────────────────────────────────────────
        plan: ExecutionPlan = task_planner.build_plan(intent_result)
        logger.info(
            f"[AI-BRAIN] Plan: {len(plan.steps)} step(s) — "
            + ", ".join(s.tool for s in plan.steps)
        )

        # ── Step 5: Tool execution ───────────────────────────────────────────
        last_result: Optional[ToolResult] = None
        previous_failed = False

        for step in plan.steps:
            if step.depends_on_previous and previous_failed:
                logger.info(f"[AI-BRAIN] Skipping step {step.tool!r} — previous step failed")
                continue

            result = await tool_executor.execute(
                tool_name=step.tool,
                arguments=step.arguments,
                ctx=ctx,
            )
            logger.info(f"[AI-BRAIN] Result: {result}")

            # ── Update music context on successful play ──────────────────────
            if result.success and step.tool in ("music_play", "music_search_play", "music_next"):
                query = step.arguments.get("query", "")
                ctx.update_music_context(
                    query=query,
                    track=result.track_title,
                    artist=result.track_artist,
                )
                # Update long-term memory with preferences
                memory_store.extract_and_store(
                    session_id=sid,
                    intent=step.tool,
                    query=query,
                    artist=result.track_artist,
                )

            previous_failed = not result.success
            last_result = result

            # For single-step plans, stop after first result
            if not plan.is_multi_step():
                break

        # If all steps somehow skipped, create a safe no-op result
        if last_result is None:
            last_result = ToolResult(
                success=False,
                tool=plan.steps[0].tool if plan.steps else "chat_response",
                error="No tools were executed.",
            )

        # ── Step 6: Response generation ──────────────────────────────────────
        response = await response_generator.generate(
            tool_result=last_result,
            intent_result=intent_result,
            original_message=message,
            ctx=ctx,
            session_id=session_id,
        )

        # ── Step 7: Update context with assistant reply ──────────────────────
        ctx.current_intent = intent_result.intent
        ctx.add_assistant_message(response.message)

        logger.info(f"[AI-BRAIN] Response: {response.message[:80]!r}")
        logger.info(f"[AI-BRAIN] ─────────────────────────────────────────")

        return response


# Singleton instance — imported by orchestrator
ai_brain = AiBrain()
