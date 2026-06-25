#!/usr/bin/env python3
"""MAYA Provider Switch — legacy one-click backup provider activation.

Deprecated for normal use: MAYA Multi-Router is now the primary provider/model
control surface. Keep this app as a compatibility fallback until Multi-Router
has absorbed all presets and Josh explicitly approves retirement.
"""
from __future__ import annotations

import subprocess
import sys
import tkinter as tk
from pathlib import Path

HERMES_HOME = Path.home() / "AppData" / "Local" / "hermes"
HERMES_CLI = "hermes"

# ═══════════════════════════════════════
# Provider presets — label → config commands
# ═══════════════════════════════════════
LLM_PRESETS = {
    "DeepSeek V4 Pro": {
        "desc": "Fast, cheap. Best for raw code, bulk work.",
        "commands": [
            ["config", "set", "model.provider", "deepseek"],
            ["config", "set", "model.model", "deepseek-v4-pro"],
        ],
    },
    "OpenAI GPT-4o": {
        "desc": "Complex reasoning, architecture, final judgment.",
        "commands": [
            ["config", "set", "model.provider", "openai"],
            ["config", "set", "model.model", "gpt-4o"],
        ],
    },
    "OpenAI GPT-5.4 Nano": {
        "desc": "Newest reasoning model. Slower but smarter.",
        "commands": [
            ["config", "set", "model.provider", "openai"],
            ["config", "set", "model.model", "gpt-5.4-nano"],
        ],
    },
    "Gemini 2.5 Flash": {
        "desc": "Free tier. 1M context. Solid fallback.",
        "commands": [
            ["config", "set", "model.provider", "google"],
            ["config", "set", "model.model", "gemini-2.5-flash"],
        ],
    },
}

VISION_PRESETS = {
    "Gemini 2.5 Flash": {
        "desc": "Free, working, reliable.",
        "commands": [
            ["config", "set", "auxiliary.vision.provider", "google"],
            ["config", "set", "auxiliary.vision.model", "gemini-2.5-flash"],
        ],
    },
    "Groq Llama 4 Scout": {
        "desc": "Fastest free vision. Needs active GROQ_API_KEY.",
        "commands": [
            ["config", "set", "auxiliary.vision.provider", "groq"],
            ["config", "set", "auxiliary.vision.model", "llama-4-scout-17b-16e-instruct"],
        ],
    },
    "OpenAI GPT-4o": {
        "desc": "Paid. Reliable. Great quality.",
        "commands": [
            ["config", "set", "auxiliary.vision.provider", "openai"],
            ["config", "set", "auxiliary.vision.model", "gpt-4o"],
        ],
    },
}

# ═══════════════════════════════════════
# Colors
# ═══════════════════════════════════════
BG = "#12100f"
CARD_BG = "#1a1816"
GREEN = "#2d4a2d"
BLUE = "#2d3d5a"
RUST = "#8b3a1a"
TEXT = "#f2e6df"
ACCENT = "#ff7a39"
DIM = "#7d736b"
HEADER_BG = "#1a1816"


