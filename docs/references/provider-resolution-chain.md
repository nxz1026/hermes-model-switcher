# Provider Resolution Chain — "Unknown provider" 排查 (2026-06-13)

## 场景

`model.provider: xunfei` → 飞书 Bot 报 `Unknown provider 'xunfei'`
`model.provider: qiniu` → 同样报错

## 根因

Hermes provider 解析链（4 级，按顺序匹配）：

1. **内置 provider** — deepseek, openrouter, minimax-cn, dashscope, xai, edge, local, nous, openai-codex 等
   - 用 `hermes doctor` 看完整列表
2. **`custom_providers[].name`** — 精确大小写匹配 `name` 字段
   - 如果 `custom_providers` 有 `name: Api.qnaigc.com`，则 `model.provider: Api.qnaigc.com`（注意大小写）
3. **`model_config` 路径** — 仅当 `model.provider: custom`（特殊关键字）
   - 用 `model.api_key` + `model.base_url` + `model.compat`
4. **env var lookup** — 通过 `ENV_PROVIDER_HINTS` 映射

**None match → `Unknown provider '<name>'` 错误。**

## 修复

`hermes config set model.provider custom`

或使用正确的内置/provider name。

## 验证

直接用 httpx 直连测试，不要依赖 gateway 报告来判断 key 是否有效——HTTP 200 是最准确的。

## 关键教训

- **`custom` 不是未知 provider** — 它是一个特殊关键字，告诉 Hermes 使用 `model:` 块的 api_key/base_url/compat
- **不要自己编 provider 名** — 如果不在内置列表、不在 `custom_providers[]`、也不是 `custom`，就一定会失败
- **Provider 解析按顺序，不是并行** — 先命中哪个就用哪个
