#!/usr/bin/env python3
"""MAYA MoE Routing Display — Mixture of Experts visualization.

Shows live expert routing: which expert is active, confidence scores,
load distribution across the expert panel, and recent routing decisions.

MoE = Mixture of Experts: multiple specialized models (experts) gated
by a router that selects the best N experts per request. MAYA's MoE
routes tasks to the most capable expert based on context, cost, speed,
and permission level.

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
ACCENT     = "#e6a817"
GREEN      = "#2dcc5a"
BLUE       = "#3d7dcc"
RUST       = "#cc6a2a"
RED        = "#cc3333"
PURPLE     = "#9b4dca"
TEAL       = "#2dccb0"
PINK       = "#cc5aaa"
BORDER     = "#2a2a4a"
FONT       = ("Segoe UI", 9)
FONT_SM    = ("Segoe UI", 8)
FONT_BOLD  = ("Segoe UI", 9, "bold")
FONT_H1    = ("Segoe UI", 14, "bold")

# ═══════════════════════════════════════
# Expert Registry
# ═══════════════════════════════════════

EXPERTS = [
    {"id": "code_gen",       "name": "Code Generator",    "color": BLUE,
     "specialty": "Code synthesis, refactoring, bug fixes",
     "capacity": 100, "latency_ms": 200},
    {"id": "code_review",    "name": "Code Reviewer",     "color": TEAL,
     "specialty": "Static analysis, style, security review",
     "capacity": 80,  "latency_ms": 300},
    {"id": "arch_planner",   "name": "Architecture Planner","color": ACCENT,
     "specialty": "System design, trade-off analysis",
     "capacity": 60,  "latency_ms": 500},
    {"id": "research_synth", "name": "Research Synthesizer","color": PURPLE,
     "specialty": "Document analysis, summarization, comparison",
     "capacity": 120, "latency_ms": 400},
    {"id": "creative_writer","name": "Creative Writer",   "color": PINK,
     "specialty": "Prose, marketing, brainstorming",
     "capacity": 90,  "latency_ms": 250},
    {"id": "security_auditor","name":"Security Auditor",   "color": RED,
     "specialty": "Vulnerability scanning, auth review",
     "capacity": 40,  "latency_ms": 600},
    {"id": "data_analyst",   "name": "Data Analyst",      "color": GREEN,
     "specialty": "Data parsing, transformation, visualization",
     "capacity": 100, "latency_ms": 350},
    {"id": "ops_orchestrator","name":"Ops Orchestrator",   "color": RUST,
     "specialty": "Deployment, monitoring, incident response",
     "capacity": 50,  "latency_ms": 450},
]

ROUTE_LOG = []
TICK = 0


class MoERoutingDisplay(tk.Tk):
    """MAYA MoE Routing Display — expert panel visualization."""

    def __init__(self):
        super().__init__()
        self.title("MAYA MoE Routing")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(500, 560)
        self.overrideredirect(True)
        self.geometry("520x600+240+40")

        self._expert_widgets = {}
        self._build_title_bar()
        self._build_body()
        self._animate()

    # ── Title Bar ──────────────────────────

    def _build_title_bar(self):
        bar = tk.Frame(self, bg=HEADER_BG, height=32)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)

        node = tk.Canvas(bar, width=20, height=20, bg=HEADER_BG, highlightthickness=0)
        cx, cy = 10, 10
        for deg in range(0, 360, 45):
            import math
            rad = math.radians(deg)
            x = cx + 7 * math.cos(rad)
            y = cy + 7 * math.sin(rad)
            node.create_oval(x-2, y-2, x+2, y+2, fill=ACCENT, outline="")
        node.create_oval(6, 6, 14, 14, outline=ACCENT, width=1.5)
        node.pack(side=tk.LEFT, padx=(8, 6), pady=6)

        tk.Label(bar, text="MoE Routing Engine", bg=HEADER_BG, fg=ACCENT,
                 font=FONT_BOLD).pack(side=tk.LEFT, pady=4)

        self.active_expert_lbl = tk.Label(bar, text="", bg=HEADER_BG, fg=GREEN,
                                          font=("Segoe UI", 7, "bold"))
        self.active_expert_lbl.pack(side=tk.LEFT, padx=10, pady=5)

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

        # ── Router Status ──
        status_frame = tk.Frame(body, bg=CARD_BG, highlightthickness=1,
                                highlightbackground=BORDER)
        status_frame.pack(fill=tk.X, pady=(0, 8), ipady=4)

        inner = tk.Frame(status_frame, bg=CARD_BG)
        inner.pack(fill=tk.X, padx=10, pady=6)

        # Current request + top experts
        self.request_var = tk.StringVar(value="idle — no active request")
        tk.Label(inner, textvariable=self.request_var, bg=CARD_BG, fg=DIM,
                 font=("Segoe UI", 7)).pack(anchor=tk.W)

        self.top_experts_var = tk.StringVar(value="")
        tk.Label(inner, textvariable=self.top_experts_var, bg=CARD_BG, fg=TEXT,
                 font=FONT_BOLD).pack(anchor=tk.W, pady=(4, 0))

        self.routing_reason_var = tk.StringVar(value="")
        tk.Label(inner, textvariable=self.routing_reason_var, bg=CARD_BG, fg=DIM,
                 font=("Segoe UI", 7)).pack(anchor=tk.W, pady=(2, 0))

        # ── Expert Panel ──
        tk.Label(body, text="EXPERT PANEL", bg=BG, fg=ACCENT,
                 font=("Segoe UI", 8, "bold")).pack(anchor=tk.W, pady=(0, 4))

        col_frame = tk.Frame(body, bg=BG)
        col_frame.pack(fill=tk.X)

        tk.Label(col_frame, text="Expert", bg=BG, fg=DIM, font=("Segoe UI", 7, "bold"),
                 width=16, anchor=tk.W).pack(side=tk.LEFT)
        tk.Label(col_frame, text="Load", bg=BG, fg=DIM, font=("Segoe UI", 7, "bold"),
                 width=8, anchor=tk.CENTER).pack(side=tk.LEFT)
        tk.Label(col_frame, text="Latency", bg=BG, fg=DIM, font=("Segoe UI", 7, "bold"),
                 width=9, anchor=tk.CENTER).pack(side=tk.LEFT)
        tk.Label(col_frame, text="State", bg=BG, fg=DIM, font=("Segoe UI", 7, "bold"),
                 width=10, anchor=tk.CENTER).pack(side=tk.LEFT)

        tk.Frame(body, bg=BORDER, height=1).pack(fill=tk.X, pady=2)

        self.expert_frame = tk.Frame(body, bg=BG)
        self.expert_frame.pack(fill=tk.BOTH, expand=True)

        for expert in EXPERTS:
            self._build_expert_row(expert)

        # ── Routing Log ──
        tk.Label(body, text="ROUTING LOG", bg=BG, fg=PURPLE,
                 font=("Segoe UI", 8, "bold")).pack(anchor=tk.W, pady=(8, 4))

        self.log_box = tk.Text(body, bg=CARD_BG, fg=DIM, font=("Consolas", 8),
                               wrap=tk.WORD, height=4, bd=0, padx=8, pady=4,
                               state=tk.DISABLED, relief=tk.FLAT)
        self.log_box.pack(fill=tk.X, pady=(0, 4))

        self.footer = tk.Label(self, text="MoE Router active — simulating live routing",
                               bg=BG, fg=DIM, font=("Segoe UI", 7))
        self.footer.pack(pady=(0, 6))

    def _build_expert_row(self, expert):
        row = tk.Frame(self.expert_frame, bg=CARD_BG, height=32)
        row.pack(fill=tk.X, pady=1)
        row.pack_propagate(False)

        # Expert name
        tk.Label(row, text=expert["name"], bg=CARD_BG, fg=TEXT,
                 font=FONT_SM, width=16, anchor=tk.W).pack(side=tk.LEFT, padx=(6, 0))

        # Load bar
        load_frame = tk.Frame(row, bg=CARD_BG, width=80, height=18)
        load_frame.pack(side=tk.LEFT, padx=2)
        load_frame.pack_propagate(False)
        load_canvas = tk.Canvas(load_frame, width=80, height=18, bg=CARD_BG,
                                highlightthickness=0)
        load_canvas.pack()
        load_text = load_canvas.create_text(40, 9, text="0%", fill=DIM,
                                            font=("Segoe UI", 7, "bold"))

        # Latency
        lat_lbl = tk.Label(row, text=f"{expert['latency_ms']}ms", bg=CARD_BG, fg=DIM,
                           font=("Segoe UI", 7), width=9, anchor=tk.CENTER)
        lat_lbl.pack(side=tk.LEFT)

        # State
        state_lbl = tk.Label(row, text="IDLE", bg=CARD_BG, fg=DIM,
                             font=("Segoe UI", 7, "bold"), width=10, anchor=tk.CENTER)
        state_lbl.pack(side=tk.LEFT)

        self._expert_widgets[expert["id"]] = {
            "row": row, "load_canvas": load_canvas, "load_text": load_text,
            "lat_lbl": lat_lbl, "state_lbl": state_lbl, "expert": expert,
        }

    # ── Animation ──────────────────────────

    def _animate(self):
        """Simulate MoE routing decisions."""
        global TICK
        TICK += 1

        # Pick 2-3 top experts
        n_top = random.randint(2, 3)
        top_experts = random.sample(EXPERTS, k=n_top)

        # Simulate request types
        request_types = [
            "code_completion", "refactor_request", "architecture_review",
            "security_scan", "research_query", "data_analysis",
            "creative_brief", "deployment_check", "bug_fix",
            "doc_generation", "api_design", "performance_review",
        ]
        request = random.choice(request_types)
        confidence = random.randint(72, 98)

        # Assign loads
        for expert in EXPERTS:
            w = self._expert_widgets[expert["id"]]
            load = random.randint(5, 95)
            w["load_canvas"].delete("all")
            # Background
            w["load_canvas"].create_rectangle(0, 0, 80, 18, fill=CARD_BG, outline="")
            # Fill bar
            fill_w = int(80 * load / 100)
            color = GREEN if load < 50 else ACCENT if load < 75 else RED
            w["load_canvas"].create_rectangle(0, 0, fill_w, 18, fill=color, outline="")
            w["load_canvas"].itemconfigure(w["load_text"], text=f"{load}%",
                                           fill=TEXT if load > 40 else DIM)

            if expert in top_experts:
                w["state_lbl"].configure(text="ROUTED", fg=GREEN)
            else:
                w["state_lbl"].configure(text="IDLE", fg=DIM)

        # Update router status
        top_names = [e["name"] for e in top_experts]
        self.request_var.set(f"Active request: {request}")
        self.top_experts_var.set(f"Top {n_top} experts: {', '.join(top_names)}")
        self.active_expert_lbl.configure(text=f"● {top_names[0]}")
        self.routing_reason_var.set(
            f"Confidence: {confidence}% | Strategy: top-{n_top} gating | "
            f"Latency budget: {sum(e['latency_ms'] for e in top_experts)}ms combined"
        )

        # Add log entry
        ts = datetime.now().strftime("%H:%M:%S")
        log_entry = (f"[{ts}] ROUTE [{request}] → {', '.join(top_names)} "
                     f"({confidence}% conf) | tick={TICK}")
        ROUTE_LOG.append(log_entry)
        if len(ROUTE_LOG) > 30:
            ROUTE_LOG.pop(0)

        self.log_box.configure(state=tk.NORMAL)
        self.log_box.delete("1.0", tk.END)
        for line in ROUTE_LOG[-4:]:
            self.log_box.insert(tk.END, line + "\n")
        self.log_box.configure(state=tk.DISABLED)
        self.log_box.see(tk.END)

        self.footer.configure(text=f"MoE Router — {TICK} routes processed | "
                                   f"active experts: {n_top}/{len(EXPERTS)} | {ts}")

        self.after(random.randint(2500, 5000), self._animate)

    # ── Drag ──────────────────────────────

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event):
        self.geometry(f"+{self.winfo_x() + event.x - self._drag_x}"
                      f"+{self.winfo_y() + event.y - self._drag_y}")


if __name__ == "__main__":
    app = MoERoutingDisplay()
    app.mainloop()
