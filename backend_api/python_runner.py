from __future__ import annotations

import ast
import contextlib
import io
import multiprocessing as mp
import traceback
from typing import Any


ALLOWED_IMPORTS = {"math", "statistics", "json", "pandas", "numpy"}
FORBIDDEN_NAMES = {
    "open",
    "exec",
    "eval",
    "compile",
    "input",
    "__import__",
    "globals",
    "locals",
    "vars",
    "help",
}


def _validate_code(code: str) -> None:
    tree = ast.parse(code, mode="exec")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in ALLOWED_IMPORTS:
                    raise ValueError(f"Import '{root}' is not allowed.")

        if isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root not in ALLOWED_IMPORTS:
                raise ValueError(f"Import '{root}' is not allowed.")

        if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            raise ValueError(f"Usage of '{node.id}' is not allowed.")

        if isinstance(node, ast.Attribute) and isinstance(node.attr, str):
            if node.attr.startswith("__"):
                raise ValueError("Dunder attribute access is not allowed.")



def _worker(code: str, gold_data: dict[str, Any], queue: mp.Queue) -> None:
    stdout_capture = io.StringIO()
    charts: list[dict[str, Any]] = []

    def chart(
        chart_type: str,
        data: list[dict[str, Any]],
        title: str = "Generated Chart",
        x_key: str | None = None,
        y_key: str | None = None,
        series: list[str] | None = None,
    ) -> None:
        chart_type = (chart_type or "").strip().lower()
        if chart_type not in {"bar", "line", "pie", "radar", "scatter"}:
            raise ValueError("chart_type must be one of: bar,line,pie,radar,scatter")
        if not isinstance(data, list):
            raise ValueError("chart data must be a list of objects")

        charts.append(
            {
                "chart_type": chart_type,
                "title": title,
                "data": data[:300],
                "x_key": x_key,
                "y_key": y_key,
                "series": series or [],
            }
        )

    safe_builtins = {
        "abs": abs,
        "min": min,
        "max": max,
        "sum": sum,
        "len": len,
        "sorted": sorted,
        "round": round,
        "range": range,
        "enumerate": enumerate,
        "zip": zip,
        "list": list,
        "dict": dict,
        "set": set,
        "tuple": tuple,
        "float": float,
        "int": int,
        "str": str,
        "bool": bool,
        "print": print,
    }

    local_ns: dict[str, Any] = {}
    global_ns: dict[str, Any] = {
        "__builtins__": safe_builtins,
        "gold_data": gold_data,
        "chart": chart,
    }

    try:
        with contextlib.redirect_stdout(stdout_capture):
            exec(code, global_ns, local_ns)

        result = local_ns.get("result", None)
        queue.put(
            {
                "ok": True,
                "stdout": stdout_capture.getvalue()[-8000:],
                "result": result,
                "charts": charts,
            }
        )
    except Exception:
        queue.put(
            {
                "ok": False,
                "error": traceback.format_exc()[-8000:],
                "stdout": stdout_capture.getvalue()[-8000:],
                "charts": charts,
            }
        )



def execute_python_analysis(
    code: str,
    gold_data: dict[str, Any],
    timeout_seconds: int = 8,
) -> dict[str, Any]:
    _validate_code(code)

    queue: mp.Queue = mp.Queue()
    proc = mp.Process(target=_worker, args=(code, gold_data, queue), daemon=True)
    proc.start()
    proc.join(timeout_seconds)

    if proc.is_alive():
        proc.terminate()
        proc.join()
        return {
            "ok": False,
            "error": f"Python execution timed out after {timeout_seconds}s",
            "stdout": "",
            "charts": [],
        }

    if queue.empty():
        return {
            "ok": False,
            "error": "Python execution returned no output",
            "stdout": "",
            "charts": [],
        }

    return queue.get()
