from typing import Any

from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static


class QuickActionsPanel(Vertical):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.border_title = "Quick Actions"

    def compose(self):
        with Horizontal(id="action-buttons"):
            yield Button("Check Emails", id="action-email", variant="success")
            yield Button("Canvas Assignments", id="action-canvas", variant="warning")
            yield Button("Refresh Dashboard", id="action-refresh", variant="primary")
        yield Static("Standing by.", id="action-status")

    def set_status(self, message: str) -> None:
        self.query_one("#action-status", Static).update(message)
