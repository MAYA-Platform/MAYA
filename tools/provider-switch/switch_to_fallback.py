#!/usr/bin/env python3
"""Emergency Fallback Switch — automated provider failover for cron/scripts.
Usage: python switch_to_fallback.py [openai|gemini|deepseek]
"""
import subprocess
import sys
from pathlib import Path

HERMES_HOME = Path.home() / "AppData" / "Local" / "hermes"

FALLBACKS = {
    "openai": [
        ["config", "set", "model.provider", "openai"],
        ["config", "set", "model.model", "gpt-4o"],
    ],
    "gemini": [
        ["config", "set", "model.provider", "google"],
        ["config", "set", "model.model", "gemini-2.5-flash"],
    ],
    "deepseek": [
        ["config", "set", "model.provider", "deepseek"],
        ["config", "set", "model.model", "deepseek-v4-pro"],
    ],
}


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "gemini"

    if target not in FALLBACKS:
        print(f"Unknown target: {target}. Options: {', '.join(FALLBACKS)}")
        sys.exit(1)

    cmds = FALLBACKS[target]
    print(f"Switching primary LLM to {target}...")

    for cmd in cmds:
        result = subprocess.run(
            ["hermes"] + cmd,
            cwd=str(HERMES_HOME),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            print(f"FAILED: hermes {' '.join(cmd)}")
            print(result.stderr)
            sys.exit(1)

    print(f"✅ Switched to {target}. Restart Hermes to apply.")


if __name__ == "__main__":
    main()
