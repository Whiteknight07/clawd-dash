# clawd-dash

A beautiful terminal dashboard for Clawdbot/Moltbot. Built with [Textual](https://textual.textualize.io/) to give Stavan a crisp morning overview of system status.

## Features
- Session panel with model, tokens, and uptime
- Cron jobs panel with countdown to next run
- Memory panel showing recent files from `/root/clawd/memory/`
- System health panel (CPU, memory, disk)
- Quick action buttons (placeholders)
- Auto-refresh every 30 seconds

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Notes
- If `moltbot` commands are unavailable, the dashboard will show graceful placeholder data.
- Use `r` to refresh, `q` to quit.
