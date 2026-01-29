import json
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from textual.widgets import Static

CRON_COMMAND = ["moltbot", "cron", "list", "--json"]


PLACEHOLDER_JOBS = [
    {
        "name": "daily_summary",
        "schedule": "0 7 * * *",
        "next_run": "2026-01-30T07:00:00Z",
    },
    {
        "name": "sync_memory",
        "schedule": "*/15 * * * *",
        "next_run": "2026-01-29T14:15:00Z",
    },
    {
        "name": "nightly_cleanup",
        "schedule": "30 2 * * *",
        "next_run": "2026-01-30T02:30:00Z",
    },
]


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


def _load_jobs() -> List[Dict[str, Any]]:
    output = _run_command(CRON_COMMAND)
    if not output:
        return PLACEHOLDER_JOBS
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return PLACEHOLDER_JOBS
    if isinstance(data, dict) and "jobs" in data:
        jobs = data["jobs"]
    else:
        jobs = data
    if not isinstance(jobs, list):
        return PLACEHOLDER_JOBS
    return jobs


def _parse_datetime(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return datetime.fromisoformat(value)
    except ValueError:
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
        jobs = _load_jobs()
        parsed: List[Dict[str, Any]] = []
        for job in jobs:
            name = str(job.get("name") or job.get("id") or "job")
            schedule = str(job.get("schedule") or job.get("cron") or "-")
            next_run = job.get("next_run") or job.get("next") or job.get("nextRun")
            parsed.append(
                {
                    "name": name,
                    "schedule": schedule,
                    "next_run": next_run,
                    "next_dt": _parse_datetime(str(next_run)) if next_run else None,
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
            lines.append(
                f"[bold #c8f7c5]{job['name']}[/] · {job['schedule']}"
            )

        if len(lines) <= 2:
            lines.append("No upcoming jobs found.")

        self.update("\n".join(lines))
