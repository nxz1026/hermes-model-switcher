# hermes-switch CLI Alias Divergence (2026-06-13)

## 问题

`hermes-switch --list` 列出 `xunfei/xopqwen36v35b`、`minimax-cn/MiniMax-M3` 等别名，
但这些**不是** Hermes core config.yaml 里的 provider 字段值。

| CLI 显示名 (hermes-switch 别名) | Hermes core config.yaml provider 值 |
|---|---|
| `xunfei/xopqwen36v35b` | `custom` |
| `minimax-cn/MiniMax-M3` | `minimax-cn` (这个刚好一致) |
| `custom/xopqwen36v35b` | `custom` (CLI 也认) |

## 症状

- CLI `hermes-switch --list` 显示某个 provider 可用
- 但切过去后 Hermes core 报 `Unknown provider '<name>'`
- 或切 `custom/...` 报 `Unknown model`

## 原因

`hermes-switch` CLI 维护自己的 `PROVIDER_HINTS` 映射表（`hermes_switch/env_providers.py`），
与 Hermes core 的 `credential_pool.py` provider resolution 是两套独立的系统。

## 解决方案

永远直接编辑 `~/.hermes/config.yaml`：
1. 改 `model.provider` → 用 `custom`（讯飞）或已注册的 provider name
2. 改 `model.default` → 模型 ID
3. 确保 `custom_providers` 里有对应的 name+api_key+base_url
4. `kill -USR1 <gateway_pid>` reload

## 验证

切完后跑 `hermes-switch --list` 看 CLI 是否列出对应模型，
以及直接发一条消息测试 Hermes core 是否响应。
