from typing import Any

import psutil
from textual.widgets import Static


def _format_bytes(value: float) -> str:
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = float(value)
    for unit in units:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} EB"


class SystemHealthPanel(Static):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.border_title = "System Health"

    def refresh_panel(self) -> None:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        lines = [
            f"[bold #8ce99a]CPU:[/] {cpu_percent:.1f}%",
            f"[bold #74c0fc]Memory:[/] {memory.percent:.1f}% ({_format_bytes(memory.used)} / {_format_bytes(memory.total)})",
            f"[bold #ffd43b]Disk:[/] {disk.percent:.1f}% ({_format_bytes(disk.used)} / {_format_bytes(disk.total)})",
        ]
        self.update("\n".join(lines))
