"""Model listing — extract models from config (3 schema compatible)."""

from typing import Any

from .env_providers import PROVIDER_DEFAULT_MODELS, read_env_keys


def extract_models(config: dict[str, Any]) -> list[dict[str, str]]:
    """Extract model entries from *config*.

    Supports three config schemas, tried in priority order:

    A) opencode / Hermes v1 — ``provider.<name>.models.<id>.name``
    B) Hermes v2 — ``providers.<name>.models.<id>.name``
    C) Fallback — no ``providers`` section; infer from ``.env`` keys
       (see :func:`~hermes_switch.env_providers.read_env_keys`).
    """
    models: list[dict[str, str]] = []
    seen: set[str] = set()

    # ── Schema A ──────────────────────────────────────────────────────────
    for provider_name, provider_cfg in (config.get("provider") or {}).items():
        for model_id, model_info in (provider_cfg.get("models") or {}).items():
            label = (model_info or {}).get("name", model_id)
            key = f"{provider_name}/{model_id}"
            if key not in seen:
                models.append({
                    "key": key,
                    "provider": provider_name,
                    "model_id": model_id,
                    "label": label,
                })
                seen.add(key)

    # ── Schema B ──────────────────────────────────────────────────────────
    for provider_name, provider_cfg in (config.get("providers") or {}).items():
        for model_id, model_info in (provider_cfg.get("models") or {}).items():
            label = (model_info or {}).get("name", model_id)
            key = f"{provider_name}/{model_id}"
            if key not in seen:
                models.append({
                    "key": key,
                    "provider": provider_name,
                    "model_id": model_id,
                    "label": label,
                })
                seen.add(key)

    # ── Schema C (fallback) ───────────────────────────────────────────────
    if not models:
        for provider, _env_key in read_env_keys():
            for model_id, label in PROVIDER_DEFAULT_MODELS.get(provider, []):
                key = f"{provider}/{model_id}"
                if key not in seen:
                    models.append({
                        "key": key,
                        "provider": provider,
                        "model_id": model_id,
                        "label": label,
                    })
                    seen.add(key)

    return models


def get_current_model(config: dict[str, Any]) -> str | None:
    """Return the active model key (``provider/model-id``) or ``None``."""
    model = config.get("model")
    if isinstance(model, str) and "/" in model:
        return model
    if isinstance(model, dict):
        provider = model.get("provider", "")
        default = model.get("default", "")
        if provider and default:
            return f"{provider}/{default}"
    return None
