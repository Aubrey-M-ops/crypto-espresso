# web3-news-push — Claude Code 工作指南

每日自动抓取加密货币新闻，Claude AI 生成中文摘要并推送 Telegram 频道。

---

## 并行子 Agent 工作流

### 核心模式

主 Agent 将独立任务分配给多个子 Agent，每个子 Agent 在独立的 git worktree 中工作，完成后开 PR，主 Agent 汇总或合并。

```
主 Agent
├── 子 Agent 1 → worktree-1 → 写代码 → push → PR
├── 子 Agent 2 → worktree-2 → 写代码 → push → PR
└── 子 Agent 3 → worktree-3 → 写代码 → push → PR
              ↓
        主 Agent review / merge
```

### 何时派生子 Agent

**适合并行的场景：**
- 多个独立功能模块同时开发（如：新增数据源 + 优化摘要格式 + 修复 Telegram 推送）
- 多个不相关 bug 同时修复
- 不同测试文件的失败，根因相互独立

**不适合并行的场景：**
- 任务之间有依赖（A 完成才能做 B）
- 多个 Agent 会修改同一文件
- 需要全局状态理解才能决策

### 操作步骤

#### 1. 主 Agent：拆解任务

识别独立的问题域，每个域分配给一个子 Agent。

#### 2. 主 Agent：为每个子 Agent 准备 worktree

```bash
# 为每个子 Agent 建独立分支和 worktree
git worktree add ../web3-news-push-worktree-1 -b feature/agent-1-task
git worktree add ../web3-news-push-worktree-2 -b feature/agent-2-task
git worktree add ../web3-news-push-worktree-3 -b feature/agent-3-task
```

#### 3. 主 Agent：并行派生子 Agent

在同一条消息里同时发起多个 Agent 调用（并行，不是串行）：

```
Agent 1 prompt:
  工作目录：../web3-news-push-worktree-1
  任务：[具体任务描述，自包含，不依赖会话上下文]
  约束：只修改 src/xxx.py，不动其他文件
  输出：完成后 git push 并用 gh pr create 开 PR，返回 PR URL

Agent 2 prompt: ...
Agent 3 prompt: ...
```

#### 4. 子 Agent：在 worktree 里完成工作

子 Agent 在自己的 worktree 分支中：
1. 阅读相关文件，理解现有代码
2. 实现任务
3. 运行测试验证
4. `git add` + `git commit`
5. `git push -u origin <branch>`
6. `gh pr create --title "..." --body "..."`
7. 返回 PR URL 给主 Agent

#### 5. 主 Agent：汇总结果

收到所有子 Agent 返回后：
- Review 每个 PR 的改动，确认无冲突
- 按顺序 merge，或合并成一个 PR

---

## 子 Agent Prompt 模板

```markdown
你是一个独立执行子任务的 Agent。

**工作目录：** <worktree 路径，如 ../web3-news-push-worktree-1>
**分支：** <branch 名称>

**任务：**
<具体描述，自包含，包含所有必要上下文>

**约束：**
- 只修改以下文件：<文件列表>
- 不要修改其他文件
- 不要改变接口/函数签名（除非任务要求）

**完成后：**
1. git add <相关文件>
2. git commit -m "<描述性 commit message>"
3. git push -u origin <branch>
4. gh pr create --title "<PR 标题>" --body "<PR 描述>"
5. 返回 PR URL 和变更摘要
```

---

## 项目结构

```
src/
  main.py        # 入口，调度抓取 + 摘要 + 推送
  digest.py      # Claude AI 摘要生成
  fetcher.py     # RSS 新闻抓取
  telegram.py    # Telegram 推送
  kol.py         # KOL 频道抓取（Telethon）
  dedup.py       # 7 天哈希去重
db/              # SQLite 持久化
logs/            # 运行日志
tests/           # 测试文件
```

---

## 开发约定

- Python 3.10+，依赖见 `requirements.txt`
- 环境变量通过 `.env` 注入（不提交）
- 提交前确认不含 API key / token
- 优先编辑已有文件，不新增非必要文件
- 修改摘要逻辑时先阅读 `src/digest.py`，修改推送逻辑时先阅读 `src/telegram.py`

---

## 常用命令

```bash
# 本地运行
python src/main.py

# 运行测试
pytest tests/

# 查看 worktree 列表
git worktree list

# 清理 worktree（任务完成后）
git worktree remove ../web3-news-push-worktree-1
git branch -d feature/agent-1-task
```
