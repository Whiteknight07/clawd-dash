import time
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Footer, Header, Button

from panels import (
    CronJobsPanel,
    MemoryPanel,
    QuickActionsPanel,
    SessionPanel,
    SystemHealthPanel,
)


class ClawdDashApp(App):
    CSS = """
    Screen {
        background: #0b1220;
        color: #e2e8f0;
    }

    #grid {
        layout: grid;
        grid-size: 2 3;
        grid-columns: 1fr 1fr;
        grid-rows: 1fr 1fr 7;
        grid-gutter: 1 2;
        padding: 1 2;
    }

    .panel {
        border: round #334155;
        background: #111827;
        padding: 1 2;
    }

    #session {
        border-title-color: #7ee787;
    }

    #crons {
        border-title-color: #ffb3c1;
    }

    #memory {
        border-title-color: #ffc078;
    }

    #health {
        border-title-color: #8ce99a;
    }

    #actions {
        column-span: 2;
        border-title-color: #a5d6ff;
        height: 7;
    }

    #action-buttons {
        height: 3;
        content-align: center middle;
    }

    Button {
        margin: 0 1;
    }

    #action-status {
        color: #94a3b8;
        margin-top: 1;
        content-align: center middle;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.start_time = time.time()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="grid"):
            yield SessionPanel(self.start_time, id="session", classes="panel")
            yield CronJobsPanel(id="crons", classes="panel")
            yield MemoryPanel(id="memory", classes="panel")
            yield SystemHealthPanel(id="health", classes="panel")
            yield QuickActionsPanel(id="actions", classes="panel")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_all()
        self.set_interval(30, self.refresh_all)

    def action_refresh(self) -> None:
        self.refresh_all()

    def refresh_all(self) -> None:
        self.query_one(SessionPanel).refresh_panel()
        self.query_one(CronJobsPanel).refresh_panel()
        self.query_one(MemoryPanel).refresh_panel()
        self.query_one(SystemHealthPanel).refresh_panel()

    def _set_action_status(self, message: str) -> None:
        actions = self.query_one(QuickActionsPanel)
        actions.set_status(message)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id: Optional[str] = event.button.id
        if button_id == "action-refresh":
            self.refresh_all()
            self._set_action_status("Dashboard refreshed.")
        elif button_id == "action-email":
            self._set_action_status("Checking inbox... (placeholder)")
        elif button_id == "action-canvas":
            self._set_action_status("Fetching Canvas assignments... (placeholder)")


if __name__ == "__main__":
    ClawdDashApp().run()
