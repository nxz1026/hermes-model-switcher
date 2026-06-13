"""Core switching logic — config loading, model switching, save, and gateway restart."""

import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from .env_providers import PROVIDER_ENDPOINT

CONFIG_PATHS: list[Path] = [
    Path.home() / ".hermes" / "config.yaml",
    Path.home() / ".hermes" / "config.yml",
    Path.home() / ".config" / "hermes" / "config.json",
    Path.home() / ".config" / "opencode" / "opencode.json",
]


def find_config(path: str | None = None) -> Path | None:
    """Locate the Hermes config file, optionally from a user-supplied path."""
    if path:
        p = Path(path)
        return p if p.exists() else None
    for p in CONFIG_PATHS:
        if p.exists():
            return p
    return None


def load_config(path: Path) -> Any:
    """Load a YAML or JSON config file."""
    text = path.read_text(encoding="utf-8")
    if path.suffix in (".yaml", ".yml"):
        try:
            import yaml

            return yaml.safe_load(text)
        except ImportError:
            raise SystemExit("PyYAML not installed. pip install pyyaml")
    return json.loads(text)


def save_config(config: Any, path: Path) -> None:
    """Write *config* back to *path* in the original format (YAML / JSON)."""
    if path.suffix in (".yaml", ".yml"):
        try:
            import yaml

            text = yaml.safe_dump(
                config,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            )
        except ImportError:
            raise SystemExit("PyYAML not installed. pip install pyyaml")
    else:
        text = json.dumps(config, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def backup_config(path: Path) -> Path:
    """Create a timestamped backup of the config file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(f".{timestamp}.backup")
    shutil.copy2(path, backup)
    return backup


def set_model(config: dict[str, Any], model_key: str) -> dict[str, Any]:
    """Switch *config* to *model_key* (``provider/model-id``).

    Updates ``model.provider`` / ``model.default`` / ``model.api_key`` /
    ``model.base_url`` / ``model.compat``.  Returns the mutated config dict.
    """
    provider, model_id = model_key.split("/", 1)

    if isinstance(config.get("model"), dict):
        config["model"]["provider"] = provider
        config["model"]["default"] = model_id
    elif isinstance(config.get("model"), str):
        config["model"] = model_key
        return config
    else:
        config["model"] = {"provider": provider, "default": model_id}

    # ── Sync api_key / base_url / compat from endpoint map & .env ──────
    endpoint = PROVIDER_ENDPOINT.get(provider, {})
    env_key = endpoint.get("env_key", "")
    base_url = endpoint.get("base_url", "")
    compat = endpoint.get("compat", "")

    config["model"]["compat"] = compat or "openai"

    if env_key:
        env_path = Path.home() / ".hermes" / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith(env_key + "="):
                    api_key = line.split("=", 1)[1].strip()
                    if api_key and "PLACEHOLDER" not in api_key and api_key != "***":
                        config["model"]["api_key"] = api_key
                    break

    if base_url:
        config["model"]["base_url"] = base_url

    return config


def reload_gateway() -> tuple[bool, str]:
    """Attempt to restart the Hermes gateway.

    .. note::

       The ``hermes gateway`` CLI has no ``reload`` subcommand, so we use
       ``restart``.  To prevent accidental disruption the restart is only
       performed when the environment variable
       ``HERMES_SWITCH_FORCE_RESTART=1`` is set.
    """
    if not os.environ.get("HERMES_SWITCH_FORCE_RESTART"):
        return False, "Set HERMES_SWITCH_FORCE_RESTART=1 to restart gateway automatically"
    try:
        result = subprocess.run(
            ["hermes", "gateway", "restart"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0, (result.stdout + result.stderr).strip()
    except FileNotFoundError:
        return False, "hermes CLI not found in PATH"
    except subprocess.TimeoutExpired:
        return False, "hermes gateway restart timed out"
