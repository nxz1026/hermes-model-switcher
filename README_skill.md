# hermes-model-switcher

Hermes Agent 模型切换 CLI 工具 + 连通性验证。

## 快速安装

```bash
git clone https://github.com/nxz1026/hermes-model-switcher.git /tmp/hms
cd /tmp/hms && pip install --break-system-packages -e .
```

安装后提供 `hermes-switch` CLI 命令。

## 安装验证

```bash
hermes-switch --list    # 列出所有可用模型 + 当前活跃
hermes-switch --help    # 完整帮助
```

## 命令行用法

列出所有可用模型 + 当前活跃：

```bash
hermes-switch --list
```

切换到指定模型：

```bash
hermes-switch <provider>/<model_id>
```

示例：

```bash
# 切换到 OpenRouter 的 Claude
hermes-switch openrouter/claude-sonnet-4

# 切换到 DeepSeek
hermes-switch deepseek/deepseek-chat

# 切换回当前主模型（讯飞）
hermes-switch custom/xopqwen36v35b
```

## 输出格式

运行 `hermes-switch --list` 会输出类似如下：

```
📁 Config: /root/.hermes/config.yaml
● ○ ○ ─── 当前活跃模型 ●───

  ○ openrouter/claude-sonnet-4      (openrouter, default: claude-sonnet-4-20250514)
  ○ deepseek/deepseek-chat          (deepseek, default: deepseek-chat)
  ● custom/xopqwen36v35b           (custom, default: xopqwen36v35b) ← 当前
  ○ dashscope/qwen-plus             (dashscope, default: qwen-plus)
```

- `●` — 当前活跃
- `○` — 可用

## 支持的 Provider

| Provider | 环境变量 | base_url | compat |
|----------|----------|----------|--------|
| deepseek | `DEEPSEEK_API_KEY` | `api.deepseek.com` | openai |
| openrouter | `OPENROUTER_API_KEY` | `openrouter.ai/api/v1` | openai |
| dashscope | `DASHSCOPE_API_KEY` | `dashscope.aliyuncs.com/compatible-mode` | openai |
| custom (讯飞) | `.env` / config | `maas-api.cn-huabei-1.xf-yun.com/v2` | openai |
| minimax-cn | `MINIMAX_CN_API_KEY` | `api.minimaxi.com/anthropic` | anthropic |

## 添加新 Provider

在三个配置字典中分别注册：

1. `ENV_PROVIDER_HINTS` — 映射 env key → provider 名
2. `PROVIDER_DEFAULT_MODELS` — 注册默认模型列表
3. `PROVIDER_ENDPOINT` — 注册 base_url + compat

## 连通性验证

提供 `scripts/verify_model_switcher.py` 用于自动化验证：

```bash
# 全部测试
python3 scripts/verify_model_switcher.py

# 只测当前主模型
python3 scripts/verify_model_switcher.py --quick

# JSON 输出（适合 cron/CI）
python3 scripts/verify_model_switcher.py --json
```

输出示例：

```
🔍 hermes-model-switcher 连通性验证 (2026-06-13 06:17:33)
============================================================
✅      custom/xunfei                       1.5s tokens=18
✅      deepseek/deepseek-chat              1.1s tokens=10
✅      openrouter/claude-sonnet-4          1.7s tokens=13
✅      dashscope/qwen-plus                 1.2s tokens=14
❌404   minimax-cn/MiniMax-M3               endpoint 不匹配

📊 总计: 8 | ✅ 6 | ❌ 2
```

## 文件结构

```
hermes-model-switcher/
├── hermes_switch/
│   ├── __init__.py         # 入口 + CLI 解析
│   ├── switch.py           # 核心切换逻辑 (3 套 schema 兼容)
│   ├── list_models.py      # --list 输出
│   └── env_providers.py    # 环境变量 → provider 映射
├── scripts/
│   └── verify_model_switcher.py  # 连通性验证
├── references/
│   ├── env-key-leading-space.md     # shell 转义空格 bug
│   └── provider-resolution-debug.md # "Unknown provider" 排查
├── SKILL.md                # Skill.md 主文件
├── README.md               # 本文档
├── setup.py                # pip install 配置
└── pyproject.toml          # uv/pip 元数据
```

## 注意事项

- `config.yaml` 修改后需要 `/reset` 或 gateway `restart` 才能生效
- `.env` 中的 key 值不能有空格（`KEY= value` 会失败）
- minimax-cn 的 base_url 必须包含 `/anthropic` 后缀
- gateway 没有 `reload` 子命令，只能用 `restart`

## License

MIT