def run_hermes(args: list[str]) -> bool:
    """Run a hermes config command. Returns True on success."""
    try:
        result = subprocess.run(
            [HERMES_CLI] + args,
            cwd=str(HERMES_HOME),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


class ProviderSwitch(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MAYA Provider Switch")
        self.configure(bg=BG)
        self.resizable(False, False)

        # Frameless with custom title bar
        self.overrideredirect(True)
        self.geometry("420x560+100+100")

        # Title bar
        title_bar = tk.Frame(self, bg=HEADER_BG, height=32)
        title_bar.pack(fill=tk.X)
        title_bar.pack_propagate(False)

        tk.Label(title_bar, text="  ◉  MAYA Provider Switch", bg=HEADER_BG, fg=ACCENT,
                 font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, pady=4)
        tk.Button(title_bar, text="✕", bg=HEADER_BG, fg=TEXT, font=("Segoe UI", 10),
                  relief=tk.FLAT, command=self.destroy, activebackground="#4d1a1a",
                  activeforeground="#ffffff", bd=0, padx=10).pack(side=tk.RIGHT, pady=2)
        tk.Button(title_bar, text="—", bg=HEADER_BG, fg=TEXT, font=("Segoe UI", 10),
                  relief=tk.FLAT, command=self.iconify, activebackground="#333344",
                  bd=0, padx=8).pack(side=tk.RIGHT, pady=2)

        # Make draggable
        title_bar.bind("<Button-1>", self.start_drag)
        title_bar.bind("<B1-Motion>", self.on_drag)
        for child in title_bar.winfo_children():
            child.bind("<Button-1>", self.start_drag)
            child.bind("<B1-Motion>", self.on_drag)

        # Status
        self.status_var = tk.StringVar(value="Ready")
        status = tk.Label(self, textvariable=self.status_var, bg=BG, fg=DIM,
                          font=("Segoe UI", 8))
        status.pack(pady=(8, 4))

        # LLM Section
        tk.Label(self, text="PRIMARY LLM", bg=BG, fg=ACCENT,
                 font=("Segoe UI", 9, "bold")).pack(pady=(8, 2))
        tk.Label(self, text="Switch main model — one click, then /reset in Hermes",
                 bg=BG, fg=DIM, font=("Segoe UI", 7)).pack()

        cards_frame = tk.Frame(self, bg=BG)
        cards_frame.pack(fill=tk.X, padx=12, pady=4)

        for label, preset in LLM_PRESETS.items():
            self._make_card(cards_frame, label, preset)

        # Vision Section
        tk.Label(self, text="VISION PROVIDER", bg=BG, fg=ACCENT,
                 font=("Segoe UI", 9, "bold")).pack(pady=(12, 2))
        tk.Label(self, text="Switch image analysis backend",
                 bg=BG, fg=DIM, font=("Segoe UI", 7)).pack()

        vision_frame = tk.Frame(self, bg=BG)
        vision_frame.pack(fill=tk.X, padx=12, pady=4)

        for label, preset in VISION_PRESETS.items():
            self._make_card(vision_frame, label, preset)

        # Note
        tk.Label(self, text="⚠  After switching: type /reset in Hermes to apply",
                 bg=BG, fg=DIM, font=("Segoe UI", 7)).pack(pady=(10, 4))

    def _make_card(self, parent, label, preset):
        card = tk.Frame(parent, bg=CARD_BG, bd=0, highlightthickness=1,
                        highlightbackground="#2a2a4a")
        card.pack(fill=tk.X, pady=2)

        info = tk.Frame(card, bg=CARD_BG)
        info.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8, pady=6)

        tk.Label(info, text=label, bg=CARD_BG, fg=TEXT,
                 font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
        tk.Label(info, text=preset["desc"], bg=CARD_BG, fg=DIM,
                 font=("Segoe UI", 7), wraplength=250).pack(anchor=tk.W)

        btn = tk.Button(card, text="ACTIVATE", bg=BLUE, fg=TEXT,
                        font=("Segoe UI", 8, "bold"), relief=tk.FLAT,
                        activebackground=GREEN, activeforeground="#ffffff",
                        bd=0, padx=10, pady=4,
                        command=lambda p=preset, l=label: self._activate(l, p))
        btn.pack(side=tk.RIGHT, padx=8, pady=4)

    def _activate(self, label, preset):
        self.status_var.set(f"Switching to {label}...")
        self.update()

        success = True
        for cmd in preset["commands"]:
            if not run_hermes(cmd):
                success = False
                break

        if success:
            self.status_var.set(f"✅ Switched to {label} — /reset to apply")
            # Flash the card green briefly
            self.after(3000, lambda: self.status_var.set("Ready"))
        else:
            self.status_var.set(f"❌ Failed — check Hermes is installed")

    def start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def on_drag(self, event):
        x = self.winfo_x() + event.x - self._drag_x
        y = self.winfo_y() + event.y - self._drag_y
        self.geometry(f"+{x}+{y}")


if __name__ == "__main__":
    app = ProviderSwitch()
    app.mainloop()
