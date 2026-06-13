# Hermes 压缩 + Hindsight 协同

## 何时使用

- 用户询问是否需要压缩记忆
- 用户设置 `compression.threshold`
- 用户想优化 token 消耗
- 用户问 Hindsight 是否替代了 MEMORY.md

## 关键发现（2026-06-13 实战）

### 架构分工

Hermes 有两个独立的记忆机制，服务不同目的：

**1. session compression（当前会话压缩）**
- 作用域：当前 session 内的对话历史
- 目的：防止 token 超限，压缩对话历史（保留最近 20 条 + 前 3 条 + 摘要）
- 触发阈值：`compression.threshold`（默认 0.5，可调）
- 配置：`~/.hermes/config.yaml` → `compression.*`

**2. Hindsight（跨 session 向量记忆）**
- 作用域：跨 session 持久存储
- 目的：自动 retain 关键事实，供未来 session 检索
- 配置：Hindsight Docker 容器 + `vectorize.io` 向量数据库
- 路径：`~/.hermes/HINDSIGHT.md`

**3. MEMORY.md / USER.md（传统记忆）**
- 作用域：当前 profile
- 目的：持久用户配置
- 状态：如果启用了 Hindsight，这些文件通常不存在

### 压缩的收益评估

压缩节省 token 的前提是**对话历史占 tokens 的大部分**。但：

- 系统 prompt（SOUL/USER/AGENTS/MEMORY/skills 索引）通常占 **90-99%** 输入 tokens
- 对话历史只占 **1-10%**
- **结论**：当 system prompt 很大时，压缩的收益很小（< 1%）

### 推荐配置

| 场景 | threshold | target_ratio | 说明 |
|------|-----------|--------------|------|
| 系统 prompt 大 | 0.65-0.7 | 0.2 | 减少不必要压缩，依赖 Hindsight |
| 系统 prompt 小 | 0.4-0.5 | 0.2 | 正常压缩对话历史 |
| 对话历史长 | 0.5 | 0.15 | 更激进压缩 |

### 压缩不做的事

- ❌ 不压缩 system prompt（system prompt 是每轮重建的）
- ❌ 不替代 Hindsight（Hindsight 管跨 session，压缩管当前 session）
- ❌ 不替代 MEMORY.md（Hindsight 已替代）

### 验证压缩是否生效

```bash
# 查看当前压缩配置
grep -A 5 '^compression:' ~/.hermes/config.yaml

# 查看 Hindsight 状态
docker ps | grep hindsight

# 查看当前 session token 消耗
grep -A 10 'SELECT.*sessions' ~/.hermes/state.db  # 需 sqlite3
```

## 相关

- `hermes-agent` skill — compression 配置章节
- `hindsight-3-defense-lines` — Hindsight 隔离规则
- `hindsight-recovery-procedure` — Hindsight 容器恢复
