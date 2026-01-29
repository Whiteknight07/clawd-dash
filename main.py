import subprocess
import time
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, RichLog, Static
from rich.markup import escape

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

    CommandLogScreen {
        align: center middle;
    }

    #command-log {
        width: 90%;
        height: 90%;
        border: round #334155;
        background: #0f172a;
        padding: 1 2;
    }

    #command-log-title {
        height: 3;
        content-align: center middle;
        color: #a5d6ff;
    }

    #command-log-body {
        height: 1fr;
        border: round #1f2937;
        background: #0b1220;
        padding: 1;
    }

    #command-log-buttons {
        height: 3;
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

    def set_action_status(self, message: str) -> None:
        actions = self.query_one(QuickActionsPanel)
        actions.set_status(message)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id: Optional[str] = event.button.id
        if button_id == "action-refresh":
            self.refresh_all()
            self.set_action_status("Dashboard refreshed.")
        elif button_id == "action-email":
            self.set_action_status("Checking inbox...")
            self.push_screen(CommandLogScreen("Check Emails", ["/root/clawd/nightly-builds/unified-email-checker/check-emails"]))
        elif button_id == "action-canvas":
            self.set_action_status("Canvas assignments coming soon.")
            self.notify("Canvas assignments integration is coming soon.")


class CommandLogScreen(ModalScreen[None]):
    BINDINGS = [("escape", "close", "Close")]

    def __init__(self, title: str, command: list[str]) -> None:
        super().__init__()
        self._title = title
        self._command = command

    def compose(self) -> ComposeResult:
        with Vertical(id="command-log"):
            yield Static(self._title, id="command-log-title")
            yield RichLog(id="command-log-body", highlight=True, markup=True, auto_scroll=True)
            with Horizontal(id="command-log-buttons"):
                yield Button("Close", id="command-log-close", variant="primary")

    def on_mount(self) -> None:
        log = self.query_one("#command-log-body", RichLog)
        log.write(f"$ {' '.join(self._command)}")
        self.app.run_worker(self._run_command, thread=True, name="command-log")

    def action_close(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "command-log-close":
            self.app.pop_screen()

    def _append_line(self, line: str) -> None:
        if not self.is_mounted:
            return
        self.query_one("#command-log-body", RichLog).write(line)

    def _run_command(self) -> None:
        try:
            process = subprocess.Popen(
                self._command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except OSError as exc:
            self.app.call_from_thread(self._append_line, f"[bold #ff6b6b]Error:[/] {exc}")
            self.app.call_from_thread(self.app.set_action_status, "Email check failed to start.")
            return

        assert process.stdout is not None
        for line in process.stdout:
            self.app.call_from_thread(self._append_line, escape(line.rstrip("\n")))

        return_code = process.wait()
        self.app.call_from_thread(self._append_line, f"[bold #a5d6ff]Exit code:[/] {return_code}")
        if return_code == 0:
            self.app.call_from_thread(self.app.set_action_status, "Email check complete.")
        else:
            self.app.call_from_thread(self.app.set_action_status, "Email check finished with errors.")


if __name__ == "__main__":
    ClawdDashApp().run()
