import json
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from textual.widgets import Static

CRON_COMMAND = ["moltbot", "cron", "list", "--json"]


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


def _load_jobs() -> Tuple[List[Dict[str, Any]], Optional[str]]:
    output = _run_command(CRON_COMMAND)
    if not output:
        return [], "moltbot cron list --json failed"
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return [], "invalid JSON from moltbot cron list"
    if isinstance(data, dict) and "jobs" in data:
        jobs = data["jobs"]
    else:
        jobs = data
    if not isinstance(jobs, list):
        return [], "unexpected cron payload"
    return jobs, None


def _parse_datetime(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _parse_epoch(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, str) and value.isdigit():
        value = int(value)
    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 1e12:
            timestamp /= 1000.0
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    if isinstance(value, str):
        return _parse_datetime(value)
    return None


def _extract_next_run(job: Dict[str, Any]) -> Optional[datetime]:
    state = job.get("state") or {}
    for key in ("nextRunAtMs", "next_run_at_ms", "nextRunAt", "next_run_at", "next"):
        if key in state:
            return _parse_epoch(state[key])
    schedule = job.get("schedule") or {}
    if isinstance(schedule, dict):
        if schedule.get("kind") == "at":
            for key in ("atMs", "at", "at_ms"):
                if key in schedule:
                    return _parse_epoch(schedule[key])
        for key in ("nextRunAtMs", "nextRunAt", "next"):
            if key in schedule:
                return _parse_epoch(schedule[key])
    for key in ("nextRunAtMs", "nextRunAt", "next_run", "next"):
        if key in job:
            return _parse_epoch(job[key])
    return None


def _format_countdown(target: Optional[datetime]) -> str:
    if not target:
        return "unknown"
    now = datetime.now(timezone.utc)
    if target.tzinfo is None:
        target = target.replace(tzinfo=timezone.utc)
    delta = int((target - now).total_seconds())
    if delta <= 0:
        return "due"
    minutes, seconds = divmod(delta, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


class CronJobsPanel(Static):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.border_title = "Cron Jobs"

    def refresh_panel(self) -> None:
        jobs, error = _load_jobs()
        if error:
            self.update(f"[bold #ff6b6b]Cron load failed[/]\n{error}")
            return
        parsed: List[Dict[str, Any]] = []
        for job in jobs:
            name = str(job.get("name") or job.get("id") or "job")
            schedule = job.get("schedule") or job.get("cron")
            schedule_text = "-"
            if isinstance(schedule, dict):
                if schedule.get("kind") == "cron":
                    schedule_text = str(schedule.get("expr") or schedule.get("cron") or "-")
                elif schedule.get("kind") == "at":
                    schedule_text = "at"
            elif schedule:
                schedule_text = str(schedule)
            next_dt = _extract_next_run(job)
            parsed.append(
                {
                    "name": name,
                    "schedule": schedule_text,
                    "next_dt": next_dt,
                }
            )

        parsed.sort(key=lambda item: item["next_dt"] or datetime.max.replace(tzinfo=timezone.utc))
        next_job = parsed[0] if parsed else None
        countdown = _format_countdown(next_job["next_dt"] if next_job else None)

        lines = [
            f"[bold #ffb3c1]Next in:[/] {countdown}",
            "",
        ]
        for job in parsed[:5]:
            per_job = _format_countdown(job["next_dt"])
            lines.append(
                f"[bold #c8f7c5]{job['name']}[/] · {per_job}"
            )

        if len(lines) <= 2:
            lines.append("No upcoming jobs found.")

        self.update("\n".join(lines))
