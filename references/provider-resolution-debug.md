# Provider Resolution Debug — "Unknown provider" 实战 (2026-06-13)

## 场景

`model.provider: xunfei` → 飞书 Bot 报 `Unknown provider 'xunfei'`
`model.provider: qiniu` → 同样报错

## 根因

Hermes provider 解析链：
1. 是否内置 provider？→ xunfei/qiniu 都不是
2. 是否 `custom_providers[].name`？→ 当时没注册
3. 是否 `custom` 关键字？→ 也不是
4. → ❌ Unknown provider

**实际上 model.api_key + model.base_url 都在 config.yaml 里**，只需要 `model.provider: custom` 就能触发 credential pool 的 `model_config` 路径。

## 修复

```
hermes config set model.provider custom
```
或手动改 config.yaml。

## 验证

用 httpx 直连测试（见 SKILL.md 的 Provider Direct Testing 节），不要依赖 gateway 报告来判断 key 是否有效——直接 HTTP 200 是最准确的。

## 后续发现

### 共享 base_url 的多个 provider
`custom_providers` 里可以注册多个 provider 指向同一 base_url（如讯飞 qiniu + xunfei 共用 `maas-api.cn-huabei-1.xf-yun.com/v2`）。凭证池按 base_url 聚合，`model.provider: custom` 路由基于 base_url 匹配而非 name。

### Provider 解析顺序 (2026-06-13 实测)
1. **内置 provider** (deepseek, openrouter, minimax-cn, dashscope, xai, etc.) → 见 `hermes doctor`
2. **`custom_providers[].name`** → 精确大小写匹配 `name` 字段
3. **`model_config` source** → 仅当 `model.provider: custom`。用 `model.api_key` + `model.base_url` + `model.compat`
4. **env var lookup** → 通过 `ENV_PROVIDER_HINTS` 映射

None match → `Unknown provider '<name>'` 错误。**不要用虚构的 provider 名**——如果不在内置列表、不在 `custom_providers[]`、也不是 `custom`，就一定会失败。