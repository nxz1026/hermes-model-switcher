import json
import shutil
from pathlib import Path

CONFIG_PATHS = [
    Path.home() / ".config" / "opencode" / "opencode.json",
    Path.home() / ".config" / "hermes" / "config.json",
]


def find_config(path=None):
    if path:
        p = Path(path)
        if p.exists():
            return p
        return None
    for p in CONFIG_PATHS:
        if p.exists():
            return p
    return None


def load_config(path):
    return json.loads(path.read_text(encoding="utf-8"))


def backup_config(path):
    backup = path.with_suffix(path.suffix + ".backup")
    shutil.copy2(path, backup)
    return backup


def extract_models(config):
    models = []
    providers = config.get("provider", {})
    for provider_name, provider_cfg in providers.items():
        for model_id, model_info in provider_cfg.get("models", {}).items():
            label = model_info.get("name", model_id)
            key = f"{provider_name}/{model_id}"
            models.append({"key": key, "provider": provider_name, "model_id": model_id, "label": label})
    return models


def get_current_model(config):
    model = config.get("model")
    if model and "/" in model:
        return model
    return None


def set_model(config, model_key):
    config["model"] = model_key
    return config


def save_config(config, path):
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
