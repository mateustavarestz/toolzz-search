"""Orquestrador de agente Selenium (planner-executor-observer)."""
import time
from typing import Any

from loguru import logger
from pydantic import BaseModel

from src.core.ai_processor import AIProcessor
from src.core.extraction_buffer import ExtractionBuffer
from src.core.selenium_browser import SeleniumBrowser
from src.core.validator import DataValidator
from src.models.agent import AgentAction, AgentExecutionResponse, AgentState, AgentStepResult, StopCondition


class AgentOrchestrator:
    """Executa loop do agente com limite de passos e guardrails simples."""

    def __init__(self) -> None:
        self.ai = AIProcessor()
        self.validator = DataValidator()

    async def run(
        self,
        url: str,
        goal: str,
        schema: type[BaseModel],
        max_steps: int = 8,
        headless: bool = True,
    ) -> AgentExecutionResponse:
        started = time.perf_counter()
        buffer = ExtractionBuffer()
        steps: list[AgentStepResult] = []
        stop = StopCondition()
        last_urls: list[str] = []

        async with SeleniumBrowser(headless=headless) as browser:
            await browser.execute_action({"action": "goto", "value": url})
            state_dict = await browser.capture_state(step_index=0)
            buffer.add_state(state_dict)
            current_state = AgentState(**state_dict, last_action=None)

            for idx in range(1, max_steps + 1):
                action = await self.ai.plan_next_action(current_state, goal)
                if action.action == "stop":
                    stop.reached_goal = True
                    stop.reason = action.reason or "planner_stop"
                    break
                if action.action == "extract":
                    stop.reached_goal = True
                    stop.reason = "planner_extract"
                    break

                exec_result = await browser.execute_action(action.model_dump())
                state_dict = await browser.capture_state(step_index=idx, last_error=exec_result.error)
                buffer.add_state(state_dict)
                current_state = AgentState(**state_dict, last_action=action, last_error=exec_result.error)
                step_result = AgentStepResult(
                    step_index=idx,
                    action=action,
                    success=exec_result.success,
                    current_url=current_state.current_url,
                    title=current_state.title,
                    error=exec_result.error,
                    elapsed_seconds=exec_result.elapsed_seconds,
                    state_snapshot={
                        "url": current_state.current_url,
                        "title": current_state.title,
                        "last_error": current_state.last_error,
                    },
                )
                steps.append(step_result)

                # Guardrails simples de no-progress/loop.
                last_urls.append(current_state.current_url)
                if len(last_urls) > 4:
                    last_urls = last_urls[-4:]
                if len(last_urls) >= 4 and len(set(last_urls)) == 1:
                    stop.no_progress = True
                    stop.reason = "same_url_loop"
                    break
                if exec_result.error and "captcha" in exec_result.error.lower():
                    stop.captcha_or_blocked = True
                    stop.reason = "captcha_or_blocked"
                    break

            if len(steps) >= max_steps and not stop.reason:
                stop.max_steps_reached = True
                stop.reason = "max_steps_reached"

        ai_result = await self.ai.extract_from_evidence(buffer.states, schema=schema, goal=goal)
        validated_data, errors, quality = self.validator.validate(ai_result["data"], schema=schema)
        elapsed = time.perf_counter() - started
        if errors or validated_data is None:
            logger.error(f"Agent validation failed: {errors}")
            return AgentExecutionResponse(
                success=False,
                data=None,
                steps=steps,
                metadata={
                    "error": "Validation failed",
                    "validation_errors": errors,
                    "quality": quality,
                    "duration_seconds": elapsed,
                    "tokens_used": ai_result["metadata"]["tokens_used"],
                    "cost_usd": ai_result["metadata"]["cost_usd"],
                    "stop": stop.model_dump(),
                    "error_type": "validation",
                },
            )
        return AgentExecutionResponse(
            success=True,
            data=validated_data,
            steps=steps,
            metadata={
                "duration_seconds": elapsed,
                "tokens_used": ai_result["metadata"]["tokens_used"],
                "cost_usd": ai_result["metadata"]["cost_usd"],
                "quality": quality,
                "stop": stop.model_dump(),
                "error_type": None,
            },
        )

