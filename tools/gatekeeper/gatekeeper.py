#!/usr/bin/env python3
"""MAYA Gatekeeper — Permission & Access Control Dashboard.

Visual permission dashboard showing every tool, its risk level, who's
granted access, and live audit state. Nothing skips the Gatekeeper.
That's not a feature — that's the architecture.

Dark MAYA theme. Frameless tkinter desktop app.
"""
from __future__ import annotations

import random
import tkinter as tk
from datetime import datetime
from pathlib import Path

# ═══════════════════════════════════════
# MAYA Design System Colors
# ═══════════════════════════════════════
BG         = "#1a1a2e"
CARD_BG    = "#16213e"
HEADER_BG  = "#0f0f23"
TEXT       = "#e0e0e0"
DIM        = "#888888"
ACCENT     = "#e6a817"       # MAYA gold
GREEN      = "#2dcc5a"
GREEN_BG   = "#1a3a1a"
BLUE       = "#3d7dcc"
RUST       = "#cc6a2a"
RED        = "#cc3333"
RED_BG     = "#3a1a1a"
AMBER      = "#e6a817"
BORDER     = "#2a2a4a"
FONT       = ("Segoe UI", 9)
FONT_SM    = ("Segoe UI", 8)
FONT_BOLD  = ("Segoe UI", 9, "bold")

# ═══════════════════════════════════════
# Permission Registry — every gated action
# ═══════════════════════════════════════

GATE_RULES = [
    {"tool": "file_read",        "risk": "low",     "level": 0, "desc": "Read any file on disk"},
    {"tool": "file_write",       "risk": "medium",  "level": 1, "desc": "Create or modify files"},
    {"tool": "file_delete",      "risk": "high",    "level": 3, "desc": "Delete files/directories"},
    {"tool": "shell_git",        "risk": "low",     "level": 2, "desc": "Git operations (status, diff, log)"},
    {"tool": "shell_npm",        "risk": "medium",  "level": 2, "desc": "Package install (npm, pip, etc.)"},
    {"tool": "shell_sudo",       "risk": "critical","level": 5, "desc": "System-level commands"},
    {"tool": "http_get",         "risk": "low",     "level": 4, "desc": "Outbound HTTP GET requests"},
    {"tool": "http_post",        "risk": "high",    "level": 4, "desc": "Outbound HTTP POST (data egress)"},
    {"tool": "email_send",       "risk": "critical","level": 5, "desc": "Send email on user's behalf"},
    {"tool": "sms_send",         "risk": "critical","level": 5, "desc": "Send SMS / text messages"},
    {"tool": "browser_open",     "risk": "medium",  "level": 4, "desc": "Open URLs in browser"},
    {"tool": "desktop_control",  "risk": "critical","level": 5, "desc": "Mouse/keyboard automation"},
    {"tool": "config_read",      "risk": "low",     "level": 0, "desc": "Read MAYA/hermes config"},
    {"tool": "config_write",     "risk": "high",    "level": 3, "desc": "Modify MAYA/hermes config"},
    {"tool": "api_key_read",     "risk": "high",    "level": 3, "desc": "Read stored API keys"},
    {"tool": "api_key_write",    "risk": "critical","level": 5, "desc": "Store/modify API keys"},
    {"tool": "memory_read",      "risk": "low",     "level": 0, "desc": "Read MAYA memory/context"},
    {"tool": "memory_write",     "risk": "medium",  "level": 1, "desc": "Write to MAYA memory"},
    {"tool": "memory_delete",    "risk": "high",    "level": 3, "desc": "Delete memory entries"},
    {"tool": "cron_manage",      "risk": "medium",  "level": 2, "desc": "Create/edit scheduled jobs"},
]

RISK_COLORS = {
    "low":      {"fg": GREEN, "bg": GREEN_BG},
    "medium":   {"fg": AMBER, "bg": "#2a2010"},
    "high":     {"fg": RUST,  "bg": "#2a1508"},
    "critical": {"fg": RED,   "bg": RED_BG},
}

# Simulated agent profiles
AGENTS = ["Sagan", "Echo", "Raven", "Shadow", "Flint", "Scribe", "Chief", "Cerberus"]

GATE_LOG = []


