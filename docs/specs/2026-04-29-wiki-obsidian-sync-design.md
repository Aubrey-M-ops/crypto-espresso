# Wiki → Obsidian Sync 设计文档

**日期：** 2026-04-29  
**状态：** 已批准

---

## 目标

将 VPS 上 `kol_tracker.py` 自动生成的 `wiki/projects/*.md` 文件，每天定时同步到用户的 Obsidian vault，落点为 `Web3/Project_Tracking/`，并在同步完成后发送 Telegram 通知。

---

## 架构

```
VPS
├── main.py → kol_tracker.py 生成 wiki/projects/*.md（现有，不变）
│
├── VPS cron（每天 22:00 UTC = 18:00 Toronto EDT）
│     src/wiki_sync.py：
│       ① rsync wiki/projects/*.md → ~/.wiki-cache/crypto-wiki-private/projects/
│       ② git -C ~/.wiki-cache/... add + commit（无变化则跳过）
│       ③ git push → /opt/crypto-wiki-private.git（VPS bare repo）
│       ④ curl Telegram Bot API → 通知 TELEGRAM_ADMIN_CHAT_ID
│
├── /opt/crypto-wiki-private.git（VPS bare repo，SSH 暴露）
│
Mac（仅 Obsidian Git 社区插件）
  └── 定时 pull from user@vps:/opt/crypto-wiki-private.git
      vault 落点：Web3/Project_Tracking/
                ↓
      Obsidian Sync → 其他设备
```

---

## 组件详细说明

### 1. `src/wiki_sync.py`（新文件）

职责：将本地 wiki 文件同步到 VPS bare repo，并发送通知。

流程：
1. 确保 `~/.wiki-cache/crypto-wiki-private/` 已 clone（首次自动 clone）
2. `rsync wiki/projects/*.md` → `~/.wiki-cache/crypto-wiki-private/projects/`
3. `git diff --quiet` 检查是否有变化，无变化则退出（静默）
4. `git add . && git commit -m "wiki: auto-update YYYY-MM-DD"`
5. `git push origin main`
6. 统计变更文件数，发送 Telegram 通知

Telegram 通知格式：
```
✅ Wiki 已同步 | 更新 N 个项目文件（BTC, ARB...）| 2026-04-29 18:00
```

### 2. VPS bare repo

- 路径：`/opt/crypto-wiki-private.git`
- 初始化：`git init --bare /opt/crypto-wiki-private.git`
- 通过 SSH 对外暴露，供 Obsidian Git 插件 pull
- 目录结构（工作 clone 视角）：
  ```
  crypto-wiki-private/
  └── projects/
      ├── BTC.md
      ├── ARB.md
      └── FET.md
  ```

### 3. VPS cron

- 在现有 cron 配置（`openclaw-cron.yaml` 或系统 crontab）中新增一条
- 时间：`0 22 * * *`（UTC）= 每天 18:00 Toronto EDT
- 命令：`cd /path/to/project && python src/wiki_sync.py`
- `wiki_sync.py` 独立于 `main.py`，单独调度（解耦 wiki 生成与同步时间）

### 4. `main.py` 调整

无需调整。`wiki_sync.py` 作为独立 cron 运行，不耦合到 main pipeline。

### 5. 环境变量（追加到 `.env`）

```
WIKI_WORKING_DIR=/root/.wiki-cache/crypto-wiki-private
WIKI_BARE_REPO=/opt/crypto-wiki-private.git
```

复用现有变量（无需新增）：
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_ADMIN_CHAT_ID`

### 6. Mac：Obsidian Git 插件配置（一次性手动操作）

- 安装 Obsidian 社区插件：**Obsidian Git**
- 在 vault 的 `Web3/Project_Tracking/` 目录下执行：
  ```bash
  git clone user@vps-ip:/opt/crypto-wiki-private.git .
  ```
- 插件设置：
  - Auto pull interval：30 分钟（VPS 每天 22:00 UTC 推送，插件会在之后的下一个 interval 拉取）
  - Pull on startup：开启

---

## 错误处理

| 场景 | 处理方式 |
|---|---|
| wiki/projects/ 无文件 | 跳过，不 commit，不通知 |
| git push 失败 | 记录 warning log，不发通知 |
| Telegram 发送失败 | 记录 warning log，不阻塞主流程 |
| bare repo 不存在 | 脚本启动时检查，打印明确错误信息并退出 |

---

## 不在本次范围内

- wiki 文件内容格式修改
- Obsidian 模板或 dataview 集成
- VPS SSH key 管理（假设已有 Mac→VPS SSH 访问）
