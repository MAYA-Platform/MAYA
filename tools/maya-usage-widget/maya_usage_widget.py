#!/usr/bin/env python3
"""MAYA Usage Widget — Compact tkinter desktop widget.
Shows all provider usage, rate limits, DeepSeek balance,
MoE routing status, and CRL cache stats in one compact window.

MAYA dark theme. Frameless. Always on top.
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import threading
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import ttk
except Exception:
    tk = None
    ttk = None

APP_NAME = "MAYA Usage Widget"
APP_VERSION = "1.0.0"
APP_DIR = Path(__file__).resolve().parent
LOG_DIR = APP_DIR / "logs"
MAYA_BASE = os.environ.get("MAYA_BASE_URL", "http://127.0.0.1:8765")

# ═══════════════════════════════════════
# MAYA Design System Colors
# ═══════════════════════════════════════
BG = "#12100f"
CARD_BG = "#1a1816"
HEADER_BG = "#1a1816"
TEXT = "#f2e6df"
MUTED = "#a3968e"
DIM = "#7d736b"
ACCENT = "#ff7a39"
GREEN = "#35d46f"
RED = "#ff5f5f"
BORDER = "#3d2a1a"


def log(message: str) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with (LOG_DIR / "widget.log").open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] {message}\n")
    except Exception:
        pass


def maya_get(path: str, timeout: float = 8.0) -> dict:
    try:
        req = urllib.request.Request(f"{MAYA_BASE}{path}")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"ok": False, "error": str(e)}


def fetch_all_data() -> dict:
    data = {"deepseek": {}, "apis": [], "providers": [], "moe": {}, "crl": {}, "rate_limits": [], "status": {}}
    cr = maya_get("/api/maya-agent/codex-usage")
    if cr.get("ok"):
        data["deepseek"] = cr.get("deepseek") or {}
        data["apis"] = cr.get("apis") or []
        data["rate_limits"] = cr.get("rateLimits") or []
        data["usage_error"] = cr.get("error") or ""
    ph = maya_get("/api/maya-agent/provider-health")
    if ph.get("ok"):
        data["providers"] = ph.get("providers") or []
        data["provider_health"] = ph
    status = maya_get("/api/maya-agent/status")
    if status.get("ok"):
        data["status"] = status
    moe = maya_get("/api/maya-agent/moe-gating")
    if moe.get("ok"):
        data["moe"] = moe or {}
    crl = maya_get("/api/maya-agent/crl-stats")
    if crl.get("ok"):
        data["crl"] = crl or {}
    return data


class MayaUsageWidget:
    def __init__(self):
        if tk is None:
            raise RuntimeError("tkinter is not available")
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        try:
            self.root.overrideredirect(True)
        except Exception:
            pass

        self._refreshing = False
        self._bars = {}
        self._bar_values = {}
        self._labels = {}

        self._build_ui()
        self._position_default()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(200, self.refresh)
        self.root.after(1000, self._tick_clock)

    def _position_default(self):
        self.root.update_idletasks()
        w, h = 310, 520
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = sw - w - 28
        y = 72
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _bind_draggable(self, widget):
        widget.bind("<ButtonPress-1>", self._start_drag)
        widget.bind("<B1-Motion>", self._on_drag)

    def _build_ui(self):
        # Outer border
        outer = tk.Frame(self.root, bg=BORDER, bd=0)
        outer.pack(fill="both", expand=True, padx=1, pady=1)
        card = tk.Frame(outer, bg=BG, bd=0)
        card.pack(fill="both", expand=True, padx=1, pady=1)

        # Title bar
        header = tk.Frame(card, bg=HEADER_BG, height=30)
        header.pack(fill="x")
        header.pack_propagate(False)
        self._bind_draggable(header)

        orb = tk.Canvas(header, width=18, height=18, bg=HEADER_BG, highlightthickness=0)
        orb.create_oval(3, 3, 15, 15, outline=ACCENT, width=2)
        orb.create_arc(3, 3, 15, 15, start=90, extent=-240, outline=ACCENT, width=2, style="arc")
        orb.pack(side="left", padx=(8, 4), pady=6)

        title = tk.Label(header, text="MAYA Usage", bg=HEADER_BG, fg=TEXT,
                         font=("Segoe UI", 10, "bold"))
        title.pack(side="left")

        self._labels["status"] = tk.Label(header, text="", bg=HEADER_BG, fg=DIM,
                                           font=("Segoe UI", 8))
        self._labels["status"].pack(side="left", padx=(8, 0))

        close_btn = tk.Button(header, text="✕", command=self.close,
                              bg=HEADER_BG, fg=MUTED, activebackground="#4d1a1a",
                              activeforeground="#ffffff", borderwidth=0,
                              font=("Segoe UI", 11), padx=6, pady=0, cursor="hand2")
        close_btn.pack(side="right", pady=2)

        refresh_btn = tk.Button(header, text="↻", command=self.refresh,
                                bg=HEADER_BG, fg=MUTED, activebackground=CARD_BG,
                                activeforeground=TEXT, borderwidth=0,
                                font=("Segoe UI", 10), padx=6, pady=0, cursor="hand2")
        refresh_btn.pack(side="right", pady=2)

        # Body
        body = tk.Frame(card, bg=BG)
        body.pack(fill="x", padx=10, pady=(8, 0))

        rows = [
            ("controller", "Main"),
            ("deepseek", "DeepSeek"),
            ("codex_5h", "Codex 5h"),
            ("codex_week", "Codex Weekly"),
            ("gemini", "Gemini"),
            ("ollama", "Ollama"),
            ("moe", "MoE Router"),
            ("crl", "CRL Cache"),
        ]
        for i, (key, label) in enumerate(rows):
            self._make_row(body, key, label, i)

        # Footer
        footer = tk.Frame(card, bg=CARD_BG)
        footer.pack(fill="x", padx=1, pady=(8, 1), side="bottom")
        self._labels["footer"] = tk.Label(
            footer, text="Connecting to MAYA server…", bg=CARD_BG, fg=MUTED,
            anchor="w", font=("Segoe UI", 7), padx=8, pady=5
        )
        self._labels["footer"].pack(fill="x")

    def _make_row(self, parent, key, label, row):
        frame = tk.Frame(parent, bg=BG)
        frame.grid(row=row, column=0, sticky="ew", pady=3)
        parent.grid_columnconfigure(0, weight=1)

        self._labels[f"{key}_label"] = tk.Label(
            frame, text=label, bg=BG, fg=TEXT,
            font=("Segoe UI", 9, "bold"), width=10, anchor="w"
        )
        self._labels[f"{key}_label"].grid(row=0, column=0, sticky="w")

        self._labels[f"{key}_val"] = tk.Label(
            frame, text="—", bg=BG, fg=TEXT,
            font=("Segoe UI", 9), anchor="e", width=8
        )
        self._labels[f"{key}_val"].grid(row=0, column=1, sticky="e", padx=(0, 8))

        self._labels[f"{key}_extra"] = tk.Label(
            frame, text="", bg=BG, fg=DIM,
            font=("Segoe UI", 8), anchor="e", width=10
        )
        self._labels[f"{key}_extra"].grid(row=0, column=2, sticky="e")

        bar = tk.Canvas(frame, width=270, height=5, bg=BG, highlightthickness=0)
        bar.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(2, 0))
        self._bars[key] = bar
        self._bar_values[key] = 0
        self._draw_bar(key, 0)

    def _draw_bar(self, key, pct):
        bar = self._bars[key]
        bar.delete("all")
        w = max(1, bar.winfo_width() or 270)
        h = 5
        bar.create_rectangle(0, 0, w, h, fill=CARD_BG, outline="")
        fill_w = int(w * max(0, min(100, pct)) / 100)
        color = GREEN if pct >= 50 else ACCENT if pct >= 20 else RED
        bar.create_rectangle(0, 0, fill_w, h, fill=color, outline="")

    def _start_drag(self, event):
        self._drag_x = event.x_root - self.root.winfo_x()
        self._drag_y = event.y_root - self.root.winfo_y()

    def _on_drag(self, event):
        self.root.geometry(f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}")

    def _tick_clock(self):
        for key, val in self._bar_values.items():
            self._draw_bar(key, val)
        self.root.after(5000, self._tick_clock)

    def refresh(self):
        if self._refreshing:
            return
        self._refreshing = True
        self._labels["status"].configure(text="⟳", fg=ACCENT)
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self):
        try:
            data = fetch_all_data()
            self.root.after(0, lambda: self._apply_data(data))
        except Exception as e:
            log(f"Refresh failed: {e}")
            self.root.after(0, lambda: self._apply_error(str(e)))
        finally:
            self.root.after(0, self._finish_refresh)

    def _finish_refresh(self):
        self._refreshing = False
        self.root.after(300000, self.refresh)  # every 5 min

    def _set_row(self, key, pct, val, extra, green=False, red=False):
        self._labels[f"{key}_val"].configure(text=val)
        self._labels[f"{key}_extra"].configure(
            text=extra,
            fg=GREEN if green else RED if red else DIM
        )
        self._bar_values[key] = pct
        self._draw_bar(key, pct)

    def _apply_data(self, data):
        self._labels["status"].configure(text="●", fg=GREEN)

        providers = data.get("providers", [])
        ph_map = {p.get("id", ""): p for p in providers if isinstance(p, dict)}

        # Main provider / controller lane
        status = data.get("status", {}) or {}
        bridge = status.get("hermesBridge", {}) if isinstance(status, dict) else {}
        cfg = bridge.get("config", {}) if isinstance(bridge, dict) else {}
        main_provider = cfg.get("provider") or "openai-codex"
        main_model = cfg.get("model") or "gpt-5.5"
        controller = ph_map.get(main_provider) or ph_map.get("openai-codex") or {}
        if controller.get("configured") or main_provider:
            self._set_row("controller", 100, str(main_model)[:8], str(main_provider)[:10], green=True)
        else:
            self._set_row("controller", 0, "—", "unknown", red=True)

        # DeepSeek
        ds = data.get("deepseek", {}) or {}
        ds_provider = ph_map.get("deepseek") or {}
        if ds.get("configured") and ds.get("balances"):
            bal = (ds.get("balances") or [{}])[0]
            amt = bal.get("total_balance", "?")
            self._set_row("deepseek", min(100, int(float(amt) * 10) if amt != "?" else 50),
                         f"${amt}", "balance", green=True)
        elif ds.get("configured") or ds_provider.get("configured"):
            self._set_row("deepseek", 100, "✓", "worker", green=True)
        else:
            self._set_row("deepseek", 0, "—", "offline", red=True)

        # Codex rate limits
        rl_list = data.get("rate_limits", [])
        codex_5h = next((r for r in rl_list if "5h" in str(r.get("windowDurationMins", ""))), None)
        codex_wk = next((r for r in rl_list if "week" in str(r.get("limitName", "")).lower()), None)
        if not codex_5h:
            for r in rl_list:
                dur = r.get("windowDurationMins", 0)
                if dur and dur < 1440:
                    codex_5h = r
                    break
        if not codex_wk:
            for r in rl_list:
                dur = r.get("windowDurationMins", 0)
                if dur and dur >= 1440:
                    codex_wk = r
                    break

        if codex_5h and isinstance(codex_5h, dict):
            rem = max(0, 100 - int(codex_5h.get("usedPercent", 0) or 0))
            self._set_row("codex_5h", rem, f"{rem}%", "5h limit")
        else:
            self._set_row("codex_5h", 0, "—", "no data")

        if codex_wk and isinstance(codex_wk, dict):
            rem = max(0, 100 - int(codex_wk.get("usedPercent", 0) or 0))
            self._set_row("codex_week", rem, f"{rem}%", "weekly")
        else:
            self._set_row("codex_week", 0, "—", "no data")

        # Providers
        gemini = ph_map.get("gemini")
        if gemini and gemini.get("configured"):
            self._set_row("gemini", 100, "✓", "healthy", green=True)
        else:
            self._set_row("gemini", 0, "—", "not configured")

        ollama = ph_map.get("ollama")
        if ollama and ollama.get("configured"):
            self._set_row("ollama", 100, "✓", "healthy", green=True)
        else:
            self._set_row("ollama", 0, "—", "not configured")

        # MoE
        moe = data.get("moe", {})
        if moe.get("activeExpert"):
            short = moe["activeExpert"][:12]
            conf = round(moe.get("confidence", 0))
            self._set_row("moe", conf, short, f"{conf}% conf")
        else:
            self._set_row("moe", 0, "—", "offline")

        # CRL
        crl = data.get("crl", {})
        if crl.get("totalCalls", 0) > 0:
            hit = crl.get("hitRate", 0)
            saved = crl.get("estimatedBytesSavedFormatted", "")
            self._set_row("crl", hit, f"{hit}%", saved)
        else:
            self._set_row("crl", 0, "—", "no calls")

        now = datetime.now().strftime("%I:%M %p").lstrip("0")
        self._labels["footer"].configure(text=f"Updated {now} · {MAYA_BASE}")

    def _apply_error(self, msg):
        self._labels["status"].configure(text="●", fg=RED)
        self._labels["footer"].configure(
            text=f"Offline — {msg[:80]}",
            fg=RED
        )

    def close(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def run(self):
        self.root.mainloop()


def main():
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--smoke", action="store_true", help="Fetch live data once and print a compact JSON summary without opening the widget.")
    args = parser.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if args.smoke:
        data = fetch_all_data()
        providers = data.get("providers", [])
        ph_map = {p.get("id", ""): p for p in providers if isinstance(p, dict)}
        cfg = data.get("status", {}).get("hermesBridge", {}).get("config", {})
        summary = {
            "ok": True,
            "main_provider": cfg.get("provider") or "openai-codex",
            "main_model": cfg.get("model") or "gpt-5.5",
            "deepseek_configured": bool(ph_map.get("deepseek", {}).get("configured") or data.get("deepseek", {}).get("configured")),
            "providers": sorted(k for k in ph_map.keys() if k),
            "usage_probe_error": (data.get("usage_error") or "")[:180],
        }
        print(json.dumps(summary, indent=2))
        return 0

    app = MayaUsageWidget()
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
