#!/usr/bin/env python3
"""Hermes-model-switcher connectivity verification script.

Usage::

    python3 verify_model_switcher.py           # run all tests
    python3 verify_model_switcher.py --quick    # test only the current model
    python3 verify_model_switcher.py --json     # JSON output (CI / cron)
"""

import argparse
import json
import sys
import time
from pathlib import Path

import httpx
import yaml
from dotenv import dotenv_values

# ── Default paths (can be overridden via env vars) ────────────────────────
CONFIG_PATH = Path(__file__).resolve().parent.parent / ".hermes" / "config.yaml"
ENV_PATH = Path.home() / ".hermes" / ".env"
SKILL_PATH = Path.home() / ".hermes" / "skills" / "devops" / "hermes-model-switcher" / "SKILL.md"

# Override from environment when running outside the repo
CONFIG_PATH = Path(__file__).resolve().parent.parent / ".hermes" / "config.yaml"
if not CONFIG_PATH.exists():
    CONFIG_PATH = Path.home() / ".hermes" / "config.yaml"

PROVIDER_TESTS = [
    ("custom/xunfei", "https://maas-api.cn-huabei-1.xf-yun.com/v2", None, "xopqwen36v35b"),
    ("custom/qiniu", "https://api.qnaigc.com/v1", None, "deepseek/deepseek-v4-flash"),
    ("deepseek/deepseek-chat", "https://api.deepseek.com", "DEEPSEEK_API_KEY", "deepseek-chat"),
    ("deepseek/deepseek-reasoner", "https://api.deepseek.com", "DEEPSEEK_API_KEY", "deepseek-reasoner"),
    ("openrouter/claude-sonnet-4", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "anthropic/claude-sonnet-4"),
    ("openrouter/gpt-4o", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "openai/gpt-4o"),
    ("dashscope/qwen-plus", "https://dashscope.aliyuncs.com/compatible-mode/v1", "DASHSCOPE_API_KEY", "qwen-plus"),
    ("minimax-cn/MiniMax-M3", "https://api.minimaxi.com/v1/chat/completions", "MINIMAX_CN_API_KEY", "MiniMax-M3"),
]


def load_env() -> dict[str, str | None]:
    return dotenv_values(ENV_PATH)


def load_custom_key(name: str) -> tuple[str, str]:
    """Look up a custom provider api_key/base_url from the config file."""
    cfg = yaml.safe_load(CONFIG_PATH.read_text())
    for cp in cfg.get("custom_providers", []):
        cp_name = cp.get("name", "").lower()
        if cp_name in name.lower() or name.lower() in cp_name:
            return cp.get("api_key", ""), cp.get("base_url", "")
    model = cfg.get("model", {})
    return model.get("api_key", ""), model.get("base_url", "")


def test_provider(name: str, base_url: str, env_key: str | None, model: str) -> dict:
    env = load_env()
    key = ""
    if env_key:
        key = env.get(env_key, "") or ""

    if not key:
        cp_key, cp_url = load_custom_key(name.split("/")[0])
        if cp_key:
            key = cp_key
            base_url = cp_url

    if not key:
        return {"name": name, "status": "🔑EMPTY", "detail": f"key not set ({env_key or 'config'})"}

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    }
    if "openrouter" in name or "openrouter" in base_url:
        headers["HTTP-Referer"] = "https://hermes-agent"

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 5,
    }

    start = time.time()
    try:
        with httpx.Client(timeout=10, follow_redirects=False) as c:
            r = c.post(f"{base_url.rstrip('/')}/chat/completions", headers=headers, json=payload)
            elapsed = time.time() - start
            if r.status_code == 200:
                usage = r.json().get("usage", {})
                return {
                    "name": name,
                    "status": "✅",
                    "detail": f"{elapsed:.1f}s tokens={usage.get('total_tokens', '-')}",
                    "elapsed_s": round(elapsed, 2),
                }
            elif r.status_code in (401, 403):
                return {"name": name, "status": "🔑", "detail": "key 无效/过期"}
            elif r.status_code == 404:
                return {"name": name, "status": "❌404", "detail": "endpoint 不匹配"}
            elif r.status_code == 429:
                return {"name": name, "status": "⏳429", "detail": "限流/用量耗尽"}
            elif r.status_code == 400:
                err = r.json().get("error", {}).get("message", "")[:100]
                return {"name": name, "status": f"❌{r.status_code}", "detail": err}
            else:
                return {"name": name, "status": f"❌{r.status_code}", "detail": r.text[:100]}
    except Exception as e:
        return {"name": name, "status": "❌", "detail": f"{type(e).__name__}: {str(e)[:100]}"}


def config_custom_provider_tests() -> list[tuple[str, str, None, str]]:
    """Return tests for every custom provider registered in config.yaml."""
    try:
        cfg = yaml.safe_load(CONFIG_PATH.read_text()) or {}
    except Exception:
        return []
    tests = []
    for cp in cfg.get("custom_providers", []) or []:
        name = cp.get("name") or cp.get("base_url", "custom")
        base_url = cp.get("base_url", "")
        model = cp.get("model") or cp.get("default") or ""
        if base_url and model:
            tests.append((f"custom/{name}", base_url, None, model))
    return tests



def verify_skill_md() -> dict:
    p = Path(SKILL_PATH)
    if p.exists():
        content = p.read_text()
        return {
            "path": str(SKILL_PATH),
            "exists": True,
            "lines": len(content.splitlines()),
            "size_bytes": len(content.encode()),
        }
    return {"path": str(SKILL_PATH), "exists": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    if args.quick:
        cfg = yaml.safe_load(CONFIG_PATH.read_text())
        model_cfg = cfg.get("model", {})
        default = model_cfg.get("default", "")
        base_url = model_cfg.get("base_url", "")
        tests = [(f"current/{default}", base_url, None, default)]
    else:
        seen = set()
        tests = []
        for item in config_custom_provider_tests() + PROVIDER_TESTS:
            if item[0] not in seen:
                tests.append(item)
                seen.add(item[0])

    results = [test_provider(n, u, k, m) for n, u, k, m in tests]
    skill = verify_skill_md()

    ok = sum(1 for r in results if r["status"] == "✅")
    empty = sum(1 for r in results if r["status"] == "🔑EMPTY")
    rate = sum(1 for r in results if "429" in r["status"])
    fail = sum(1 for r in results if "❌" in r["status"])
    warn = sum(1 for r in results if r["status"] == "🔑")

    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(results),
        "ok": ok,
        "empty_key": empty,
        "rate_limited": rate,
        "failed": fail,
        "warning_key": warn,
        "skill_md": skill,
    }

    if args.json_output:
        print(json.dumps({"summary": summary, "results": results}, indent=2, ensure_ascii=False))
    else:
        print(f"\n🔍 hermes-model-switcher 连通性验证 ({summary['timestamp']})")
        print(f"{'=' * 60}")
        for r in results:
            print(f"{r['status']:6} {r['name']:35} {r['detail']}")
        lines = skill.get("lines", 0)
        bytes_ = skill.get("size_bytes", 0)
        print(f"\n📊 总计: {summary['total']} | ✅ {ok} | 🔑KEY {empty} | ⏳429 {rate} | 🔑 {warn} | ❌ {fail}")
        print(f"\n📄 SKILL.md: {lines} 行, {bytes_} 字节" + (" (不存在！)" if not skill['exists'] else ""))

    return 0 if ok > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
