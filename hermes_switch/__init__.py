"""hermes-model-switcher — Switch the active Hermes Agent model from the CLI."""

from .env_providers import (
    ENV_PROVIDER_HINTS,
    PROVIDER_DEFAULT_MODELS,
    PROVIDER_ENDPOINT,
    read_env_keys,
)
from .list_models import extract_models, get_current_model
from .switch import (
    CONFIG_PATHS,
    backup_config,
    find_config,
    load_config,
    reload_gateway,
    save_config,
    set_model,
)

__all__ = [
    "CONFIG_PATHS",
    "ENV_PROVIDER_HINTS",
    "PROVIDER_DEFAULT_MODELS",
    "PROVIDER_ENDPOINT",
    "backup_config",
    "extract_models",
    "find_config",
    "get_current_model",
    "load_config",
    "read_env_keys",
    "reload_gateway",
    "save_config",
    "set_model",
]
