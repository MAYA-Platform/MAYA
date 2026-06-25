#!/usr/bin/env python3
"""MAYA Multi-Router v1 — Desktop App
Frameless tkinter desktop app for model switching and task routing.
MAYA dark theme with gold accents. All buttons work.

Features:
- Switch Hermes primary model with one click
- Classify and route tasks to optimal provider lane
- Visual lane indicators with status bars
- Compact frameless window, always on top
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import ttk
except Exception:
    tk = None
    ttk = None

try:
    import yaml
except Exception:
    yaml = None

# ═══════════════════════════════════════
# MAYA Design System Colors (Nova-standard)
# ═══════════════════════════════════════
BG_DEEP = "#1a1a2e"
BG_CARD = "#16213e"
BG_HEADER = "#0f0f23"
TEXT = "#e0e0e0"
TEXT_DIM = "#888888"
ACCENT = "#e6a817"       # MAYA gold
GREEN = "#2d4a2d"
BLUE = "#2d3d5a"
RUST = "#8b3a1a"
RED = "#4d1a1a"
DARK_ORANGE = "#4d2814"
BORDER = "#2a2a4a"
FONT = ("Segoe UI", 9)
FONT_SM = ("Segoe UI", 8)
FONT_BOLD = ("Segoe UI", 9, "bold")
FONT_H1 = ("Segoe UI", 13, "bold")

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / "AppData" / "Local" / "hermes"))
HERMES_CLI = "hermes"

# ═══════════════════════════════════════
# Model Presets
# ═══════════════════════════════════════
LLM_PRESETS = {
    "DeepSeek V4 Pro": {
        "desc": "Fast, cheap. Best for raw code, bulk work.",
        "provider": "deepseek",
        "model": "deepseek-v4-pro",
    },
    "OpenAI GPT-5.5": {
        "desc": "Complex reasoning, architecture, final judgment.",
        "provider": "openai-codex",
        "model": "gpt-5.5",
    },
    "OpenAI GPT-4o": {
        "desc": "Reliable fallback. Good for general tasks.",
        "provider": "openai",
        "model": "gpt-4o",
    },
    "Gemini 2.5 Flash": {
        "desc": "Free tier. 1M context. Solid research fallback.",
        "provider": "gemini",
        "model": "gemini-2.5-flash",
    },
    "Ollama Local": {
        "desc": "Fully offline. Private. Draft/summarize only.",
        "provider": "local-ollama",
        "model": "llama3.2:3b",
    },
}

VISION_PRESETS = {
    "Gemini 2.5 Flash": {
        "desc": "Free, working, reliable vision.",
        "provider": "google",
        "model": "gemini-2.5-flash",
    },
    "Groq Llama 4 Scout": {
        "desc": "Fastest free vision. Needs GROQ_API_KEY.",
        "provider": "groq",
        "model": "llama-4-scout-17b-16e-instruct",
    },
    "OpenAI GPT-4o": {
        "desc": "Paid. Reliable. Great quality.",
        "provider": "openai",
        "model": "gpt-4o",
    },
}

# ═══════════════════════════════════════
# Task Classifier (from maya_model_router.py)
# ═══════════════════════════════════════
ARCH_WORDS = {"architecture", "architect", "arc", "ace", "adaptive context", "context engine", "model routing", "router", "permission layer"}
RESEARCH_WORDS = {"research", "lookup", "docs", "documentation", "compare", "market", "current", "summarize document", "long context"}
CODE_WORDS = {"code", "fix", "build", "implement", "refactor", "typescript", "python", "bug", "repo", "component", "route"}
QA_WORDS = {"qa", "regression", "test", "console error", "broken import", "smoke", "verify", "acceptance"}
SECURITY_WORDS = {"security", "permission", "audit", "auth", "credential", "secret", "token", "billing", "production", "system-control"}
DANGEROUS_WORDS = {"delete", "remove files", "rm -rf", "wipe", "deploy", "production", "send message", "post externally", "billing", "credentials", "auth token", "install dependency", "desktop settings", "system settings"}
LARGE_CONTEXT_WORDS = {"large repo", "entire repo", "many files", "multi-file", "long document", "big markdown", "session dump", "archive"}
LOCAL_PRIVATE_WORDS = {"local", "ollama", "offline", "private", "privacy", "cheap", "low cost", "no cloud", "summarize", "summary", "draft", "brainstorm", "classify"}

LANE_COLORS = {
    "openai_controller": "#4a90d9",
    "deepseek_worker": "#52d273",
    "gemini_research": "#e6a817",
    "local_private": "#8b3a1a",
}

LANE_LABELS = {
    "openai_controller": "OpenAI Controller",
    "deepseek_worker": "DeepSeek Worker",
    "gemini_research": "Gemini Research",
    "local_private": "Ollama Local",
}


def contains_any(text: str, words: set[str]) -> bool:
    low = text.lower()
    for w in words:
        if len(w) <= 3 and w.isalpha():
            if re.search(rf"\b{re.escape(w)}\b", low):
                return True
        elif w in low:
            return True
    return False


def classify_task(task: str) -> dict:
    low = task.lower()
    notes = []

    if contains_any(low, DANGEROUS_WORDS):
        risk = "dangerous"
    elif contains_any(low, SECURITY_WORDS):
        risk = "high"
    elif contains_any(low, ARCH_WORDS) or "multi-file" in low or "large repo" in low:
        risk = "medium"
    else:
        risk = "low"

    if contains_any(low, SECURITY_WORDS):
        task_type = "security"
    elif contains_any(low, ARCH_WORDS):
        task_type = "architecture"
    elif contains_any(low, RESEARCH_WORDS):
        task_type = "research"
    elif contains_any(low, QA_WORDS):
        task_type = "QA"
    elif contains_any(low, CODE_WORDS):
        task_type = "coding"
    else:
        task_type = "general"

    if contains_any(low, LARGE_CONTEXT_WORDS) or len(task) > 4000:
        context_size = "large"
    elif len(task) > 1200:
        context_size = "medium"
    else:
        context_size = "small"

    if context_size == "large" or "multi-file" in low or "architecture" in low or "refactor" in low:
        complexity = "complex"
    elif "implement" in low or "build" in low or "debug" in low or "research" in low:
        complexity = "moderate"
    else:
        complexity = "simple"

    return {
        "task_type": task_type,
        "risk": risk,
        "complexity": complexity,
        "context_size": context_size,
        "notes": notes,
    }


def choose_lane(classification: dict) -> str:
    task_type = classification["task_type"]
    risk = classification["risk"]

    if risk in {"dangerous", "high"} or task_type == "security":
        return "openai_controller"
    if task_type == "architecture":
        return "openai_controller"
    if task_type == "research":
        return "gemini_research"
    if task_type in {"coding", "QA"} and risk == "low":
        return "deepseek_worker"
    return "openai_controller"


def run_hermes(args: list[str]) -> tuple[bool, str]:
    """Run a hermes CLI command. Returns (success, output)."""
    try:
        result = subprocess.run(
            [HERMES_CLI] + args,
            cwd=str(HERMES_HOME),
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            return True, result.stdout.strip() or "OK"
        return False, result.stderr.strip() or f"Exit code {result.returncode}"
    except FileNotFoundError:
        return False, "Hermes CLI not found"
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


class MayaMultiRouter(tk.Tk):
    """MAYA Multi-Router — frameless desktop app for model switching & task routing."""

    def __init__(self):
        super().__init__()
        self.title("MAYA Multi-Router")
        self.configure(bg=BG_DEEP)
        self.resizable(True, True)
        self.minsize(460, 520)

        # Frameless with custom title bar
        self.overrideredirect(True)
        self.geometry("480x580+200+100")
        self.attributes("-topmost", True)

        self._build_title_bar()
        self._build_notebook()

        self.after(100, self._center_window)

    def _center_window(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"+{x}+{y}")

    def _build_title_bar(self):
        bar = tk.Frame(self, bg=BG_HEADER, height=30)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)

        orb = tk.Canvas(bar, width=18, height=18, bg=BG_HEADER, highlightthickness=0)
        orb.create_oval(3, 3, 15, 15, outline=ACCENT, width=2)
        orb.create_arc(3, 3, 15, 15, start=90, extent=-240, outline=ACCENT, width=2, style="arc")
        orb.pack(side=tk.LEFT, padx=(8, 4), pady=6)

        tk.Label(bar, text="MAYA Multi-Router", bg=BG_HEADER, fg=ACCENT,
                 font=FONT_BOLD).pack(side=tk.LEFT, pady=4)

        # Min/Max/Close buttons
        for label, cmd, hover_bg in [
            ("—", lambda: self.iconify(), "#333344"),
            ("□", self._toggle_maximize, "#333344"),
            ("✕", self.destroy, "#661111"),
        ]:
            btn = tk.Button(bar, text=label, bg=BG_HEADER, fg=TEXT,
                            font=("Segoe UI", 10), relief=tk.FLAT,
                            command=cmd, activebackground=hover_bg,
                            activeforeground="#ffffff", bd=0, padx=8)
            btn.pack(side=tk.RIGHT, pady=2)

        # Drag bindings
        for widget in [bar] + list(bar.winfo_children()):
            widget.bind("<Button-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._on_drag)

    def _build_notebook(self):
        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))

        style = ttk.Style()
        style.theme_use("default")
        style.configure("TNotebook", background=BG_DEEP, borderwidth=0)
        style.configure("TNotebook.Tab", background=BG_CARD, foreground=TEXT,
                        padding=[12, 4], font=FONT_SM, borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", BG_HEADER)],
                  foreground=[("selected", ACCENT)])

        # Tab 1: Model Switch
        switch_frame = tk.Frame(nb, bg=BG_DEEP)
        nb.add(switch_frame, text="  Model Switch  ")
        self._build_switch_tab(switch_frame)

        # Tab 2: Task Router
        router_frame = tk.Frame(nb, bg=BG_DEEP)
        nb.add(router_frame, text="  Task Router  ")
        self._build_router_tab(router_frame)

    # ── MODEL SWITCH TAB ────────────────────
    def _build_switch_tab(self, parent):
        # Status
        self.switch_status = tk.StringVar(value="Ready — select a model to switch")
        st = tk.Label(parent, textvariable=self.switch_status, bg=BG_DEEP, fg=TEXT_DIM,
                      font=FONT_SM)
        st.pack(pady=(10, 4))

        # LLM Section
        tk.Label(parent, text="PRIMARY LLM", bg=BG_DEEP, fg=ACCENT,
                 font=FONT_BOLD).pack(pady=(8, 2))

        llm_frame = tk.Frame(parent, bg=BG_DEEP)
        llm_frame.pack(fill=tk.X, padx=8, pady=2)

        for label, preset in LLM_PRESETS.items():
            self._make_switch_card(llm_frame, label, preset, "llm")

        # Vision Section
        tk.Label(parent, text="VISION PROVIDER", bg=BG_DEEP, fg=ACCENT,
                 font=FONT_BOLD).pack(pady=(12, 2))

        vis_frame = tk.Frame(parent, bg=BG_DEEP)
        vis_frame.pack(fill=tk.X, padx=8, pady=2)

        for label, preset in VISION_PRESETS.items():
            self._make_switch_card(vis_frame, label, preset, "vision")

        # Note
        tk.Label(parent, text="⚠ After switching: type /reset in Hermes to apply",
                 bg=BG_DEEP, fg=TEXT_DIM, font=FONT_SM).pack(pady=(8, 4))

    def _make_switch_card(self, parent, label, preset, mode):
        card = tk.Frame(parent, bg=BG_CARD, bd=0,
                        highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill=tk.X, pady=1)

        info = tk.Frame(card, bg=BG_CARD)
        info.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8, pady=5)

        tk.Label(info, text=label, bg=BG_CARD, fg=TEXT,
                 font=FONT_BOLD).pack(anchor=tk.W)
        tk.Label(info, text=preset["desc"], bg=BG_CARD, fg=TEXT_DIM,
                 font=FONT_SM, wraplength=280).pack(anchor=tk.W)

        btn_color = BLUE if mode == "llm" else RUST
        btn = tk.Button(card, text="SWITCH", bg=btn_color, fg=TEXT,
                        font=("Segoe UI", 8, "bold"), relief=tk.FLAT,
                        activebackground=GREEN, activeforeground="#ffffff",
                        bd=0, padx=12, pady=6,
                        command=lambda l=label, p=preset, m=mode: self._do_switch(l, p, m))
        btn.pack(side=tk.RIGHT, padx=8, pady=6)

    def _do_switch(self, label, preset, mode):
        self.switch_status.set(f"Switching to {label}...")
        self.update()

        if mode == "llm":
            cmds = [
                ["config", "set", "model.provider", preset["provider"]],
                ["config", "set", "model.model", preset["model"]],
            ]
        else:
            cmds = [
                ["config", "set", "auxiliary.vision.provider", preset["provider"]],
                ["config", "set", "auxiliary.vision.model", preset["model"]],
            ]

        all_ok = True
        for cmd in cmds:
            ok, out = run_hermes(cmd)
            if not ok:
                all_ok = False
                self.switch_status.set(f"❌ Failed: {out[:80]}")
                break

        if all_ok:
            self.switch_status.set(f"✅ Switched to {label} — /reset to apply")
            self.after(4000, lambda: self.switch_status.set("Ready — select a model to switch"))

    # ── TASK ROUTER TAB ────────────────────
    def _build_router_tab(self, parent):
        # Input
        tk.Label(parent, text="Enter task description:", bg=BG_DEEP, fg=TEXT,
                 font=FONT_SM).pack(anchor=tk.W, padx=8, pady=(8, 2))

        input_frame = tk.Frame(parent, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
        input_frame.pack(fill=tk.X, padx=8, pady=2)

        self.task_input = tk.Text(input_frame, bg=BG_CARD, fg=TEXT, font=FONT,
                                  wrap=tk.WORD, height=4, bd=0, padx=8, pady=6,
                                  insertbackground=ACCENT, relief=tk.FLAT)
        self.task_input.pack(fill=tk.X)
        self.task_input.insert("1.0", "Enter a task to classify and route...")

        # Action buttons
        btn_frame = tk.Frame(parent, bg=BG_DEEP)
        btn_frame.pack(fill=tk.X, padx=8, pady=4)

        tk.Button(btn_frame, text="CLASSIFY & ROUTE", bg=BLUE, fg=TEXT,
                  font=("Segoe UI", 8, "bold"), relief=tk.FLAT,
                  activebackground="#3d5d8a", activeforeground="#ffffff",
                  bd=0, padx=12, pady=6,
                  command=self._classify_route).pack(side=tk.LEFT, padx=2)

        tk.Button(btn_frame, text="CLEAR", bg=RUST, fg=TEXT,
                  font=("Segoe UI", 8, "bold"), relief=tk.FLAT,
                  activebackground="#9b4a2a", activeforeground="#ffffff",
                  bd=0, padx=12, pady=6,
                  command=self._clear_route).pack(side=tk.LEFT, padx=2)

        # Results area
        self.route_result = tk.Frame(parent, bg=BG_DEEP)
        self.route_result.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # Classification
        cframe = tk.LabelFrame(self.route_result, text="Classification", bg=BG_DEEP, fg=TEXT,
                               font=FONT_SM, bd=0, padx=8, pady=4)
        cframe.pack(fill=tk.X, pady=2)

        self.class_vars = {}
        for key in ["task_type", "risk", "complexity", "context_size"]:
            row = tk.Frame(cframe, bg=BG_DEEP)
            row.pack(fill=tk.X)
            tk.Label(row, text=f"{key.replace('_', ' ').title()}:", bg=BG_DEEP, fg=TEXT_DIM,
                     font=FONT_SM, width=12, anchor=tk.W).pack(side=tk.LEFT)
            var = tk.StringVar(value="—")
            self.class_vars[key] = var
            tk.Label(row, textvariable=var, bg=BG_DEEP, fg=TEXT,
                     font=FONT_BOLD).pack(side=tk.LEFT)

        # Route decision
        rframe = tk.LabelFrame(self.route_result, text="Route Decision", bg=BG_DEEP, fg=TEXT,
                               font=FONT_SM, bd=0, padx=8, pady=4)
        rframe.pack(fill=tk.X, pady=2)

        self.route_vars = {}
        for key in ["lane", "provider", "model", "reason"]:
            row = tk.Frame(rframe, bg=BG_DEEP)
            row.pack(fill=tk.X)
            tk.Label(row, text=f"{key.title()}:", bg=BG_DEEP, fg=TEXT_DIM,
                     font=FONT_SM, width=12, anchor=tk.W).pack(side=tk.LEFT)
            var = tk.StringVar(value="—")
            self.route_vars[key] = var
            tk.Label(row, textvariable=var, bg=BG_DEEP, fg=TEXT,
                     font=FONT_BOLD, wraplength=300).pack(side=tk.LEFT)

        # Lane visual indicator
        self.lane_canvas = tk.Canvas(self.route_result, width=440, height=28,
                                     bg=BG_DEEP, highlightthickness=0)
        self.lane_canvas.pack(fill=tk.X, pady=4)
        self._draw_lane_indicator(None)

        # Execute button
        tk.Button(self.route_result, text="EXECUTE (via Hermes CLI)", bg=GREEN, fg=TEXT,
                  font=("Segoe UI", 8, "bold"), relief=tk.FLAT,
                  activebackground="#3d6a3d", activeforeground="#ffffff",
                  bd=0, padx=12, pady=6,
                  command=self._execute_route).pack(pady=4)

        # Output
        self.exec_output = tk.Text(self.route_result, bg=BG_CARD, fg=TEXT_DIM,
                                   font=("Consolas", 8), wrap=tk.WORD, height=6,
                                   bd=0, padx=8, pady=6, relief=tk.FLAT, state=tk.DISABLED)
        self.exec_output.pack(fill=tk.BOTH, expand=True)

    def _classify_route(self):
        task = self.task_input.get("1.0", "end-1c").strip()
        if not task or task == "Enter a task to classify and route...":
            self.class_vars["task_type"].set("No input")
            return

        classification = classify_task(task)
        lane = choose_lane(classification)

        self.class_vars["task_type"].set(classification["task_type"])
        self.class_vars["risk"].set(classification["risk"])
        self.class_vars["complexity"].set(classification["complexity"])
        self.class_vars["context_size"].set(classification["context_size"])

        self.route_vars["lane"].set(LANE_LABELS.get(lane, lane))
        self.route_vars["provider"].set(lane)
        self.route_vars["model"].set(self._get_model_for_lane(lane))
        self.route_vars["reason"].set(self._get_reason(classification, lane))

        self._draw_lane_indicator(lane)
        self._last_lane = lane

    def _get_model_for_lane(self, lane: str) -> str:
        mapping = {
            "openai_controller": "gpt-5.5",
            "deepseek_worker": "deepseek-v4-pro",
            "gemini_research": "gemini-2.5-flash",
            "local_private": "llama3.2:3b",
        }
        return mapping.get(lane, "unknown")

    def _get_reason(self, cl, lane: str) -> str:
        reasons = {
            "openai_controller": f"Controller lane — {cl['risk']} risk, {cl['task_type']} task needs final authority",
            "deepseek_worker": f"Worker lane — cost-effective for {cl['task_type']} at {cl['risk']} risk",
            "gemini_research": f"Research lane — optimized for {cl['task_type']} with large context",
            "local_private": f"Local lane — fully offline, private {cl['task_type']}",
        }
        return reasons.get(lane, "No specific reason")

    def _draw_lane_indicator(self, lane):
        c = self.lane_canvas
        c.delete("all")
        width = c.winfo_width() or 440

        colors = ["#2a2a4a", "#2a2a4a", "#2a2a4a", "#2a2a4a"]
        labels = ["Controller", "DeepSeek", "Gemini", "Local"]

        if lane == "openai_controller":
            colors[0] = "#4a90d9"
        elif lane == "deepseek_worker":
            colors[1] = "#52d273"
        elif lane == "gemini_research":
            colors[2] = ACCENT
        elif lane == "local_private":
            colors[3] = "#8b3a1a"

        seg_w = width // 4
        for i, (color, label) in enumerate(zip(colors, labels)):
            x1 = i * seg_w + 4
            x2 = x1 + seg_w - 8
            c.create_rectangle(x1, 4, x2, 24, fill=color, outline="", tags=f"seg{i}")
            if color != "#2a2a4a":
                c.create_text((x1 + x2) // 2, 14, text=label, fill="#ffffff",
                              font=("Segoe UI", 7, "bold"))

    def _execute_route(self):
        if not hasattr(self, "_last_lane"):
            return
        lane = self._last_lane
        task = self.task_input.get("1.0", "end-1c").strip()

        self._set_exec_output("Executing...\n", TEXT)
        threading.Thread(target=self._execute_worker, args=(lane, task), daemon=True).start()

    def _execute_worker(self, lane, task):
        provider_map = {
            "openai_controller": "openai-codex",
            "deepseek_worker": "deepseek",
            "gemini_research": "gemini",
            "local_private": "local-ollama",
        }
        model_map = {
            "openai_controller": "gpt-5.5",
            "deepseek_worker": "deepseek-v4-pro",
            "gemini_research": "gemini-2.5-flash",
            "local_private": "llama3.2:3b",
        }

        provider = provider_map.get(lane, "openai-codex")
        model = model_map.get(lane, "gpt-5.5")

        if lane == "local_private":
            # Try Ollama directly
            try:
                payload = json.dumps({
                    "model": model,
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": "You are Hermes Local Lite. Be concise and useful."},
                        {"role": "user", "content": task},
                    ],
                    "options": {"temperature": 0.25},
                }).encode("utf-8")
                req = urllib.request.Request(
                    "http://127.0.0.1:11434/api/chat",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=120) as resp:
                    body = json.loads(resp.read().decode())
                text = ((body.get("message") or {}).get("content") or "No response")
                self.after(0, lambda: self._set_exec_output(text, TEXT))
            except Exception as e:
                self.after(0, lambda: self._set_exec_output(f"Ollama error: {e}", TEXT_DIM))
        else:
            # Use hermes CLI
            prompt = f"You are a MAYA worker lane.\nRoute: {lane}\nBe concise.\n\nTask:\n{task}"
            ok, out = run_hermes([
                "chat", "--provider", provider, "-m", model,
                "-t", "safe", "-q", prompt, "-Q",
            ])
            if ok:
                self.after(0, lambda: self._set_exec_output(out, TEXT))
            else:
                self.after(0, lambda: self._set_exec_output(f"Error: {out}", TEXT_DIM))

    def _set_exec_output(self, text, color):
        self.exec_output.configure(state=tk.NORMAL)
        self.exec_output.delete("1.0", tk.END)
        self.exec_output.insert("1.0", text)
        self.exec_output.configure(fg=color, state=tk.DISABLED)

    def _clear_route(self):
        self.task_input.delete("1.0", tk.END)
        for var in self.class_vars.values():
            var.set("—")
        for var in self.route_vars.values():
            var.set("—")
        self._draw_lane_indicator(None)
        self._set_exec_output("", TEXT_DIM)
        if hasattr(self, "_last_lane"):
            del self._last_lane

    # ── Window Management ──────────────────
    def _start_drag(self, event):
        self._dx = event.x
        self._dy = event.y

    def _on_drag(self, event):
        x = self.winfo_x() + event.x - self._dx
        y = self.winfo_y() + event.y - self._dy
        self.geometry(f"+{x}+{y}")

    def _toggle_maximize(self):
        if self.state() == "normal":
            self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        else:
            self.geometry("480x580+200+100")


def main():
    parser = argparse.ArgumentParser(description="MAYA Multi-Router Desktop App")
    parser.add_argument("--once", action="store_true", help="CLI mode: classify and exit")
    parser.add_argument("--task", help="Task to classify (with --once)")
    args = parser.parse_args()

    if args.once:
        if not args.task:
            print("Usage: maya_multi_router.py --once --task 'your task'")
            return 1
        cl = classify_task(args.task)
        lane = choose_lane(cl)
        print(json.dumps({
            "task": args.task,
            "classification": cl,
            "lane": lane,
            "label": LANE_LABELS.get(lane, lane),
        }, indent=2))
        return 0

    app = MayaMultiRouter()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
