#!/usr/bin/env python3
"""MAYA ARC Context Engine — Adaptive Relational Context desktop monitor.

Shows live context classification, model routing logic, and permission
gating in a dark-themed MAYA tkinter app. Every request flows through:
  Context Classifier → Router → Gatekeeper → Audit Log

ARC = Adaptive Relational Context. It selects the right memory, profile,
and project data for the right model at the right time — without dumping
your entire life into every prompt.
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
BLUE_BG    = "#1a2a4a"
RUST       = "#cc6a2a"
RUST_BG    = "#3a1a0a"
RED        = "#cc3333"
RED_BG     = "#3a1a1a"
PURPLE     = "#9b4dca"
PURPLE_BG  = "#2a1a3a"
BORDER     = "#2a2a4a"
FONT       = ("Segoe UI", 9)
FONT_SM    = ("Segoe UI", 8)
FONT_BOLD  = ("Segoe UI", 9, "bold")
FONT_H1    = ("Segoe UI", 13, "bold")

# ═══════════════════════════════════════
# Simulated ARC Context State
# ═══════════════════════════════════════

CONTEXT_MODES = {
    "coding":     {"icon": "</>", "color": BLUE,    "desc": "Writing/editing source code"},
    "research":   {"icon": "🔍",  "color": PURPLE,  "desc": "Looking up docs, comparing sources"},
    "architecture":{"icon": "🏛",  "color": ACCENT,  "desc": "System design, planning, decisions"},
    "security":   {"icon": "🛡",  "color": RED,     "desc": "Auth, audit, credential handling"},
    "creative":   {"icon": "✨",  "color": GREEN,   "desc": "Writing, design, brainstorming"},
    "operations": {"icon": "⚙",   "color": RUST,    "desc": "Deploy, monitor, infrastructure"},
    "review":     {"icon": "👁",  "color": "#5a9acc","desc": "Code review, QA, acceptance"},
}

MODEL_LANES = {
    "openai_controller":  {"label": "OpenAI Controller",  "color": "#4a90d9",
                           "desc": "Complex reasoning, architecture, security"},
    "deepseek_worker":    {"label": "DeepSeek Worker",    "color": "#52d273",
                           "desc": "Fast, cheap — raw code & bulk work"},
    "gemini_research":    {"label": "Gemini Research",    "color": ACCENT,
                           "desc": "1M context window, free tier"},
    "local_private":      {"label": "Ollama Local",       "color": RUST,
                           "desc": "Fully offline, private drafts"},
}

PERMISSION_LEVELS = {
    "read":        {"level": 0, "color": GREEN,   "desc": "Read files, list dirs, search"},
    "write_local": {"level": 1, "color": BLUE,    "desc": "Write local files, create dirs"},
    "shell_safe":  {"level": 2, "color": ACCENT,  "desc": "Shell: git, npm, pip (no sudo)"},
    "shell_admin": {"level": 3, "color": RUST,    "desc": "Shell: system-level, installs"},
    "network":     {"level": 4, "color": PURPLE,  "desc": "HTTP, API calls, webhooks"},
    "external":    {"level": 5, "color": RED,     "desc": "Post externally, send messages"},
}

AUDIT_LOG = []


class ARCContextEngine(tk.Tk):
    """MAYA ARC Context Engine — live context routing dashboard."""

    def __init__(self):
        super().__init__()
        self.title("MAYA ARC Context Engine")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(520, 620)
        self.overrideredirect(True)
        self.geometry("540x660+220+80")

        self._build_title_bar()
        self._build_body()
        self._animate()

    # ── Title Bar ──────────────────────────

    def _build_title_bar(self):
        bar = tk.Frame(self, bg=HEADER_BG, height=32)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)

        orb = tk.Canvas(bar, width=20, height=20, bg=HEADER_BG, highlightthickness=0)
        orb.create_oval(3, 3, 17, 17, outline=ACCENT, width=2)
        orb.create_arc(3, 3, 17, 17, start=90, extent=-240, outline=ACCENT, width=2, style="arc")
        orb.pack(side=tk.LEFT, padx=(8, 6), pady=6)

        tk.Label(bar, text="ARC Context Engine", bg=HEADER_BG, fg=ACCENT,
                 font=FONT_BOLD).pack(side=tk.LEFT, pady=4)

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

        # ── Panel 1: Context Classification ──
        self._section_header(body, "◉  CONTEXT CLASSIFICATION", ACCENT)
        self.ctx_frame = tk.Frame(body, bg=CARD_BG, highlightthickness=1,
                                  highlightbackground=BORDER)
        self.ctx_frame.pack(fill=tk.X, pady=(2, 8), ipady=6)
        self.ctx_inner = tk.Frame(self.ctx_frame, bg=CARD_BG)
        self.ctx_inner.pack(fill=tk.X, padx=10, pady=6)
        self.ctx_mode_var = tk.StringVar(value="idle")
        self.ctx_desc_var = tk.StringVar(value="Waiting for input...")
        self.ctx_mode_lbl = tk.Label(self.ctx_inner, textvariable=self.ctx_mode_var,
                                     bg=CARD_BG, fg=TEXT, font=("Segoe UI", 18, "bold"))
        self.ctx_mode_lbl.pack(anchor=tk.W)
        self.ctx_desc_lbl = tk.Label(self.ctx_inner, textvariable=self.ctx_desc_var,
                                     bg=CARD_BG, fg=DIM, font=FONT_SM)
        self.ctx_desc_lbl.pack(anchor=tk.W, pady=(2, 0))

        # Context details
        self.ctx_details = tk.Frame(self.ctx_inner, bg=CARD_BG)
        self.ctx_details.pack(fill=tk.X, pady=(6, 0))
        self._ctx_vars = {}
        for key in ["mode", "confidence", "tokens_used", "profiles_active"]:
            row = tk.Frame(self.ctx_details, bg=CARD_BG)
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=f"{key.replace('_',' ').title()}:", bg=CARD_BG, fg=DIM,
                     font=FONT_SM, width=14, anchor=tk.W).pack(side=tk.LEFT)
            var = tk.StringVar(value="—")
            self._ctx_vars[key] = var
            tk.Label(row, textvariable=var, bg=CARD_BG, fg=TEXT,
                     font=FONT_SM).pack(side=tk.LEFT)

        # ── Panel 2: Model Routing Logic ──
        self._section_header(body, "◉  MODEL ROUTING", BLUE)
        self.route_frame = tk.Frame(body, bg=BG)
        self.route_frame.pack(fill=tk.X, pady=(2, 8))
        self._lane_widgets = {}
        self._lane_indicators = {}
        for lane_id, lane_info in MODEL_LANES.items():
            self._build_lane_row(lane_id, lane_info)

        # ── Panel 3: Permission Gating ──
        self._section_header(body, "◉  PERMISSION GATING", GREEN)
        self.perm_frame = tk.Frame(body, bg=BG)
        self.perm_frame.pack(fill=tk.X, pady=(2, 8))
        self._perm_widgets = {}
        for perm_id, perm_info in PERMISSION_LEVELS.items():
            self._build_perm_row(perm_id, perm_info)

        # ── Panel 4: Audit Trail ──
        self._section_header(body, "◉  AUDIT TRAIL (last 5 events)", PURPLE)
        self.audit_box = tk.Text(body, bg=CARD_BG, fg=DIM, font=("Consolas", 8),
                                 wrap=tk.WORD, height=6, bd=0, padx=8, pady=6,
                                 state=tk.DISABLED, relief=tk.FLAT)
        self.audit_box.pack(fill=tk.BOTH, expand=True, pady=(2, 4))

        # Footer
        self.footer = tk.Label(self, text="ARC active — auto-simulating context routing",
                               bg=BG, fg=DIM, font=("Segoe UI", 7))
        self.footer.pack(pady=(0, 6))

    def _section_header(self, parent, text, color):
        hdr = tk.Frame(parent, bg=BG)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text=text, bg=BG, fg=color,
                 font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT)
        sep = tk.Frame(hdr, bg=BORDER, height=1)
        sep.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0), pady=8)

    def _build_lane_row(self, lane_id, info):
        row = tk.Frame(self.route_frame, bg=CARD_BG, height=28)
        row.pack(fill=tk.X, pady=1)
        row.pack_propagate(False)

        dot = tk.Label(row, text="●", bg=CARD_BG, fg=info["color"],
                       font=("Segoe UI", 10))
        dot.pack(side=tk.LEFT, padx=(8, 4))

        name_lbl = tk.Label(row, text=info["label"], bg=CARD_BG, fg=TEXT,
                            font=FONT_SM, width=16, anchor=tk.W)
        name_lbl.pack(side=tk.LEFT)

        desc_lbl = tk.Label(row, text=info["desc"], bg=CARD_BG, fg=DIM,
                            font=("Segoe UI", 7), width=30, anchor=tk.W)
        desc_lbl.pack(side=tk.LEFT, padx=4)

        active_lbl = tk.Label(row, text="IDLE", bg=CARD_BG, fg=DIM,
                              font=("Segoe UI", 7, "bold"), width=8, anchor=tk.E)
        active_lbl.pack(side=tk.RIGHT, padx=8)

        self._lane_widgets[lane_id] = {"dot": dot, "active": active_lbl}

    def _build_perm_row(self, perm_id, info):
        row = tk.Frame(self.perm_frame, bg=CARD_BG, height=24)
        row.pack(fill=tk.X, pady=1)
        row.pack_propagate(False)

        level_lbl = tk.Label(row, text=f"L{info['level']}", bg=CARD_BG, fg=info["color"],
                             font=("Segoe UI", 8, "bold"), width=3, anchor=tk.CENTER)
        level_lbl.pack(side=tk.LEFT, padx=(6, 2))

        name_lbl = tk.Label(row, text=perm_id.replace("_", " ").title(), bg=CARD_BG,
                            fg=TEXT, font=FONT_SM, width=13, anchor=tk.W)
        name_lbl.pack(side=tk.LEFT)

        desc_lbl = tk.Label(row, text=info["desc"], bg=CARD_BG, fg=DIM,
                            font=("Segoe UI", 7), width=30, anchor=tk.W)
        desc_lbl.pack(side=tk.LEFT, padx=4)

        granted_lbl = tk.Label(row, text="DENIED", bg=CARD_BG, fg=RED,
                               font=("Segoe UI", 7, "bold"), width=8, anchor=tk.E)
        granted_lbl.pack(side=tk.RIGHT, padx=8)

        self._perm_widgets[perm_id] = {"granted": granted_lbl}

    # ── Animation / Simulation ────────────

    def _animate(self):
        """Simulate live ARC context routing decisions."""
        # Pick a random context mode
        modes = list(CONTEXT_MODES.items())
        mode_key, mode_info = random.choice(modes)

        self.ctx_mode_var.set(f"{mode_info['icon']}  {mode_key.upper()}")
        self.ctx_desc_var.set(mode_info["desc"])
        self.ctx_mode_lbl.configure(fg=mode_info["color"])

        # Simulate confidence
        conf = random.randint(78, 99)
        self._ctx_vars["mode"].set(mode_key)
        self._ctx_vars["confidence"].set(f"{conf}%")
        self._ctx_vars["tokens_used"].set(f"{random.randint(200, 8000):,}")
        self._ctx_vars["profiles_active"].set(f"{random.randint(1, 5)} profiles")

        # Route to best lane
        all_lanes = list(MODEL_LANES.keys())
        best_lane = random.choice(all_lanes[:3]) if mode_key in ("coding", "security", "architecture") \
                    else random.choice(all_lanes[2:])

        for lid, widgets in self._lane_widgets.items():
            if lid == best_lane:
                widgets["dot"].configure(fg=GREEN)
                widgets["active"].configure(text="ACTIVE", fg=GREEN)
            else:
                widgets["dot"].configure(fg=DIM)
                widgets["active"].configure(text="IDLE", fg=DIM)

        # Filter lanes as unavailable randomly
        unavailable = random.sample([l for l in all_lanes if l != best_lane], k=min(2, len(all_lanes)-1))
        for ul in unavailable:
            self._lane_widgets[ul]["dot"].configure(fg=RED)
            self._lane_widgets[ul]["active"].configure(text="OFFLINE", fg=RED)

        # Permission gating
        # Grant permissions based on context mode
        perms_to_grant = {"read", "write_local"}
        if mode_key in ("coding", "operations"):
            perms_to_grant.update({"shell_safe"})
        if mode_key in ("operations", "security"):
            perms_to_grant.update({"network", "shell_admin"})
        if mode_key == "security":
            perms_to_grant.add("external")

        for pid, widgets in self._perm_widgets.items():
            if pid in perms_to_grant:
                widgets["granted"].configure(text="GRANTED", fg=GREEN)
            elif random.random() > 0.7 and pid != "read":
                widgets["granted"].configure(text="ASK", fg=ACCENT)
            else:
                widgets["granted"].configure(text="DENIED", fg=RED)

        # Add audit event
        ts = datetime.now().strftime("%H:%M:%S")
        event = (f"[{ts}] ARC :: mode={mode_key} conf={conf}% "
                 f"→ route={MODEL_LANES[best_lane]['label']} "
                 f"| permissions={len(perms_to_grant)} granted "
                 f"| tokens_est={self._ctx_vars['tokens_used'].get()}")
        AUDIT_LOG.append(event)
        if len(AUDIT_LOG) > 50:
            AUDIT_LOG.pop(0)

        self.audit_box.configure(state=tk.NORMAL)
        self.audit_box.delete("1.0", tk.END)
        for line in AUDIT_LOG[-5:]:
            self.audit_box.insert(tk.END, line + "\n")
        self.audit_box.configure(state=tk.DISABLED)
        self.audit_box.see(tk.END)

        now = datetime.now().strftime("%H:%M:%S")
        self.footer.configure(text=f"ARC active — last routing {now} | mode={mode_key} → "
                                   f"{MODEL_LANES[best_lane]['label']}")

        # Re-run every 3-6 seconds
        self.after(random.randint(3000, 6000), self._animate)

    # ── Drag ──────────────────────────────

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event):
        self.geometry(f"+{self.winfo_x() + event.x - self._drag_x}"
                      f"+{self.winfo_y() + event.y - self._drag_y}")


if __name__ == "__main__":
    app = ARCContextEngine()
    app.mainloop()