class Gatekeeper(tk.Tk):
    """MAYA Gatekeeper — permission dashboard."""

    def __init__(self):
        super().__init__()
        self.title("MAYA Gatekeeper")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(520, 580)
        self.overrideredirect(True)
        self.geometry("560x620+270+60")

        self._build_title_bar()
        self._build_body()
        self._animate()

    # ── Title Bar ──────────────────────────

    def _build_title_bar(self):
        bar = tk.Frame(self, bg=HEADER_BG, height=32)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)

        shield = tk.Canvas(bar, width=20, height=20, bg=HEADER_BG, highlightthickness=0)
        shield.create_polygon(10, 2, 18, 6, 18, 12, 13, 18, 10, 20, 7, 18, 2, 12, 2, 6,
                              fill="", outline=ACCENT, width=2)
        shield.create_text(10, 11, text="✓", fill=ACCENT, font=("Segoe UI", 9, "bold"))
        shield.pack(side=tk.LEFT, padx=(8, 6), pady=6)

        tk.Label(bar, text="MAYA Gatekeeper", bg=HEADER_BG, fg=ACCENT,
                 font=FONT_BOLD).pack(side=tk.LEFT, pady=4)

        # Status badge
        self.status_badge = tk.Label(bar, text="● GATING ACTIVE", bg=HEADER_BG, fg=GREEN,
                                     font=("Segoe UI", 7, "bold"))
        self.status_badge.pack(side=tk.LEFT, padx=10, pady=5)

        for lbl, cmd, hbg in [
            ("—", self.iconify, "#333344"),
            ("✕", self.destroy, "#661111"),
        ]:
            tk.Button(bar, text=lbl, bg=HEADER_BG, fg=TEXT, font=("Segoe UI", 10),
                      relief=tk.FLAT, command=cmd, activebackground=hbg,
                      activeforeground="#fff", bd=0, padx=8).pack(side=tk.RIGHT, pady=2)

        for w in [bar] + list(bar.winfo_children()):
            w.bind("<Button-1>", self._start_drag)
            w.bind("<B1-Motion>", self._on_drag)

    # ── Body ──────────────────────────────

    def _build_body(self):
        body = tk.Frame(self, bg=BG)
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 4))

        # Summary bar
        summary = tk.Frame(body, bg=CARD_BG, height=36, highlightthickness=1,
                           highlightbackground=BORDER)
        summary.pack(fill=tk.X, pady=(0, 8))
        summary.pack_propagate(False)
        self.sum_vars = {}
        for label in ["Total", "Granted", "Denied", "Blocked"]:
            fg = GREEN if label == "Granted" else RED if label in ("Denied", "Blocked") else TEXT
            var = tk.StringVar(value="—")
            self.sum_vars[label.lower()] = var
            f = tk.Frame(summary, bg=CARD_BG)
            f.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
            tk.Label(f, text=label, bg=CARD_BG, fg=DIM, font=("Segoe UI", 7)).pack(pady=(4, 0))
            tk.Label(f, textvariable=var, bg=CARD_BG, fg=fg,
                     font=("Segoe UI", 11, "bold")).pack(pady=(0, 4))

        # Column headers
        hdr = tk.Frame(body, bg=BG)
        hdr.pack(fill=tk.X)
        cols = [("TOOL", 16), ("RISK", 8), ("LEVEL", 6), ("DESCRIPTION", 30), ("STATE", 10)]
        for col, width in cols:
            tk.Label(hdr, text=col, bg=BG, fg=DIM, font=("Segoe UI", 7, "bold"),
                     width=width, anchor=tk.W).pack(side=tk.LEFT)

        # Separator
        tk.Frame(body, bg=BORDER, height=1).pack(fill=tk.X, pady=2)

        # Scrollable gate list
        canvas_frame = tk.Frame(body, bg=BG)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_frame, bg=BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.gate_list = tk.Frame(self.canvas, bg=BG)

        self.gate_list.bind("<Configure>",
                            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.gate_list, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Build gate rows
        self._gate_widgets = {}
        for rule in GATE_RULES:
            self._build_gate_row(rule)

        # Log footer
        self.log_box = tk.Text(body, bg=CARD_BG, fg=DIM, font=("Consolas", 8),
                               wrap=tk.WORD, height=4, bd=0, padx=8, pady=4,
                               state=tk.DISABLED, relief=tk.FLAT)
        self.log_box.pack(fill=tk.X, pady=(8, 4))

        self.footer = tk.Label(self, text="Gatekeeper: every tool gated — no exceptions",
                               bg=BG, fg=DIM, font=("Segoe UI", 7))
        self.footer.pack(pady=(0, 6))

    def _build_gate_row(self, rule):
        row = tk.Frame(self.gate_list, bg=CARD_BG, height=26)
        row.pack(fill=tk.X, pady=1)
        row.pack_propagate(False)

        risk_info = RISK_COLORS.get(rule["risk"], RISK_COLORS["low"])

        # Tool name
        tk.Label(row, text=rule["tool"], bg=CARD_BG, fg=TEXT,
                 font=FONT_SM, width=16, anchor=tk.W).pack(side=tk.LEFT, padx=(6, 0))

        # Risk badge
        risk_lbl = tk.Label(row, text=rule["risk"].upper(), bg=risk_info["bg"],
                            fg=risk_info["fg"], font=("Segoe UI", 7, "bold"),
                            width=7, anchor=tk.CENTER)
        risk_lbl.pack(side=tk.LEFT, padx=4)

        # Level
        tk.Label(row, text=f"L{rule['level']}", bg=CARD_BG, fg=DIM,
                 font=FONT_SM, width=5, anchor=tk.CENTER).pack(side=tk.LEFT)

        # Description
        tk.Label(row, text=rule["desc"], bg=CARD_BG, fg=DIM,
                 font=("Segoe UI", 7), width=28, anchor=tk.W).pack(side=tk.LEFT, padx=4)

        # State
        state_lbl = tk.Label(row, text="DENIED", bg=CARD_BG, fg=RED,
                             font=("Segoe UI", 7, "bold"), width=9, anchor=tk.E)
        state_lbl.pack(side=tk.RIGHT, padx=6)

        self._gate_widgets[rule["tool"]] = {"risk": risk_lbl, "state": state_lbl}

    # ── Animation ──────────────────────────

    def _animate(self):
        """Simulate live permission decisions."""
        active_agent = random.choice(AGENTS)
        granted = 0
        denied = 0
        blocked = 0

        for rule in GATE_RULES:
            widgets = self._gate_widgets[rule["tool"]]

            # Simulate gate decision
            roll = random.random()
            if rule["risk"] == "low":
                state = "GRANTED" if roll < 0.9 else "DENIED"
            elif rule["risk"] == "medium":
                state = "GRANTED" if roll < 0.7 else "DENIED" if roll < 0.9 else "BLOCKED"
            elif rule["risk"] == "high":
                state = "GRANTED" if roll < 0.4 else "DENIED" if roll < 0.75 else "BLOCKED"
            else:  # critical
                state = "GRANTED" if roll < 0.15 else "DENIED" if roll < 0.5 else "BLOCKED"

            color = GREEN if state == "GRANTED" else AMBER if state == "DENIED" else RED
            widgets["state"].configure(text=state, fg=color)

            if state == "GRANTED":
                granted += 1
            elif state == "DENIED":
                denied += 1
            else:
                blocked += 1

        self.sum_vars["total"].set(str(len(GATE_RULES)))
        self.sum_vars["granted"].set(str(granted))
        self.sum_vars["denied"].set(str(denied))
        self.sum_vars["blocked"].set(str(blocked))

        # Add log
        ts = datetime.now().strftime("%H:%M:%S")
        log_entry = (f"[{ts}] GATE [{active_agent}] :: {granted} granted, "
                     f"{denied} denied, {blocked} blocked — "
                     f"{(granted/len(GATE_RULES)*100):.0f}% allow rate")
        GATE_LOG.append(log_entry)
        if len(GATE_LOG) > 30:
            GATE_LOG.pop(0)

        self.log_box.configure(state=tk.NORMAL)
        self.log_box.delete("1.0", tk.END)
        for line in GATE_LOG[-4:]:
            self.log_box.insert(tk.END, line + "\n")
        self.log_box.configure(state=tk.DISABLED)
        self.log_box.see(tk.END)

        self.footer.configure(
            text=f"Gatekeeper :: {granted}/{len(GATE_RULES)} tools open — "
                 f"agent={active_agent} | {ts}")

        self.after(random.randint(4000, 7000), self._animate)

    # ── Drag ──────────────────────────────

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event):
        self.geometry(f"+{self.winfo_x() + event.x - self._drag_x}"
                      f"+{self.winfo_y() + event.y - self._drag_y}")


if __name__ == "__main__":
    app = Gatekeeper()
    app.mainloop()
