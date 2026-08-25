"""
task_planner.py — Lightweight sequential task planner for Zana AI Brain.

Converts an IntentResult (potentially containing multiple steps) into an
ordered list of TaskStep objects for the tool executor to run.

Design principles:
- Only used for multi-step requests (single-intent requests skip the planner).
- No LLM call here — planning is derived from the intent_analyzer's output.
- Steps have an explicit order when order matters.
- Simple and fast.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.core.logging_config import logger
from app.assistant.brain.intent_analyzer import IntentResult


@dataclass
class TaskStep:
    """A single executable step in a plan."""

    tool: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    required: bool = True          # If False, failure of this step is non-fatal
    depends_on_previous: bool = False  # If True, skip this step if previous failed

    def __repr__(self) -> str:
        return f"TaskStep(tool={self.tool!r}, args={self.arguments}, required={self.required})"


@dataclass
class ExecutionPlan:
    """An ordered list of steps derived from a user's intent."""

    steps: List[TaskStep] = field(default_factory=list)
    original_intent: str = ""
    description: str = ""

    def is_multi_step(self) -> bool:
        return len(self.steps) > 1

    def is_empty(self) -> bool:
        return len(self.steps) == 0


class TaskPlanner:
    """
    Converts an IntentResult into an ExecutionPlan.

    For simple single-intent results, wraps into a one-step plan.
    For multi-step results (e.g. "play X and lower volume"), parses the
    LLM-provided steps list into sequential TaskSteps.
    """

    def build_plan(self, intent_result: IntentResult) -> ExecutionPlan:
        """
        Convert an IntentResult into an ExecutionPlan.

        Parameters
        ----------
        intent_result: The structured output from IntentAnalyzer.

        Returns
        -------
        ExecutionPlan with one or more TaskSteps.
        """
        # ── Multi-step: LLM provided an explicit steps list ─────────────────
        if intent_result.steps and len(intent_result.steps) > 1:
            plan = self._build_multi_step_plan(intent_result)
            if not plan.is_empty():
                logger.info(
                    f"[AI-BRAIN] Multi-step plan ({len(plan.steps)} steps): "
                    + ", ".join(s.tool for s in plan.steps)
                )
                return plan

        # ── Single-step: wrap the single tool call ───────────────────────────
        if not intent_result.requires_tool or not intent_result.tool:
            # No tool needed — chat_response handles it
            plan = ExecutionPlan(
                steps=[TaskStep(
                    tool="chat_response",
                    arguments={
                        "intent": intent_result.intent,
                        "response_hint": intent_result.response_hint or "",
                    },
                )],
                original_intent=intent_result.intent,
                description="Generate conversational response",
            )
        else:
            plan = ExecutionPlan(
                steps=[TaskStep(
                    tool=intent_result.tool,
                    arguments=intent_result.arguments,
                    description=f"Execute {intent_result.tool}",
                )],
                original_intent=intent_result.intent,
                description=f"Single tool: {intent_result.tool}",
            )

        logger.info(f"[AI-BRAIN] Single-step plan: {plan.steps[0].tool}")
        return plan

    def _build_multi_step_plan(self, intent_result: IntentResult) -> ExecutionPlan:
        """Parse LLM-provided steps into TaskStep list."""
        steps: List[TaskStep] = []
        raw_steps = intent_result.steps

        for i, raw in enumerate(raw_steps):
            if not isinstance(raw, dict):
                continue
            tool = raw.get("tool")
            if not tool:
                continue

            step = TaskStep(
                tool=tool,
                arguments=raw.get("arguments") or {},
                description=raw.get("description", f"Step {i+1}"),
                required=raw.get("required", True),
                depends_on_previous=(i > 0),
            )
            steps.append(step)

        if not steps:
            return ExecutionPlan()

        return ExecutionPlan(
            steps=steps,
            original_intent=intent_result.intent,
            description="Multi-step execution",
        )


# Singleton instance
task_planner = TaskPlanner()
