import json
import re
import subprocess
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional, Tuple

from textual.widgets import Static

STATUS_COMMAND = ["moltbot", "status", "--json"]


def _run_command(command: list[str]) -> Optional[str]:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=8,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return None
    return result.stdout.strip() or None


def _load_status() -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    output = _run_command(STATUS_COMMAND)
    if not output:
        return None, "moltbot status --json failed"
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return None, "invalid JSON from moltbot status"
    if not isinstance(data, dict):
        return None, "unexpected status payload"
    return data, None


def _format_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return "unknown"
    total_seconds = max(0, int(seconds))
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    if days:
        return f"{days}d {hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _extract_session(status: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    session = status.get("session")
    if isinstance(session, dict):
        return session
    sessions = status.get("sessions")
    if isinstance(sessions, dict):
        recent = sessions.get("recent")
        if isinstance(recent, list) and recent:
            return recent[0]
        by_agent = sessions.get("byAgent")
        if isinstance(by_agent, list) and by_agent:
            agent_recent = by_agent[0].get("recent")
            if isinstance(agent_recent, list) and agent_recent:
                return agent_recent[0]
    if isinstance(sessions, list) and sessions:
        return sessions[0]
    return None


def _extract_model(status: Dict[str, Any], session: Optional[Dict[str, Any]]) -> str:
    candidates: Iterable[Optional[str]] = [
        session.get("model") if session else None,
        status.get("model"),
        status.get("current_model"),
        status.get("session_model"),
    ]
    for value in candidates:
        if isinstance(value, str) and value.strip():
            return value
    sessions = status.get("sessions")
    if isinstance(sessions, dict):
        defaults = sessions.get("defaults")
        if isinstance(defaults, dict):
            model = defaults.get("model")
            if isinstance(model, str) and model.strip():
                return model
    return "unknown"


def _format_tokens(status: Dict[str, Any], session: Optional[Dict[str, Any]]) -> str:
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
    if session:
        input_tokens = session.get("inputTokens") or session.get("promptTokens")
        output_tokens = session.get("outputTokens") or session.get("completionTokens")
        total_tokens = session.get("totalTokens") or session.get("tokens")
        remaining_tokens = session.get("remainingTokens")
        percent_used = session.get("percentUsed")
        context_tokens = session.get("contextTokens")
        parts = []
        if input_tokens is not None:
            parts.append(f"in {input_tokens}")
        if output_tokens is not None:
            parts.append(f"out {output_tokens}")
        if total_tokens is not None:
            parts.append(f"total {total_tokens}")
        if percent_used is not None:
            if context_tokens:
                parts.append(f"{percent_used}% of {context_tokens}")
            else:
                parts.append(f"{percent_used}% used")
        elif remaining_tokens is not None and context_tokens:
            used = context_tokens - remaining_tokens
            if used >= 0:
                parts.append(f"{used} / {context_tokens}")
        if parts:
            return " · ".join(parts)
    return "unavailable"


def _parse_iso_datetime(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, str):
        if value.isdigit():
            value = int(value)
        else:
            return _parse_iso_datetime(value)
    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 1e12:
            timestamp /= 1000.0
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return None


def _parse_duration_text(value: str) -> Optional[float]:
    if not value:
        return None
    total_seconds = 0.0
    found = False
    pattern = re.compile(
        r"(?P<num>\\d+)\\s*(?P<unit>days?|d|hours?|hrs?|h|minutes?|mins?|m|seconds?|secs?|s)",
        re.IGNORECASE,
    )
    for match in pattern.finditer(value):
        found = True
        amount = int(match.group("num"))
        unit = match.group("unit").lower()
        if unit.startswith("d"):
            total_seconds += amount * 86400
        elif unit.startswith("h"):
            total_seconds += amount * 3600
        elif unit.startswith("m"):
            total_seconds += amount * 60
        else:
            total_seconds += amount
    return total_seconds if found else None


def _coerce_seconds(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, str):
        if value.isdigit():
            value = int(value)
        else:
            parsed = _parse_iso_datetime(value)
            if parsed:
                return max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds())
            return None
    if isinstance(value, (int, float)):
        if value > 1e12:
            return value / 1000.0
        if value > 1e9:
            return float(value)
        if value > 1e6:
            return value / 1000.0
        return float(value)
    return None


def _extract_uptime_seconds(status: Dict[str, Any], session: Optional[Dict[str, Any]]) -> Optional[float]:
    for key in ("uptimeMs", "uptimeMS", "uptimeMillis", "uptimeSeconds", "uptimeSec", "uptime"):
        if key in status:
            return _coerce_seconds(status[key])
    for section_key in ("gateway", "gatewayService", "nodeService", "process", "system"):
        section = status.get(section_key)
        if isinstance(section, dict):
            for key in ("uptimeMs", "uptimeMillis", "uptimeSeconds", "uptime", "startedAtMs", "startedAt"):
                if key in section:
                    if key.startswith("started"):
                        started_at = _parse_timestamp(section[key])
                        if started_at:
                            return max(0.0, (datetime.now(timezone.utc) - started_at).total_seconds())
                    else:
                        return _coerce_seconds(section[key])
            runtime_text = section.get("runtimeShort") or section.get("runtimeLong")
            parsed = _parse_duration_text(runtime_text or "")
            if parsed is not None:
                return parsed
    if session:
        for key in ("ageMs", "age"):
            if key in session:
                value = _coerce_seconds(session[key])
                if value is not None:
                    return value
        updated_at = session.get("updatedAt")
        if updated_at:
            updated_dt = None
            if isinstance(updated_at, (int, float)):
                updated_dt = datetime.fromtimestamp(updated_at / 1000.0, tz=timezone.utc)
            elif isinstance(updated_at, str):
                updated_dt = _parse_iso_datetime(updated_at)
            if updated_dt:
                return max(0.0, (datetime.now(timezone.utc) - updated_dt).total_seconds())
    agents = status.get("agents")
    if isinstance(agents, dict):
        entries = agents.get("agents")
        if isinstance(entries, list) and entries:
            last_active = entries[0].get("lastActiveAgeMs")
            value = _coerce_seconds(last_active)
            if value is not None:
                return value
    return None


class SessionPanel(Static):
    def __init__(self, start_time: float, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.start_time = start_time
        self.border_title = "Session"

    def refresh_panel(self) -> None:
        status, error = _load_status()
        if not status:
            message = error or "moltbot status unavailable"
            self.update(f"[bold #ff6b6b]Status unavailable[/]\n{message}")
            return
        session = _extract_session(status)
        model = _extract_model(status, session)
        tokens = _format_tokens(status, session)
        uptime_seconds = _extract_uptime_seconds(status, session)
        if uptime_seconds is None:
            uptime_seconds = max(0.0, time.time() - self.start_time)
        uptime = _format_duration(uptime_seconds)
        self.update(
            "\n".join(
                [
                    f"[bold #7ee787]Model:[/] {model}",
                    f"[bold #a5d6ff]Tokens:[/] {tokens}",
                    f"[bold #ffe08a]Uptime:[/] {uptime}",
                ]
            )
        )
