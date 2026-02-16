"""Modelos para agente Selenium controlado por IA."""
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl

AgentActionType = Literal[
    "goto",
    "click",
    "type",
    "scroll",
    "wait",
    "back",
    "open_new_tab",
    "extract",
    "stop",
]


class AgentAction(BaseModel):
    """Acao sugerida pelo planner."""

    action: AgentActionType
    target: str | None = None
    value: str | None = None
    reason: str | None = None


class AgentState(BaseModel):
    """Estado atual observado na pagina."""

    step_index: int
    current_url: str
    title: str | None = None
    text_excerpt: str = ""
    html_excerpt: str = ""
    screenshot_base64: str | None = None
    last_action: AgentAction | None = None
    last_error: str | None = None


class AgentStepResult(BaseModel):
    """Resultado de uma acao executada."""

    step_index: int
    action: AgentAction
    success: bool
    current_url: str
    title: str | None = None
    error: str | None = None
    elapsed_seconds: float
    state_snapshot: dict[str, Any] = Field(default_factory=dict)


class StopCondition(BaseModel):
    """Sinal para encerramento seguro do loop."""

    reached_goal: bool = False
    max_steps_reached: bool = False
    captcha_or_blocked: bool = False
    no_progress: bool = False
    reason: str | None = None


class AgentExecutionRequest(BaseModel):
    """Payload para endpoint de scraping por agente."""

    url: HttpUrl
    goal: str = Field(min_length=5, max_length=2000)
    schema: str = "guided_extract"
    max_steps: int = Field(default=8, ge=1, le=30)
    strategy: str = "generic"
    headless: bool = True


class AgentExecutionResponse(BaseModel):
    """Resposta principal de execucao do agente."""

    execution_id: int | None = None
    success: bool
    data: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    steps: list[AgentStepResult] = Field(default_factory=list)

