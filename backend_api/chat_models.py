from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    meta: dict[str, Any] = Field(default_factory=dict)


class ChartSpec(BaseModel):
    chart_type: Literal["bar", "line", "pie", "radar", "scatter"]
    title: str
    data: list[dict[str, Any]] = Field(default_factory=list)
    x_key: str | None = None
    y_key: str | None = None
    series: list[str] = Field(default_factory=list)


class ToolEvent(BaseModel):
    tool_name: str
    args: dict[str, Any] = Field(default_factory=dict)
    ok: bool
    summary: str


class ChatRequest(BaseModel):
    keyword: str
    message: str
    conversation_id: str | None = None
    dashboard_data: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    charts: list[ChartSpec] = Field(default_factory=list)
    tool_events: list[ToolEvent] = Field(default_factory=list)


class StartSessionRequest(BaseModel):
    keyword: str


class StartSessionResponse(BaseModel):
    conversation_id: str
    keyword: str
