---
name: hermes-model-switcher
description: Switch Hermes main model from CLI. Supports 3 config schemas (v1/opencode, v2/providers, fallback C from .env). Auto-syncs provider/api_key/base_url/compat. Includes gateway reload hint.
tags: [hermes, model-switching, config]
---

# hermes-model-switcher

## 何时触发
- 用户需要切换模型/provider
- 用户遇到 `Unknown provider` 错误
- 用户需要排查哪些 provider 可用/不可用
- 用户想添加自定义 provider（讯飞 MAAS、DashScope、七牛等）

## 步骤

### 1. 查看当前模型配置

```bash
head -8 ~/.hermes/config.yaml
```

### 2. 测试 provider 连通性

运行 Python 脚本测试所有 provider（见 `references/provider-test.py`）。

### 3. 切换模型

```bash
# 切换到 custom (讯飞 MAAS)
hermes config set model.default "xopqwen36v35b"
hermes config set model.api_key "你的讯飞API密钥"
hermes config set model.base_url "https://maas-api.cn-huabei-1.xf-yun.com/v2"
hermes config set model.provider "custom"
hermes config set model.compat "openai"

# 切换到 deepseek
hermes config set model.default "deepseek-chat"
hermes config set model.api_key "你的DeepSeek密钥"
hermes config set model.base_url "https://api.deepseek.com"
hermes config set model.provider "deepseek"
hermes config set model.compat "openai"

# 切换到 openrouter
hermes config set model.default "anthropic/claude-sonnet-4"
hermes config set model.api_key "你的OpenRouter密钥"
hermes config set model.base_url "https://openrouter.ai/api/v1"
hermes config set model.provider "openrouter"
hermes config set model.compat "openai"

# 切换到七牛 (deepseek v4 flash)
hermes config set model.default "deepseek/deepseek-v4-flash"
hermes config set model.api_key "你的七牛密钥"
hermes config set model.base_url "https://api.qnaigc.com/v1"
hermes config set model.provider "custom"
hermes config set model.compat "openai"
```

### 4. 添加自定义 provider 到 custom_providers

在 `config.yaml` 的 `custom_providers` 列表中添加：

```yaml
custom_providers:
- api_key: YOUR_KEY_HERE
  base_url: https://example.com/v1
  model: your-model-id
  name: YourProviderName
```

然后 `model.provider` 设为 `custom`，Hermes 自动匹配 `base_url`。

### 5. 重启 Gateway

```bash
hermes gateway restart
```

或在飞书发消息 `/restart`。

## 关键规则

1. **`provider: custom` 是特殊关键词** — 表示"用 model_config 里的 api_key/base_url"，不是随便的 provider 名
2. **`custom_providers` 的 `name` 字段** — Hermes 用它匹配 provider
3. **`base_url` 不能带尾 `/`** — 必须严格匹配
4. **.env key 和 config.yaml `model.api_key` 是不同的** — `model.api_key` 优先
5. **`custom` provider 从 `model_config` 读取凭证**（`credential_pool.py:2132`）— 只有 `provider == "custom"` 才触发

## 已验证 provider (2026-06-13)

| provider | base_url | compat | 状态 |
|----------|---------|--------|------|
| custom (讯飞 MAAS) | `maas-api.cn-huabei-1.xf-yun.com/v2` | openai | ✅ |
| custom (七牛) | `api.qnaigc.com/v1` | openai | ✅ |
| deepseek | `api.deepseek.com` | openai | ✅ |
| openrouter | `openrouter.ai/api/v1` | openai | ✅ |
| dashscope | `dashscope.aliyuncs.com/compatible-mode/v1` | openai | ✅ |
| minimax-cn | `api.minimaxi.com/v1/chat/completions` | openai | ⏳ 需充值 |

