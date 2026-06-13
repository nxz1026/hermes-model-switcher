"""CLI entry point for hermes-switch."""

import argparse
import subprocess
import sys

from . import (
    backup_config,
    extract_models,
    find_config,
    get_current_model,
    load_config,
    reload_gateway,
    save_config,
    set_model,
)


def pick_with_fzf(models, current_key):
    """Launch fzf for interactive model selection."""
    rows = "\n".join(
        f"{'●' if m['key'] == current_key else '○'}  {m['key']:40s}  {m['label']}"
        for m in models
    )
    try:
        result = subprocess.run(
            ["fzf", "--height=40%", "--prompt=Select model > "],
            input=rows,
            text=True,
            capture_output=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None
        line = result.stdout.strip()
        if not line:
            return None
        key = line.split()[1]
        return key
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def pick_builtin(models, current_key):
    """Number-based built-in interactive picker."""
    print()
    for i, m in enumerate(models, 1):
        marker = "●" if m["key"] == current_key else "○"
        print(f"  {i:3d}. {marker}  {m['key']:40s}  {m['label']}")
    print()
    while True:
        try:
            choice = input(f"  Select [1-{len(models)}] (q to quit): ").strip()
            if choice.lower() in ("q", ""):
                return None
            idx = int(choice) - 1
            if 0 <= idx < len(models):
                return models[idx]["key"]
        except (ValueError, IndexError):
            pass
        print("  Invalid choice, try again.")


def main():
    parser = argparse.ArgumentParser(description="Switch Hermes main model")
    parser.add_argument(
        "--config", "-c",
        help="Path to config file",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available models and exit",
    )
    parser.add_argument(
        "--plain",
        action="store_true",
        help="Use the built-in selector instead of fzf even when fzf is available",
    )
    parser.add_argument(
        "model",
        nargs="?",
        help="Model key to switch to (e.g. deepseek/deepseek-chat)",
    )
    args = parser.parse_args()

    config_path = find_config(args.config)
    if not config_path:
        print("Config file not found.", file=sys.stderr)
        sys.exit(1)

    config = load_config(config_path)
    models = extract_models(config)
    if not models:
        print("No models found in config.", file=sys.stderr)
        sys.exit(1)

    current = get_current_model(config)
    max_key_len = max(len(m["key"]) for m in models)

    if args.list:
        print(f"Config: {config_path}")
        print(f"Current model: {current or '(not set)'}")
        print()
        for m in models:
            marker = "●" if m["key"] == current else "○"
            print(f"  {marker}  {m['key']:{max_key_len}}  {m['label']}")
        return

    target = args.model
    if not target:
        if not args.plain and _has_fzf():
            target = pick_with_fzf(models, current)
        else:
            target = pick_builtin(models, current)
        if not target:
            print("No model selected.")
            return

    if target not in {m["key"] for m in models}:
        print(f"Unknown model: {target}", file=sys.stderr)
        sys.exit(1)

    backup_path = backup_config(config_path)
    config = set_model(config, target)
    save_config(config, config_path)

    print(f"Config:    {config_path}")
    print(f"Backup:    {backup_path}")
    print(f"Previous:  {current or '(not set)'}")
    print(f"Current:   {target}")

    ok, msg = reload_gateway()
    if ok:
        print(f"Gateway:   ok (gateway restarted)")
    else:
        print(f"Gateway:   skipped — {msg}")
        print(f"           Run manually: hermes gateway restart")


def _has_fzf():
    try:
        subprocess.run(["fzf", "--version"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


if __name__ == "__main__":
    main()
