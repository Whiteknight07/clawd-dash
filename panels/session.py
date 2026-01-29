import json
import subprocess
import time
from typing import Any, Dict, Optional

from textual.widgets import Static

STATUS_COMMAND = ["moltbot", "status", "--json"]


def _run_command(command: list[str]) -> Optional[str]:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return None
    return result.stdout.strip() or None


def _load_status() -> Optional[Dict[str, Any]]:
    output = _run_command(STATUS_COMMAND)
    if not output:
        return None
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return None


def _format_uptime(start_time: float) -> str:
    elapsed = max(0, int(time.time() - start_time))
    hours, remainder = divmod(elapsed, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _format_tokens(status: Dict[str, Any]) -> str:
    usage = status.get("token_usage") or status.get("tokens") or {}
    if isinstance(usage, dict):
        prompt = usage.get("prompt") or usage.get("input")
        completion = usage.get("completion") or usage.get("output")
        total = usage.get("total")
        parts = []
        if prompt is not None:
            parts.append(f"prompt {prompt}")
        if completion is not None:
            parts.append(f"completion {completion}")
        if total is not None:
            parts.append(f"total {total}")
        if parts:
            return ", ".join(parts)
    return "unavailable"


class SessionPanel(Static):
    def __init__(self, start_time: float, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.start_time = start_time
        self.border_title = "Session"

    def refresh_panel(self) -> None:
        status = _load_status() or {}
        model = status.get("model") or status.get("current_model") or "moltbot-core"
        tokens = _format_tokens(status)
        uptime = _format_uptime(self.start_time)
        self.update(
            "\n".join(
                [
                    f"[bold #7ee787]Model:[/] {model}",
                    f"[bold #a5d6ff]Tokens:[/] {tokens}",
                    f"[bold #ffe08a]Uptime:[/] {uptime}",
                ]
            )
        )
