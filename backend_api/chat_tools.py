from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

try:
    from python_runner import execute_python_analysis
except ImportError:  # pragma: no cover
    from .python_runner import execute_python_analysis


@dataclass
class ToolContext:
    keyword: str
    gold_data: dict[str, Any]


@dataclass
class ToolDefinition:
    name: str
    description: str
    schema: dict[str, Any]
    handler: Callable[[dict[str, Any], ToolContext], dict[str, Any]]



def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default



def tool_get_dashboard_snapshot(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    top_videos = ctx.gold_data.get("top_videos", [])
    rd_timeline = ctx.gold_data.get("rd_timeline", [])
    yt_timeline = ctx.gold_data.get("yt_timeline", [])
    sentiment = ctx.gold_data.get("sentiment", [])

    total_views = int(sum(_safe_float(r.get("view_count", 0)) for r in top_videos))
    total_posts = int(sum(_safe_float(r.get("post_count", 0)) for r in rd_timeline))
    total_videos = int(sum(_safe_float(r.get("video_count", 0)) for r in yt_timeline))

    avg_sentiment = 0.0
    sent_weight = sum(_safe_float(r.get("count", 0), 0) for r in sentiment)
    if sent_weight:
        avg_sentiment = (
            sum(_safe_float(r.get("avg_score", 0)) * _safe_float(r.get("count", 0)) for r in sentiment)
            / sent_weight
        )

    return {
        "keyword": ctx.keyword,
        "total_views": total_views,
        "total_posts": total_posts,
        "total_videos": total_videos,
        "viability_score": ctx.gold_data.get("viability_score"),
        "avg_sentiment": round(avg_sentiment, 4),
    }



def tool_get_top_videos(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    limit = int(args.get("limit", 5))
    limit = min(max(limit, 1), 20)

    rows = sorted(
        ctx.gold_data.get("top_videos", []),
        key=lambda r: _safe_float(r.get("view_count", 0)),
        reverse=True,
    )[:limit]

    payload = [
        {
            "title": r.get("title", ""),
            "channel": r.get("channel", ""),
            "view_count": int(_safe_float(r.get("view_count", 0))),
            "like_to_view_ratio": round(_safe_float(r.get("like_to_view_ratio", 0)), 5),
            "sentiment_score": round(_safe_float(r.get("sentiment_score", 0)), 4),
        }
        for r in rows
    ]

    return {"videos": payload}



def tool_get_sentiment_breakdown(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    rows = ctx.gold_data.get("sentiment", [])
    by_label: dict[str, int] = {}
    for row in rows:
        label = (row.get("sentiment_label") or "neutral").lower()
        by_label[label] = by_label.get(label, 0) + int(_safe_float(row.get("count", 0)))

    return {
        "sentiment_counts": by_label,
        "raw": rows,
    }



def tool_get_viability_breakdown(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    rows = [r for r in ctx.gold_data.get("topic_recs", []) if r.get("metric") != "TOTAL_VIABILITY"]
    rows = sorted(rows, key=lambda r: _safe_float(r.get("weighted_contribution", 0)), reverse=True)
    return {
        "viability_score": ctx.gold_data.get("viability_score"),
        "components": rows,
    }



def tool_get_content_gaps(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    limit = int(args.get("limit", 8))
    limit = min(max(limit, 1), 20)
    rows = sorted(
        ctx.gold_data.get("content_gaps", []),
        key=lambda r: _safe_float(r.get("opportunity_score", 0)),
        reverse=True,
    )[:limit]
    return {"gaps": rows}



def tool_make_chart(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    chart_type = str(args.get("chart_type", "bar")).lower()
    source = str(args.get("source", "sentiment")).lower()

    if source == "sentiment":
        rows = ctx.gold_data.get("sentiment", [])
        by_label: dict[str, int] = {}
        for row in rows:
            label = (row.get("sentiment_label") or "neutral").lower()
            by_label[label] = by_label.get(label, 0) + int(_safe_float(row.get("count", 0)))

        data = [{"label": k, "value": v} for k, v in by_label.items()]
        return {
            "chart": {
                "chart_type": chart_type if chart_type in {"bar", "pie", "radar"} else "bar",
                "title": f"Sentiment Overview for '{ctx.keyword}'",
                "data": data,
                "x_key": "label",
                "y_key": "value",
            }
        }

    if source == "top_videos":
        rows = sorted(
            ctx.gold_data.get("top_videos", []),
            key=lambda r: _safe_float(r.get("view_count", 0)),
            reverse=True,
        )[:8]
        data = [
            {
                "title": (r.get("title", "")[:30] + "...") if len(r.get("title", "")) > 30 else r.get("title", ""),
                "views": int(_safe_float(r.get("view_count", 0))),
            }
            for r in rows
        ]
        return {
            "chart": {
                "chart_type": chart_type if chart_type in {"bar", "line", "scatter"} else "bar",
                "title": f"Top Videos by Views for '{ctx.keyword}'",
                "data": data,
                "x_key": "title",
                "y_key": "views",
            }
        }

    if source == "subreddits":
        rows = sorted(
            ctx.gold_data.get("subreddits", []),
            key=lambda r: _safe_float(r.get("post_count", 0)),
            reverse=True,
        )[:10]
        data = [
            {
                "subreddit": r.get("subreddit", ""),
                "posts": int(_safe_float(r.get("post_count", 0))),
            }
            for r in rows
        ]
        return {
            "chart": {
                "chart_type": chart_type if chart_type in {"bar", "line", "pie"} else "bar",
                "title": f"Top Subreddits for '{ctx.keyword}'",
                "data": data,
                "x_key": "subreddit",
                "y_key": "posts",
            }
        }

    raise ValueError("Unknown chart source. Use sentiment, top_videos, or subreddits.")



def tool_run_python(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    code = str(args.get("code", "")).strip()
    if not code:
        raise ValueError("'code' is required for python_exec tool")

    result = execute_python_analysis(code=code, gold_data=ctx.gold_data)
    payload: dict[str, Any] = {
        "ok": bool(result.get("ok")),
        "stdout": result.get("stdout", ""),
        "result": result.get("result", None),
    }

    charts = result.get("charts") or []
    if charts:
        payload["charts"] = charts

    if not result.get("ok"):
        payload["error"] = result.get("error", "Execution failed")

    return payload



def build_tool_registry() -> dict[str, ToolDefinition]:
    return {
        "get_dashboard_snapshot": ToolDefinition(
            name="get_dashboard_snapshot",
            description="Get a compact KPI snapshot for the current keyword dashboard data.",
            schema={"type": "object", "properties": {}},
            handler=tool_get_dashboard_snapshot,
        ),
        "get_top_videos": ToolDefinition(
            name="get_top_videos",
            description="Get top videos sorted by view count.",
            schema={"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 20}}},
            handler=tool_get_top_videos,
        ),
        "get_sentiment_breakdown": ToolDefinition(
            name="get_sentiment_breakdown",
            description="Get sentiment totals by label.",
            schema={"type": "object", "properties": {}},
            handler=tool_get_sentiment_breakdown,
        ),
        "get_viability_breakdown": ToolDefinition(
            name="get_viability_breakdown",
            description="Get weighted viability components.",
            schema={"type": "object", "properties": {}},
            handler=tool_get_viability_breakdown,
        ),
        "get_content_gaps": ToolDefinition(
            name="get_content_gaps",
            description="List Reddit demand gaps with low YouTube coverage.",
            schema={"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 20}}},
            handler=tool_get_content_gaps,
        ),
        "make_chart": ToolDefinition(
            name="make_chart",
            description="Generate a standardized chart spec from known datasets.",
            schema={
                "type": "object",
                "properties": {
                    "chart_type": {"type": "string", "enum": ["bar", "line", "pie", "radar", "scatter"]},
                    "source": {"type": "string", "enum": ["sentiment", "top_videos", "subreddits"]},
                },
            },
            handler=tool_make_chart,
        ),
        "python_exec": ToolDefinition(
            name="python_exec",
            description="Run safe analytical Python code over gold_data. Return stdout/result/chart specs.",
            schema={"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]},
            handler=tool_run_python,
        ),
    }



def execute_tool(name: str, args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    registry = build_tool_registry()
    if name not in registry:
        raise ValueError(f"Unknown tool '{name}'")
    return registry[name].handler(args or {}, ctx)



def tool_manifest() -> list[dict[str, Any]]:
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "schema": tool.schema,
        }
        for tool in build_tool_registry().values()
    ]