for label, model, base, key, compat in tests:
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
    if "openrouter" in base:
        headers["HTTP-Referer"] = "https://hermes-agent"
    url = f"{base}/chat/completions"
    payload = {"model": model, "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 5}
    try:
        r = httpx.post(url, headers=headers, json=payload, timeout=10)
        print(f"{label}: {'✅' if r.status_code==200 else '❌'+str(r.status_code)} {r.json().get('usage',{}).get('total_tokens','-') if r.status_code==200 else r.text[:80]}")
    except Exception as e:
        print(f"{label}: ❌ {type(e).__name__} {str(e)[:100]}")
```

Key status codes: `200`=OK, `401/403`=key wrong, `404`=endpoint mismatch, `429`=rate limit/quota exhausted.

## Provider Endpoint Reference (verified 2026-06-13)

| Provider | base_url | compat | Note |
|----------|---------|--------|------|
| deepseek | `https://api.deepseek.com` | openai | |
| dashscope | `https://dashscope.aliyuncs.com/compatible-mode` | openai | |
| minimax-cn | `https://api.minimaxi.com/anthropic` | anthropic | **Must include `/anthropic`** |
| openrouter | `https://openrouter.ai/api/v1` | openai | |
| custom | `https://maas-api.cn-huabei-1.xf-yun.com/v2` | openai | **讯飞 MAAS** |
| qiniu | `https://api.qnaigc.com/v1` | openai | **七牛 MAAS (deepseek v4 flash)** |
| xunfei | `https://maas-api.cn-huabei-1.xf-yun.com/v2` | openai | **讯飞 MAAS, 与 custom 共用同一 base_url** |
| xai | `https://api.x.ai` | openai | |

## Shared base_url Pitfall

Multiple `custom_providers` entries can share the same `base_url`. Hermes pools credentials by base_url, so `provider: custom` matches whichever entry's `base_url` equals `model.base_url` — **not by `name`**. E.g., `qiniu` and `xunfei` both point to `maas-api.cn-huabei-1.xf-yun.com/v2`, and `model.provider: custom` matches on base_url, not on name.

**Practical rule**: when adding a custom provider that shares an existing base_url (same underlying platform, different API key), add a new entry to `custom_providers` with the correct `name`, `api_key`, and `base_url`. `model.provider: custom` will still route correctly because credential pooling is base_url-based.

## 一键测试所有 provider (2026-06-13 实测模板)

```python
import httpx
import yaml
from dotenv import dotenv_values

env = dotenv_values("/root/.hermes/.env")
CUSTOM_URL = "https://maas-api.cn-huabei-1.xf-yun.com/v2"
CUSTOM_KEY = yaml.safe_load(open("/root/.hermes/config.yaml"))["model"]["api_key"]

tests = [
    ("dashscope/qwen-plus", "https://dashscope.aliyuncs.com/compatible-mode/v1", env.get("DASHSCOPE_API_KEY", ""), "qwen-plus", "dashscope"),
    ("deepseek/deepseek-chat", "https://api.deepseek.com", env.get("DEEPSEEK_API_KEY", ""), "deepseek-chat", "deepseek"),
    ("minimax-cn/MiniMax-M3", "https://api.minimaxi.com/anthropic/v1", env.get("MINIMAX_CN_API_KEY", ""), "MiniMax-M3", "minimax-cn"),
    ("openrouter/claude-sonnet-4", "https://openrouter.ai/api/v1", env.get("OPENROUTER_API_KEY", ""), "anthropic/claude-sonnet-4", "openrouter"),
    ("custom/xopqwen36v35b", CUSTOM_URL, CUSTOM_KEY, "xopqwen36v35b", "custom"),
]
for name, url, key, model, label in tests:
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
    if "openrouter" in url: headers["HTTP-Referer"] = "https://hermes-agent"
    payload = {"model": model, "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 5}
    try:
        r = httpx.post(url, headers=headers, json=payload, timeout=10)
        status = "✅" if r.status_code == 200 else ("🔑" if r.status_code in (401,403) else f"❌{r.status_code}")
        print(f"{status:3} {name:35} {r.status_code} {r.text[:80]}")
    except Exception as e:
        print(f"❌  {name:35} {type(e).__name__}: {str(e)[:80]}")
```

Status codes: `200`=OK, `401/403`=key wrong/empty, `404`=endpoint mismatch, `429`=quota exhausted, `400`=bad request.

## 自动化验证

**验证脚本**：`scripts/verify_model_switcher.py`

用法：
```bash
python3 scripts/verify_model_switcher.py          # 全部测试
python3 scripts/verify_model_switcher.py --quick   # 只测当前主模型
python3 scripts/verify_model_switcher.py --json    # JSON 输出（cron/CI）
```

输出 < 50 token 汇总 + 每个 provider 的状态码。用于：
- 模型切换后快速验证连通性
- cron 定时巡检（每日跑一次，异常飞书告警）
- SkillOpt gate val set 的数据来源

**验证结果快照 (2026-06-13)**：
| provider | 模型 | 状态 |
|----------|------|------|
| custom (讯飞) | xopqwen36v35b | ✅ |
| custom (七牛) | deepseek v4 flash | ⚠️ base_url 被覆盖 |
| deepseek | deepseek-chat / reasoner | ✅ |
| openrouter | claude-sonnet-4 / gpt-4o | ✅ |
| dashscope | qwen-plus | ✅ |
| minimax-cn | MiniMax-M3 | ❌ 404 endpoint |

## Pitfalls

- **`.env` keys with leading space after `=`** (`KEY= ***`): `set_model` must use `.strip()` not `.rstrip()` — see `references/env-key-leading-space.md`
- **minimax base_url**: must include `/anthropic` subpath, otherwise 404
- **gateway reload**: Hermes `gateway` CLI has no `reload` subcommand, only `restart` — tool defaults to skipping, safe for active cron
- **`providers: {}` empty in config**: C schema fallback triggers, but must have env var in `ENV_PROVIDER_HINTS` to be detected
- **`config.yaml` model block is dict type**: `set_model` mutates `model.provider`, `model.default`, `model.api_key`, `model.base_url`, `model.compat` simultaneously
- **Provider resolution order**: When Hermes resolves `model.provider`, it checks in this order:\n  1. **built-in provider** (deepseek, openrouter, minimax-cn, dashscope, xai, etc.) — full list via `hermes doctor`\n  2. **`custom_providers[].name` match** — exact case-sensitive match against `name` field in `custom_providers` list in config.yaml. E.g. `name: Api.qnaigc.com` → `model.provider: Api.qnaigc.com`\n  3. **`model_config` source** — only when `model.provider: custom` (the special keyword). Uses `model.api_key` + `model.base_url` + `model.compat` from the top-level `model:` block and auto-matches against `custom_providers` base_url for pooling\n  4. **env var lookup** — fallback via `ENV_PROVIDER_HINTS`\n  If none match → `Unknown provider '<name>'` error. **Do NOT make up a provider name** — if it's not built-in, not in `custom_providers[]`, and not `custom`, it will fail.\n\n- **`custom` is a special provider keyword** (expanded): `model.provider: custom` triggers the `model_config` credential source path (`credential_pool.py:2132`). It is NOT an unknown provider — it tells Hermes to use `model.api_key` + `model.base_url` + `model.compat` from the top-level `model:` block. This is the ONLY valid `provider` value when `custom_providers` is empty or when you want to use `model:` block credentials.
- **When `model.provider` is NOT `custom`**: It must be an actual registered provider name — either a built-in one (deepseek, openrouter, minimax-cn, etc.) or a name matching a `custom_providers[]` entry's `name` field. E.g., if `custom_providers` has `name: Maas-api.cn-huabei-1.xf-yun.com`, then `model.provider: Maas-api.cn-huabei-1.xf-yun.com` (case-sensitive). Using a name that is neither built-in, `custom`, nor a `custom_providers[].name` → `Unknown provider` error.
- **Provider resolution order**: built-in provider → `custom_providers[].name` match → `model_config` (when provider=='custom') → env var lookup. If no match at any level → `Unknown provider` error in gateway.
- **2026-06-13实战**: User put `provider: xunfei` → `Unknown provider 'xunfei'`. Then tried `qiniu` → same error. The root cause: neither `xunfei` nor `qiniu` was registered. Fix: revert to `provider: custom` (which was correct all along). The `custom` keyword is the reliable default for unregistered providers with `base_url` in `model:` block.