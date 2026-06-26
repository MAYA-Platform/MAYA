#!/usr/bin/env python3
"""MAYA Staff Tracker — live status board for all agents.
Clean, dark theme, MAYA colors. Shows who's working, upcoming, available.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread
import time

HERMES_HOME = Path.home() / "AppData" / "Local" / "hermes"

# ── Colors (MAYA Usage Dashboard style) ──
BG       = "#1a1a2e"
CARD_BG  = "#16213e"
HEADER   = "#0f0f23"
TEXT     = "#e0e0e0"
DIM      = "#888888"
GREEN    = "#2d4a2d"
GOLD     = "#e6a817"
RUST     = "#8b3a1a"
RED      = "#4d1a1a"
BLUE     = "#2d3d5a"
WORKING  = "#1a4a1a"  # bright green indicator
IDLE     = "#3a3a1a"  # amber
OFFLINE  = "#3a1a1a"  # red indicator
SCHEDULED = "#1a2a4a" # blue indicator

# ── Agent Registry ──
AGENTS = {
    # Intelligence
    "Sagan":     {"cron": "4715d13c843e", "layer": "Intelligence", "role": "Technical Scout",
                  "blurb": "Scours GitHub, HN, and dev blogs for bleeding-edge tech signals. If it compiles, Sagan saw it first."},
    "Echo":      {"cron": "f628535fb5b9", "layer": "Intelligence", "role": "Social Scout",
                  "blurb": "Listens to the social web — Twitter, Reddit, Discord. Filters noise into signal before breakfast."},
    "Raven":     {"cron": "a9614e4f63c0", "layer": "Intelligence", "role": "Market Scout",
                  "blurb": "Tracks competitors, pricing moves, and market shifts. Never misses a funding round or pivot."},
    "Shadow":    {"cron": "19572184f28a", "layer": "Intelligence", "role": "Synthesis / Banker",
                  "blurb": "The last mile of intelligence. Distills everything Sagan, Echo, and Raven found into one tight brief."},
    # Discovery
    "Flint":     {"cron": "0eeb52a9fadd", "layer": "Discovery", "role": "Prospector",
                  "blurb": "Pans the streams for golden repos. Finds projects before they trend. The original open-source bloodhound."},
    "Darwin":    {"cron": "44304a629615", "layer": "Discovery", "role": "Ecosystem Watch",
                  "blurb": "Watches package registries, SDK releases, and framework shifts. Knows what's fit to survive."},
    "Holmes":    {"cron": "187ccfedf5e9", "layer": "Discovery", "role": "Personality Scout",
                  "blurb": "Profiles key people — who's shipping, who's hiring, who's worth watching. The org chart in his head."},
    # Maintenance
    "Rust":      {"cron": "535b0c93de50", "layer": "Maintenance", "role": "Link Rot Checker",
                  "blurb": "Chases 404s like a terrier. Nothing rusts on his watch. Link rot is a personal insult."},
    "Plumb":     {"cron": "a7481bac3141", "layer": "Maintenance", "role": "Desktop Health",
                  "blurb": "Keeps the pipes clear — disk space, memory, running services. Your desktop's silent guardian."},
    "Cerberus":  {"cron": "2e9a60212102", "layer": "Maintenance", "role": "API Key Janitor",
                  "blurb": "Three heads, one job: make sure every API key is valid, rotated, and never committed to a repo."},
    "Argus":     {"cron": "d011d096dfc5", "layer": "Maintenance", "role": "Cron Health Watchdog",
                  "blurb": "Hundred eyes on every cron job. If a schedule fails, Argus knew five minutes before you did."},
    "Vantage":   {"cron": "00fd41687bbc", "layer": "Maintenance", "role": "Repo Watchtower",
                  "blurb": "Perched above every MAYA repo. New commits, stale branches, merge conflicts — nothing escapes the tower."},
    # Memory
    "Scribe":    {"cron": "bf10c46c55e1", "layer": "Memory", "role": "Session Scout",
                  "blurb": "Reads every session, finds every insight. Your second brain's librarian — Dewey Decimal but cooler."},
    "Quill":     {"cron": "a8e568016a0f", "layer": "Memory", "role": "Personal Note-Taker",
                  "blurb": "Catches the thoughts you didn't write down. Drafts, ideas, late-night brain dumps — all filed."},
    "Alembic":   {"cron": "dcd8b655c3a9", "layer": "Memory", "role": "Memory Distiller",
                  "blurb": "Takes raw memory and distills it into pure gold. Redundancy? Gone. Clarity? Amplified. The alchemist of recall."},
    # Builder
    "Forge":     {"cron": "8f27ce7914b8", "layer": "Builder", "role": "Builder Pulse",
                  "blurb": "The heartbeat of the build pipeline. Temps the metal, counts the commits, keeps the fire hot."},
    "Nova":      {"cron": "8f27ce7914b8", "layer": "Builder", "role": "Frontend Designer",
                  "blurb": "Pixels, not promises. MAYA's UI doesn't ship until Nova says it glows. Dark mode evangelist."},
    "Anchor":    {"cron": "21e16359bb42", "layer": "Builder", "role": "Git Checkpoint",
                  "blurb": "Commits at every safe harbor. If the repo goes sideways, Anchor knows exactly where to roll back."},
    "Dewey":     {"cron": "933383f2ded0", "layer": "Builder", "role": "Command Library",
                  "blurb": "Catalogues every CLI incantation. One-liners, aliases, scripts — Dewey's got the spellbook."},
    # Security
    "Sage":      {"cron": "cef52a8d50d1", "layer": "Security", "role": "Ethical Hacker",
                  "blurb": "Pokes holes so the bad guys can't. White-hat by trade, paranoid by nature. Trust nothing, verify everything."},
    # Operations
    "Chief":     {"cron": "6fc8244c573c", "layer": "Operations", "role": "Ops Commander",
                  "blurb": "Runs the war room. Coordinates every agent, every cron, every deploy. If Chief is green, MAYA is green."},
    # Delivery
    "Herald":    {"cron": "dc473e7b37c5", "layer": "Delivery", "role": "Hermes Debrief",
                  "blurb": "The voice that closes every session. Summarizes what happened, what changed, and what needs attention."},
    "Shepherd":  {"cron": "a726aa157d9d", "layer": "Delivery", "role": "Business Follow-Up",
                  "blurb": "Rounds up every loose thread from calls, emails, and meetings. Nothing falls through the cracks."},
    "Prism":     {"cron": "31ccac782e29", "layer": "Delivery", "role": "Work Review",
                  "blurb": "Splits every work product into its component parts. Clarity through refraction. No fuzzy deliverables."},
    "Lumen":     {"cron": "9989f584c559", "layer": "Delivery", "role": "ARC Memory Review",
                  "blurb": "Shines a light on memory quality. What's fresh, what's stale, what's missing. The memory illuminator."},
    # Infrastructure
    "Ticker":    {"cron": "ab596ac42718", "layer": "Infrastructure", "role": "MVP Links",
                  "blurb": "Keeps the critical links live. Every MVP endpoint, every dashboard — Ticker watches the pulse."},
    "Cipher":    {"cron": "0280191866d9", "layer": "Infrastructure", "role": "KV Prefix",
                  "blurb": "Manages the key-value namespace. No collisions, no drift, no mystery keys. The KV namespace sovereign."},
    "Ember":     {"cron": "f99327ddd207", "layer": "Infrastructure", "role": "CRL Cache Warmer",
                  "blurb": "Keeps the cache toasty. Pre-warms before you need it. Cold starts are for amateurs."},
    "Galen":     {"cron": "666e017ebee7", "layer": "Infrastructure", "role": "Health Check",
                  "blurb": "The diagnostician. Checks vitals on every service. If something's sick, Galen finds the symptom first."},
    # Gaming
    "Kai":       {"cron": "7f3ba6f7d41d", "layer": "Gaming", "role": "Aggressive Gamer",
                  "blurb": "Rushes in, no fear, all aggro. If there's a meta-breaking strat, Kai already died trying it — and learned."},
    "Zen":       {"cron": "f627dcbec068", "layer": "Gaming", "role": "Methodical Gamer",
                  "blurb": "Turtles up, controls the board. Every move calculated. Zen wins the war Kai started."},
    # Hardware
    "Watts":     {"cron": "e87ea9eb81e4", "layer": "Hardware", "role": "Hardware Engineer",
                  "blurb": "Lives at the silicon level. GPU temps, power draw, thermal throttling — Watts speaks volts and amps."},
}

LAYER_COLORS = {
    "Intelligence": GOLD,
    "Discovery": "#c9a028",
    "Maintenance": "#5a8a5a",
    "Memory": "#6a5a8a",
    "Builder": "#4a7a8a",
    "Security": "#8a3a3a",
    "Operations": "#8a6a3a",
    "Delivery": "#3a6a8a",
    "Infrastructure": "#5a5a6a",
    "Gaming": "#8a4a6a",
    "Hardware": "#6a8a4a",
}


def fetch_cron_state() -> dict:
    """Get live cron job state via hermes CLI."""
    try:
        result = subprocess.run(
            ["hermes", "cron", "list", "--json"],
            cwd=str(HERMES_HOME),
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            jobs = json.loads(result.stdout)
            return {j["job_id"]: j for j in jobs}
    except Exception:
        pass
    return {}


def agent_status(cron_state: dict, agent_id: str) -> tuple[str, str, str]:
    """Return (status, next_run_str, last_status) for an agent."""
    job = cron_state.get(agent_id, {})
    if not job:
        return ("offline", "unknown", "—")

    now = datetime.now(timezone.utc)
    next_run = job.get("next_run_at")
    last_run = job.get("last_run_at")
    last_status = job.get("last_status", "—")
    enabled = job.get("enabled", True)
    paused = job.get("paused_at") is not None

    if paused:
        return ("paused", "paused", last_status)
    if not enabled:
        return ("offline", "disabled", last_status)

    # Check if currently running
    if next_run:
        try:
            next_dt = datetime.fromisoformat(next_run)
            # If next_run is in the past but job ran recently, it's running NOW
            if next_dt < now:
                # Check if last_run was recent (< 10 min ago = still running typical cron)
                if last_run:
                    last_dt = datetime.fromisoformat(last_run)
                    diff_min = (now - last_dt).total_seconds() / 60
                    if diff_min < 15:
                        return ("working", f"running (~{int(diff_min)}m ago)", last_status)
                return ("scheduled", f"due {_format_time_ago(next_dt)}", last_status)
            else:
                return ("idle", _format_time_until(next_dt), last_status)
        except Exception:
            pass

    return ("idle", "—", last_status)


def _format_time_until(dt: datetime) -> str:
    now = datetime.now(timezone.utc)
    diff = (dt.replace(tzinfo=None) - now.replace(tzinfo=None)).total_seconds() / 60
    if diff < 1:
        return "now"
    if diff < 60:
        return f"in {int(diff)}m"
    hrs = int(diff / 60)
    mins = int(diff % 60)
    if hrs < 24:
        return f"in {hrs}h {mins}m"
    return f"in {hrs // 24}d {hrs % 24}h"


def _format_time_ago(dt: datetime) -> str:
    now = datetime.now(timezone.utc)
    diff = (now.replace(tzinfo=None) - dt.replace(tzinfo=None)).total_seconds() / 60
    if diff < 1:
        return "just now"
    if diff < 60:
        return f"{int(diff)}m ago"
    hrs = int(diff / 60)
    return f"{hrs}h ago"


# ═══════════════════════════════════════════


class StaffTracker(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MAYA Staff Tracker")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.geometry("520x640+300+80")

        # Frameless
        self.overrideredirect(True)

        # Title bar
        title_bar = tk.Frame(self, bg=HEADER, height=30)
        title_bar.pack(fill=tk.X)
        title_bar.pack_propagate(False)
        tk.Label(title_bar, text="  ◉  MAYA Staff Tracker", bg=HEADER, fg=GOLD,
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, pady=3)
        tk.Button(title_bar, text="✕", bg=HEADER, fg=TEXT, font=("Segoe UI", 9),
                  relief=tk.FLAT, command=self.destroy, activebackground=RED,
                  bd=0, padx=10).pack(side=tk.RIGHT, pady=2)
        tk.Button(title_bar, text="—", bg=HEADER, fg=TEXT, font=("Segoe UI", 9),
                  relief=tk.FLAT, command=self.iconify, activebackground="#333344",
                  bd=0, padx=8).pack(side=tk.RIGHT, pady=2)

        # Draggable
        title_bar.bind("<Button-1>", self._start_drag)
        title_bar.bind("<B1-Motion>", self._on_drag)
        for c in title_bar.winfo_children():
            c.bind("<Button-1>", self._start_drag)
            c.bind("<B1-Motion>", self._on_drag)

        # Summary bar
        self.summary = tk.Frame(self, bg=CARD_BG, height=36)
        self.summary.pack(fill=tk.X, padx=8, pady=(8, 4))
        self.summary.pack_propagate(False)
        self.sum_working = tk.Label(self.summary, text="", bg=CARD_BG, fg=TEXT,
                                     font=("Segoe UI", 8))
        self.sum_working.pack(side=tk.LEFT, padx=10, pady=6)

        # Canvas + scroll for agent list
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.agent_frame = tk.Frame(self.canvas, bg=BG)

        self.agent_frame.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.agent_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=4)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=4)

        # Footer
        self.footer = tk.Label(self, text="Refreshing...", bg=BG, fg=DIM,
                                font=("Segoe UI", 7))
        self.footer.pack(pady=(2, 6))

        self.agent_widgets = {}
        self._build_agent_rows()
        self._refresh()
        self._auto_refresh()

    def _build_agent_rows(self):
        current_layer = None
        for name, info in AGENTS.items():
            layer = info["layer"]
            if layer != current_layer:
                current_layer = layer
                sep = tk.Frame(self.agent_frame, bg=BG, height=20)
                sep.pack(fill=tk.X)
                color = LAYER_COLORS.get(layer, DIM)
                tk.Label(sep, text=f"  {layer.upper()}", bg=BG, fg=color,
                         font=("Segoe UI", 7, "bold")).pack(side=tk.LEFT)

            row = tk.Frame(self.agent_frame, bg=CARD_BG, height=40)
            row.pack(fill=tk.X, padx=4, pady=1)
            row.pack_propagate(False)

            # Status dot
            dot = tk.Label(row, text=" ● ", bg=CARD_BG, fg=DIM,
                           font=("Segoe UI", 12))
            dot.pack(side=tk.LEFT, padx=(6, 2))

            # Name + role + blurb in a vertical stack
            info_col = tk.Frame(row, bg=CARD_BG)
            info_col.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2, pady=2)

            name_frame = tk.Frame(info_col, bg=CARD_BG)
            name_frame.pack(fill=tk.X)
            name_lbl = tk.Label(name_frame, text=name, bg=CARD_BG, fg=TEXT,
                                font=("Segoe UI", 8, "bold"), anchor=tk.W)
            name_lbl.pack(side=tk.LEFT)

            role_lbl = tk.Label(name_frame, text=f"— {info['role']}", bg=CARD_BG, fg=DIM,
                                font=("Segoe UI", 7), anchor=tk.W)
            role_lbl.pack(side=tk.LEFT, padx=4)

            # Personality blurb
            blurb = info.get("blurb", "")
            if blurb:
                blurb_lbl = tk.Label(info_col, text=blurb, bg=CARD_BG, fg=DIM,
                                     font=("Segoe UI", 6), anchor=tk.W, wraplength=300)
                blurb_lbl.pack(fill=tk.X)
            else:
                blurb_lbl = tk.Label(info_col, text="", bg=CARD_BG)

            # Next run / status
            status_lbl = tk.Label(row, text="", bg=CARD_BG, fg=DIM,
                                  font=("Segoe UI", 7), width=16, anchor=tk.W)
            status_lbl.pack(side=tk.LEFT, padx=2)

            # Health dot
            health_dot = tk.Label(row, text="", bg=CARD_BG, fg=DIM,
                                  font=("Segoe UI", 10))
            health_dot.pack(side=tk.RIGHT, padx=6)

            self.agent_widgets[name] = {
                "dot": dot, "status": status_lbl, "health": health_dot,
                "name": name_lbl, "role": role_lbl, "row": row, "blurb": blurb_lbl
            }

    def _refresh(self):
        cron_state = fetch_cron_state()
        counts = {"working": 0, "idle": 0, "scheduled": 0, "offline": 0, "paused": 0}

        for name, info in AGENTS.items():
            widgets = self.agent_widgets.get(name)
            if not widgets:
                continue

            status, next_str, last_status = agent_status(cron_state, info["cron"])
            counts[status] = counts.get(status, 0) + 1

            # Status dot
            dot_colors = {"working": WORKING, "idle": SCHEDULED, "scheduled": SCHEDULED,
                          "offline": OFFLINE, "paused": OFFLINE}
            widgets["dot"].configure(fg=dot_colors.get(status, DIM))

            # Status text
            status_text = {"working": "ACTIVE", "idle": next_str, "scheduled": next_str,
                           "offline": "offline", "paused": "paused"}
            widgets["status"].configure(text=status_text.get(status, next_str))

            # Health dot
            if last_status == "ok":
                widgets["health"].configure(text="●", fg=GREEN)
            elif last_status == "error" or last_status and "error" in str(last_status).lower():
                widgets["health"].configure(text="●", fg=RED)
            else:
                widgets["health"].configure(text="●", fg=DIM)

        # Update summary
        self.sum_working.configure(
            text=f"Working: {counts['working']}  |  "
                 f"Idle: {counts['idle']}  |  "
                 f"Scheduled: {counts['scheduled']}  |  "
                 f"Offline: {counts['offline']}")

        now = datetime.now().strftime("%H:%M:%S")
        self.footer.configure(text=f"Updated {now}  —  auto-refresh every 60s")

    def _auto_refresh(self):
        self._refresh()
        self.after(60000, self._auto_refresh)

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event):
        x = self.winfo_x() + event.x - self._drag_x
        y = self.winfo_y() + event.y - self._drag_y
        self.geometry(f"+{x}+{y}")


if __name__ == "__main__":
    app = StaffTracker()
    app.mainloop()
