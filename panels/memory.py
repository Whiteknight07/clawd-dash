from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from textual.widgets import Static

MEMORY_DIR = Path("/root/clawd/memory")

PLACEHOLDER_FILES = [
    ("2026-01-29_reflection.md", "Stavan updated morning briefing flow."),
    ("2026-01-28_context.txt", "Weekly goal: stabilize cron triggers."),
    ("2026-01-28_ideas.md", "Investigate new canvas integrations."),
    ("2026-01-27_notes.txt", "Deployed moltbot v2.4.1."),
    ("2026-01-26_log.md", "System health checks passed."),
]


def _load_memory_files() -> List[Tuple[str, str]]:
    if not MEMORY_DIR.exists():
        return PLACEHOLDER_FILES

    files = [path for path in MEMORY_DIR.iterdir() if path.is_file()]
    if not files:
        return PLACEHOLDER_FILES

    files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    entries: List[Tuple[str, str]] = []
    for path in files[:5]:
        preview = "(empty)"
        try:
            content = path.read_text(encoding="utf-8", errors="ignore").strip()
            preview = content.splitlines()[0] if content else "(empty)"
        except OSError:
            preview = "(unreadable)"
        entries.append((path.name, preview))
    return entries


class MemoryPanel(Static):
    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.border_title = "Memory"

    def refresh_panel(self) -> None:
        entries = _load_memory_files()
        lines = ["[bold #ffc078]Recent updates[/]"]
        for filename, preview in entries:
            lines.append(f"[bold #f1f3f5]{filename}[/]")
            lines.append(f"  [#d0ebff]{preview}[/]")
        self.update("\n".join(lines))
