from __future__ import annotations

import json
import logging
import re
from typing import Any

try:
    from chat_models import ChartSpec, ToolEvent
    from chat_tools import ToolContext, execute_tool, tool_manifest
except ImportError:  # pragma: no cover
    from .chat_models import ChartSpec, ToolEvent
    from .chat_tools import ToolContext, execute_tool, tool_manifest

log = logging.getLogger(__name__)


class GeminiToolAgent:
    REQUEST_TIMEOUT_SECONDS = 20

    def __init__(self, model_name: str, api_key: str, use_vertex: bool = False):
        self.model_name = model_name
        self.api_key = api_key
        self.use_vertex = use_vertex

        try:
            if use_vertex:
                from google import genai
                from google.genai import types

                self._vertex_types = types
                self._client = genai.Client(vertexai=True, api_key=api_key)
                self._model = None
                self._request_options = None
                self._backend = "vertex-google-genai"
            else:
                import google.generativeai as genai
                from google.api_core import retry as gapic_retry

                self._vertex_types = None
                genai.configure(api_key=api_key)
                self._model = genai.GenerativeModel(model_name=model_name)
                self._request_options = {
                    "timeout": self.REQUEST_TIMEOUT_SECONDS,
                    "retry": gapic_retry.Retry(
                        predicate=lambda exc: False,
                        initial=0.1,
                        maximum=0.1,
                        multiplier=1.0,
                        timeout=self.REQUEST_TIMEOUT_SECONDS,
                    ),
                }
                self._backend = "google-generativeai"
            log.info("[chat-agent] Initialized %s model '%s'", self._backend, model_name)
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"Failed to initialize Gemini client: {exc}")

    def _generate_content_text(self, prompt: str) -> str:
        if self.use_vertex:
            types = self._vertex_types
            config = types.GenerateContentConfig(
                temperature=0.2,
                top_p=0.95,
                max_output_tokens=8192,
                response_mime_type="application/json",
                http_options=types.HttpOptions(timeout=self.REQUEST_TIMEOUT_SECONDS * 1000),
                safety_settings=[
                    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
                    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
                    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
                    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
                ],
                thinking_config=types.ThinkingConfig(thinking_level="LOW"),
            )
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )
            return getattr(response, "text", None) or ""

        response = self._model.generate_content(
            prompt,
            request_options=self._request_options,
        )
        return getattr(response, "text", None) or ""

    def _build_prompt(
        self,
        *,
        keyword: str,
        user_message: str,
        history: list[dict[str, Any]],
        tool_events: list[dict[str, Any]],
        gold_data: dict[str, Any],
    ) -> str:
        trimmed_history = history[-8:]

        context_preview = {
            "keyword": keyword,
            "viability_score": gold_data.get("viability_score"),
            "top_videos_count": len(gold_data.get("top_videos", [])),
            "sentiment_rows": len(gold_data.get("sentiment", [])),
            "subreddit_rows": len(gold_data.get("subreddits", [])),
            "timeline_rows": {
                "youtube": len(gold_data.get("yt_timeline", [])),
                "reddit": len(gold_data.get("rd_timeline", [])),
            },
            "has_content_gaps": bool(gold_data.get("content_gaps")),
        }

        return (
            "You are an analytics copilot for a YouTube+Reddit intelligence dashboard.\n"
            "Your job is to answer the user clearly using tools whenever data is needed.\n"
            "You may call one tool at a time.\n\n"
            "OUTPUT RULES (STRICT):\n"
            "Return JSON only, no markdown, no prose before/after JSON.\n"
            "Either:\n"
            "1) {\"action\":\"tool\",\"tool\":\"tool_name\",\"args\":{...},\"reason\":\"...\"}\n"
            "2) {\"action\":\"respond\",\"response\":\"final answer\",\"charts\":[optional chart specs]}\n\n"
            "If the user asks for custom calculations, use python_exec with code.\n"
            "For charts, either call make_chart or return chart specs in charts array.\n"
            "Keep chart specs compatible with keys: chart_type,title,data,x_key,y_key,series.\n\n"
            f"Keyword context: {keyword}\n"
            f"Data preview: {json.dumps(context_preview, ensure_ascii=True)}\n"
            f"Available tools: {json.dumps(tool_manifest(), ensure_ascii=True)}\n"
            f"Recent conversation: {json.dumps(trimmed_history, ensure_ascii=True)}\n"
            f"Tool events so far: {json.dumps(tool_events[-6:], ensure_ascii=True)}\n"
            f"User message: {user_message}\n"
        )

    def _extract_json(self, text: str) -> dict[str, Any] | None:
        text = (text or "").strip()
        if not text:
            return None

        # Raw JSON
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        # JSON block
        block = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if block:
            try:
                parsed = json.loads(block.group(0))
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                return None

        return None

    def _normalize_chart_specs(self, charts: Any) -> list[ChartSpec]:
        normalized: list[ChartSpec] = []
        if not isinstance(charts, list):
            return normalized

        for raw in charts:
            if not isinstance(raw, dict):
                continue
            try:
                normalized.append(ChartSpec(**raw))
            except Exception:
                continue
        return normalized

    def _dedupe_chart_specs(self, charts: list[ChartSpec]) -> list[ChartSpec]:
        deduped: list[ChartSpec] = []
        seen: set[str] = set()
        for chart in charts:
            chart_dict = chart.model_dump() if hasattr(chart, "model_dump") else chart.dict()
            key = json.dumps(chart_dict, sort_keys=True, ensure_ascii=True)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(chart)
        return deduped

    def _fallback_response(
        self,
        *,
        user_message: str,
        ctx: ToolContext,
        tool_events: list[ToolEvent],
    ) -> tuple[str, list[ToolEvent], list[ChartSpec]]:
        """Return a useful answer from local dashboard data when Gemini is unavailable."""
        message = user_message.lower()
        charts: list[ChartSpec] = []

        try:
            snapshot = execute_tool("get_dashboard_snapshot", {}, ctx)
            tool_events.append(
                ToolEvent(
                    tool_name="get_dashboard_snapshot",
                    args={},
                    ok=True,
                    summary="Tool 'get_dashboard_snapshot' completed by fallback",
                )
            )
        except Exception as exc:
            log.exception("[chat-agent] Fallback snapshot failed")
            tool_events.append(
                ToolEvent(
                    tool_name="get_dashboard_snapshot",
                    args={},
                    ok=False,
                    summary=f"Fallback snapshot failed: {exc}",
                )
            )
            return (
                "The AI provider timed out and I could not summarize the dashboard data locally.",
                tool_events,
                charts,
            )

        extras: list[str] = []

        if any(term in message for term in ("top video", "videos", "youtube")):
            try:
                top = execute_tool("get_top_videos", {"limit": 3}, ctx).get("videos", [])
                tool_events.append(
                    ToolEvent(
                        tool_name="get_top_videos",
                        args={"limit": 3},
                        ok=True,
                        summary="Tool 'get_top_videos' completed by fallback",
                    )
                )
                if top:
                    extras.append(
                        "Top videos: "
                        + "; ".join(
                            f"{row.get('title', 'Untitled')} ({row.get('view_count', 0):,} views)"
                            for row in top
                        )
                    )
            except Exception as exc:
                log.exception("[chat-agent] Fallback top videos failed")
                tool_events.append(
                    ToolEvent(
                        tool_name="get_top_videos",
                        args={"limit": 3},
                        ok=False,
                        summary=f"Fallback top videos failed: {exc}",
                    )
                )

        if "sentiment" in message:
            try:
                sentiment = execute_tool("get_sentiment_breakdown", {}, ctx).get("sentiment_counts", {})
                tool_events.append(
                    ToolEvent(
                        tool_name="get_sentiment_breakdown",
                        args={},
                        ok=True,
                        summary="Tool 'get_sentiment_breakdown' completed by fallback",
                    )
                )
                if sentiment:
                    extras.append(
                        "Sentiment counts: "
                        + ", ".join(f"{label}={count}" for label, count in sentiment.items())
                    )
            except Exception as exc:
                log.exception("[chat-agent] Fallback sentiment failed")
                tool_events.append(
                    ToolEvent(
                        tool_name="get_sentiment_breakdown",
                        args={},
                        ok=False,
                        summary=f"Fallback sentiment failed: {exc}",
                    )
                )

        if "chart" in message or "graph" in message:
            try:
                chart_payload = execute_tool(
                    "make_chart",
                    {"chart_type": "bar", "source": "sentiment"},
                    ctx,
                ).get("chart")
                tool_events.append(
                    ToolEvent(
                        tool_name="make_chart",
                        args={"chart_type": "bar", "source": "sentiment"},
                        ok=True,
                        summary="Tool 'make_chart' completed by fallback",
                    )
                )
                if isinstance(chart_payload, dict):
                    charts.append(ChartSpec(**chart_payload))
            except Exception as exc:
                log.exception("[chat-agent] Fallback chart failed")
                tool_events.append(
                    ToolEvent(
                        tool_name="make_chart",
                        args={"chart_type": "bar", "source": "sentiment"},
                        ok=False,
                        summary=f"Fallback chart failed: {exc}",
                    )
                )

        answer_parts = [
            "Gemini was unavailable, so I used the dashboard data directly.",
            (
                f"For '{ctx.keyword}', the dashboard shows {snapshot.get('total_views', 0):,} total YouTube views, "
                f"{snapshot.get('total_videos', 0):,} tracked videos, {snapshot.get('total_posts', 0):,} Reddit posts, "
                f"average sentiment {snapshot.get('avg_sentiment')}, and viability score "
                f"{snapshot.get('viability_score')}/100."
            ),
        ]
        answer_parts.extend(extras)

        return " ".join(answer_parts), tool_events, charts

    def run(
        self,
        *,
        keyword: str,
        user_message: str,
        history: list[dict[str, Any]],
        gold_data: dict[str, Any],
        max_steps: int = 5,
    ) -> tuple[str, list[ToolEvent], list[ChartSpec]]:
        ctx = ToolContext(keyword=keyword, gold_data=gold_data)
        tool_events: list[ToolEvent] = []
        intermediate_events: list[dict[str, Any]] = []
        seen_tool_calls: set[str] = set()

        log.info(
            "[chat-agent] Run started keyword='%s' message_len=%d history=%d max_steps=%d",
            keyword,
            len(user_message),
            len(history),
            max_steps,
        )

        for step in range(1, max_steps + 1):
            prompt = self._build_prompt(
                keyword=keyword,
                user_message=user_message,
                history=history,
                tool_events=intermediate_events,
                gold_data=gold_data,
            )

            log.info("[chat-agent] Step %d/%d: calling Gemini", step, max_steps)
            try:
                model_text = self._generate_content_text(prompt)
            except Exception as exc:
                log.exception("[chat-agent] Gemini call failed; using local dashboard fallback")
                tool_events.append(
                    ToolEvent(
                        tool_name="gemini_generate_content",
                        args={"step": step, "timeout_seconds": self.REQUEST_TIMEOUT_SECONDS},
                        ok=False,
                        summary=f"Gemini call failed: {exc}",
                    )
                )
                return self._fallback_response(
                    user_message=user_message,
                    ctx=ctx,
                    tool_events=tool_events,
                )
            action = self._extract_json(model_text)

            if not action:
                log.warning("Model response was not JSON; using direct answer fallback")
                return model_text.strip() or "I could not generate a reliable response.", tool_events, []

            action_type = str(action.get("action", "")).lower().strip()
            log.info("[chat-agent] Step %d/%d: model action='%s'", step, max_steps, action_type)

            if action_type == "tool":
                tool_name = str(action.get("tool", "")).strip()
                tool_args = action.get("args", {})
                if not isinstance(tool_args, dict):
                    tool_args = {}

                call_key = json.dumps({"tool": tool_name, "args": tool_args}, sort_keys=True, ensure_ascii=True)
                if call_key in seen_tool_calls:
                    summary = f"Repeated tool call skipped: {tool_name}"
                    log.warning("[chat-agent] %s args=%s", summary, tool_args)
                    tool_events.append(
                        ToolEvent(tool_name=tool_name, args=tool_args, ok=False, summary=summary)
                    )
                    break
                seen_tool_calls.add(call_key)

                try:
                    log.info("[chat-agent] Executing tool '%s' args=%s", tool_name, tool_args)
                    tool_result = execute_tool(tool_name, tool_args, ctx)
                    summary = f"Tool '{tool_name}' completed"
                    tool_events.append(
                        ToolEvent(tool_name=tool_name, args=tool_args, ok=True, summary=summary)
                    )
                    log.info("[chat-agent] %s", summary)
                    intermediate_events.append(
                        {
                            "tool_name": tool_name,
                            "ok": True,
                            "result": tool_result,
                        }
                    )

                    if isinstance(tool_result, dict) and "chart" in tool_result:
                        chart_payload = tool_result.get("chart")
                        if isinstance(chart_payload, dict):
                            intermediate_events[-1]["chart"] = chart_payload

                except Exception as exc:
                    summary = f"Tool '{tool_name}' failed: {exc}"
                    log.exception("[chat-agent] %s", summary)
                    tool_events.append(
                        ToolEvent(tool_name=tool_name, args=tool_args, ok=False, summary=summary)
                    )
                    intermediate_events.append(
                        {
                            "tool_name": tool_name,
                            "ok": False,
                            "error": str(exc),
                        }
                    )
                continue

            if action_type == "respond":
                answer = str(action.get("response", "")).strip()

                charts = self._normalize_chart_specs(action.get("charts", []))

                # Also pull charts emitted by tools if model forgot to include them.
                for ev in intermediate_events:
                    chart_payload = ev.get("chart")
                    if isinstance(chart_payload, dict):
                        try:
                            charts.append(ChartSpec(**chart_payload))
                        except Exception:
                            pass
                    if ev.get("tool_name") == "python_exec" and isinstance(ev.get("result"), dict):
                        for raw in ev["result"].get("charts", []):
                            if isinstance(raw, dict):
                                try:
                                    charts.append(ChartSpec(**raw))
                                except Exception:
                                    pass

                charts = self._dedupe_chart_specs(charts)
                if not answer:
                    answer = "I analyzed the request and gathered data using tools."
                log.info(
                    "[chat-agent] Run complete answer_len=%d tools=%d charts=%d",
                    len(answer),
                    len(tool_events),
                    len(charts),
                )
                return answer, tool_events, charts

        log.warning("[chat-agent] Tool-execution limit reached tools=%d", len(tool_events))
        return (
            "I reached the tool-execution limit for this request. Try narrowing the question.",
            tool_events,
            [],
        )
