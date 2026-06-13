"""Provider metadata and environment-key resolution.

Exports constants and a helper to discover available providers
from ``~/.hermes/.env``.
"""

from pathlib import Path
from typing import List, Tuple

# ── C-schema fallback — when config has no providers section ──────────────
# Maps env-var name → provider name.
ENV_PROVIDER_HINTS: dict[str, str] = {
    "DEEPSEEK_API_KEY": "deepseek",
    "DASHSCOPE_API_KEY": "dashscope",
    "MINIMAX_CN_API_KEY": "minimax-cn",
    "OPENROUTER_API_KEY": "openrouter",
    "QINIU_API_KEY": "qiniu",
    "XAI_API_KEY": "xai",
    "XUNFEI_API_KEY": "xunfei",
    "TAVILY_API_KEY": "tavily",  # search-only, excluded from model list
}

# ── Default model IDs per provider (hardcoded, no network call) ───────────
PROVIDER_DEFAULT_MODELS: dict[str, list[tuple[str, str]]] = {
    "deepseek": [("deepseek-chat", "DeepSeek Chat"), ("deepseek-reasoner", "DeepSeek Reasoner")],
    "dashscope": [("qwen-plus", "Qwen Plus"), ("qwen-max", "Qwen Max")],
    "minimax-cn": [("MiniMax-M3", "MiniMax M3")],
    "openrouter": [
        ("anthropic/claude-sonnet-4-20250514", "Claude Sonnet 4"),
        ("openai/gpt-4o-2025-01-20", "GPT-4o"),
    ],
    "qiniu": [("qwen2.5-72b-instruct", "Qwen 72B (七牛)")],
    "xai": [("grok-3-beta", "Grok 3 Beta")],
    "xunfei": [("xopqwen36v35b", "Qwen 36v35B (讯飞)")],
}

# ── Endpoint metadata per provider ────────────────────────────────────────
PROVIDER_ENDPOINT: dict[str, dict[str, str]] = {
    "deepseek": {
        "env_key": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com",
        "compat": "openai",
    },
    "dashscope": {
        "env_key": "DASHSCOPE_API_KEY",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode",
        "compat": "openai",
    },
    "minimax-cn": {
        "env_key": "MINIMAX_CN_API_KEY",
        "base_url": "https://api.minimaxi.com/anthropic",
        "compat": "anthropic",
    },
    "openrouter": {
        "env_key": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "compat": "openai",
    },
    "qiniu": {
        "env_key": "QINIU_API_KEY",
        "base_url": "https://api.qnaigc.com/v1",
        "compat": "openai",
    },
    "xai": {
        "env_key": "XAI_API_KEY",
        "base_url": "https://api.x.ai",
        "compat": "openai",
    },
    "xunfei": {
        "env_key": "XUNFEI_API_KEY",
        "base_url": "https://maas-api.cn-huabei-1.xf-yun.com/v2",
        "compat": "openai",
    },
}


def read_env_keys() -> list[tuple[str, str]]:
    """Read ``~/.hermes/.env`` and return ``(provider_name, env_key)`` pairs.

    Only includes variables whose value is non-empty and not a placeholder.
    """
    env_path = Path.home() / ".hermes" / ".env"
    if not env_path.exists():
        return []

    out: list[tuple[str, str]] = []
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        for env_key, provider in ENV_PROVIDER_HINTS.items():
            if line.startswith(env_key + "="):
                val = line.split("=", 1)[1].strip()
                if val and "PLACEHOLDER" not in val and val != "***":
                    out.append((provider, env_key))
                break
    return out
