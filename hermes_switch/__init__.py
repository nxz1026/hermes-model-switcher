"""hermes-model-switcher 兼容层 — 支持 ~/.hermes/config.yaml (YAML) 和 ~/.config/hermes/config.json (JSON)。

3 种 schema 兼容:
- A) opencode/Hermes v1: provider.{name}.models.{id}.name
- B) Hermes v2 (你实际用的): providers.{name}.models.{id}.name
- C) Hermes v2 空 providers + .env keys: 从 ~/.hermes/.env 抽 *_API_KEY 推断可用 provider

改完 model 后调 hermes gateway reload (SIGUSR1) 让 gateway reload.
"""
import json
import shutil
import subprocess
from pathlib import Path

CONFIG_PATHS = [
    Path.home() / ".hermes" / "config.yaml",
    Path.home() / ".hermes" / "config.yml",
    Path.home() / ".config" / "hermes" / "config.json",
    Path.home() / ".config" / "opencode" / "opencode.json",
]

# C schema fallback — 当 config 里 providers 空时，从这些 (provider, env_key) 推断
ENV_PROVIDER_HINTS = {
    "DEEPSEEK_API_KEY": "deepseek",
    "DASHSCOPE_API_KEY": "dashscope",
    "MINIMAX_CN_API_KEY": "minimax-cn",
    "OPENROUTER_API_KEY": "openrouter",
    "QINIU_API_KEY": "qiniu",
    "XAI_API_KEY": "xai",
    "TAVILY_API_KEY": "tavily",  # search-only, 不在切换列表
}

# 每个 provider 的常见模型 (硬编码，避免 model_catalog 联网)
PROVIDER_DEFAULT_MODELS = {
    "deepseek": [("deepseek-chat", "DeepSeek Chat"), ("deepseek-reasoner", "DeepSeek Reasoner")],
    "dashscope": [("qwen-plus", "Qwen Plus"), ("qwen-max", "Qwen Max")],
    "minimax-cn": [("MiniMax-M3", "MiniMax M3")],
    "openrouter": [("anthropic/claude-sonnet-4-20250514", "Claude Sonnet 4"), ("openai/gpt-4o-2025-01-20", "GPT-4o")],
    "qiniu": [("qwen2.5-72b-instruct", "Qwen 72B (七牛)")],
    "xai": [("grok-3-beta", "Grok 3 Beta")],
}

PROVIDER_ENDPOINT = {
    "deepseek":    {"env_key": "DEEPSEEK_API_KEY",   "base_url": "https://api.deepseek.com",                    "compat": "openai"},
    "dashscope":   {"env_key": "DASHSCOPE_API_KEY",  "base_url": "https://dashscope.aliyuncs.com/compatible-mode", "compat": "openai"},
    "minimax-cn":  {"env_key": "MINIMAX_CN_API_KEY", "base_url": "https://api.minimaxi.com",                      "compat": "anthropic"},
    "openrouter":  {"env_key": "OPENROUTER_API_KEY", "base_url": "https://openrouter.ai/api/v1",                 "compat": "openai"},
    "qiniu":       {"env_key": "QINIU_API_KEY",      "base_url": "https://maas-api.cn-huabei-1.xf-yun.com/v2",   "compat": "openai"},
    "xai":         {"env_key": "XAI_API_KEY",        "base_url": "https://api.x.ai",                             "compat": "openai"},
}


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
    text = path.read_text(encoding="utf-8")
    if path.suffix in (".yaml", ".yml"):
        try:
            import yaml
            return yaml.safe_load(text)
        except ImportError:
            raise SystemExit("PyYAML not installed. pip install pyyaml")
    return json.loads(text)


def backup_config(path):
    backup = path.with_suffix(path.suffix + ".backup")
    shutil.copy2(path, backup)
    return backup


def _read_env_keys():
    """从 ~/.hermes/.env 读出 (provider_name, env_key) 列表 (key 存在则纳入)."""
    env_path = Path.home() / ".hermes" / ".env"
    if not env_path.exists():
        return []
    out = []
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        for env_key, provider in ENV_PROVIDER_HINTS.items():
            if line.startswith(env_key + "="):
                val = line.split("=", 1)[1].rstrip()
                # 跳过空值 + 已知占位符
                if val and "PLACEHOLDER" not in val and val != "***":
                    out.append((provider, env_key))
                break
    return out


def extract_models(config):
    """3 种 schema 兼容. 优先级: A > B > C."""
    models = []
    seen = set()

    # A schema
    for provider_name, provider_cfg in (config.get("provider") or {}).items():
        for model_id, model_info in (provider_cfg.get("models") or {}).items():
            label = (model_info or {}).get("name", model_id)
            key = f"{provider_name}/{model_id}"
            if key not in seen:
                models.append({"key": key, "provider": provider_name, "model_id": model_id, "label": label})
                seen.add(key)

    # B schema
    for provider_name, provider_cfg in (config.get("providers") or {}).items():
        for model_id, model_info in (provider_cfg.get("models") or {}).items():
            label = (model_info or {}).get("name", model_id)
            key = f"{provider_name}/{model_id}"
            if key not in seen:
                models.append({"key": key, "provider": provider_name, "model_id": model_id, "label": label})
                seen.add(key)

    # C schema fallback
    if not models:
        for provider, _env_key in _read_env_keys():
            for model_id, label in PROVIDER_DEFAULT_MODELS.get(provider, []):
                key = f"{provider}/{model_id}"
                if key not in seen:
                    models.append({"key": key, "provider": provider, "model_id": model_id, "label": label})
                    seen.add(key)

    return models


def get_current_model(config):
    model = config.get("model")
    if isinstance(model, str) and "/" in model:
        return model
    if isinstance(model, dict):
        provider = model.get("provider", "")
        default = model.get("default", "")
        if provider and default:
            return f"{provider}/{default}"
    return None


def set_model(config, model_key):
    """切换 model — 同步更新 model.provider/model.default/model.api_key/model.base_url.

    返回 config.
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

    # 同步 api_key + base_url — 从 PROVIDER_ENDPOINT 拉, .env 读
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
                    # .env 可能 = 后有空格, 兼容 "KEY=val" 和 "KEY= val"
                    api_key = line.split("=", 1)[1].strip()
                    if api_key and "PLACEHOLDER" not in api_key and api_key != "***":
                        config["model"]["api_key"] = api_key
                    break

    if base_url:
        config["model"]["base_url"] = base_url

    return config


def save_config(config, path):
    if path.suffix in (".yaml", ".yml"):
        try:
            import yaml
            text = yaml.safe_dump(config, allow_unicode=True, sort_keys=False, default_flow_style=False)
        except ImportError:
            raise SystemExit("PyYAML not installed. pip install pyyaml")
    else:
        text = json.dumps(config, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def reload_gateway():
    """Hermes gateway 改完配置后需要 restart 让新配置生效.

    Note: hermes gateway CLI 没有 reload 子命令, 用 restart 代替.
    restart 会中断当前 session, 改完 config 后用户需手动决定.
    """
    import os
    # 默认不打 restart, 改完提示用户 — 防止误关活跃 gateway
    # 如果 HERMES_SWITCH_FORCE_RESTART=1 才执行
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
