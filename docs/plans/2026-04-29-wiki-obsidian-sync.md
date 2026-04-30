# Wiki → Obsidian Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 每天 22:00 UTC 自动将 `wiki/projects/*.md` 同步到 VPS bare repo，Obsidian Git 插件 pull 后落入 vault，并发送 Telegram 通知。

**Architecture:** VPS 上新增独立脚本 `src/wiki_sync.py`，复制 wiki 文件到 working clone，git commit + push 到 `/opt/crypto-wiki-private.git`（VPS bare repo），再通过 Telegram Bot 发通知。`openclaw-cron.yaml` 增加每天 22:00 UTC 的调度。Mac 侧只需一次性配置 Obsidian Git 插件。

**Tech Stack:** Python 3.10+, httpx（已有）, subprocess（标准库）, shutil（标准库）, pytest, openclaw-cron

---

## File Map

| 操作 | 路径 | 职责 |
|---|---|---|
| Create | `src/wiki_sync.py` | 核心同步逻辑：clone 检测、文件同步、git commit/push、Telegram 通知 |
| Create | `test/test_wiki_sync.py` | 单元测试 |
| Modify | `.env` | 追加 `WIKI_WORKING_DIR`、`WIKI_BARE_REPO` |
| Modify | `openclaw-cron.yaml` | 追加每天 22:00 UTC 的 wiki_sync 调度 |

---

## Task 1：VPS 一次性初始化（手动操作，无代码）

**Files:** 无（VPS shell 操作）

- [ ] **Step 1: 在 VPS 上初始化 bare repo**

```bash
sudo git init --bare /opt/crypto-wiki-private.git
sudo chown -R $USER:$USER /opt/crypto-wiki-private.git
```

- [ ] **Step 2: 初始化 working clone 并创建 main 分支**

```bash
mkdir -p ~/.wiki-cache
git clone /opt/crypto-wiki-private.git ~/.wiki-cache/crypto-wiki-private
cd ~/.wiki-cache/crypto-wiki-private
mkdir -p projects
touch projects/.gitkeep
git add .
git commit -m "init: scaffold wiki repo"
git push origin HEAD:main
git checkout main
```

- [ ] **Step 3: 验证 bare repo 有 main 分支**

```bash
git -C /opt/crypto-wiki-private.git branch
# 预期输出：main
```

---

## Task 2：添加环境变量

**Files:**
- Modify: `.env`

- [ ] **Step 1: 追加变量到 `.env`**

在 `.env` 文件末尾添加：
```
# Wiki → Obsidian Sync
WIKI_BARE_REPO=/opt/crypto-wiki-private.git
WIKI_WORKING_DIR=/root/.wiki-cache/crypto-wiki-private
```

> 注意：`WIKI_WORKING_DIR` 路径取决于 VPS 用户，若非 root 则改为 `/home/<user>/.wiki-cache/crypto-wiki-private`

- [ ] **Step 2: 确认 `.env` 不进 git（已在 .gitignore 中）**

```bash
git status
# .env 不应出现在 untracked files 中
```

---

## Task 3：实现 `src/wiki_sync.py`（TDD）

**Files:**
- Create: `test/test_wiki_sync.py`
- Create: `src/wiki_sync.py`

### 3a：`sync_files` — 文件复制，返回变更列表

- [ ] **Step 1: 写失败测试**

新建 `test/test_wiki_sync.py`：

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import tempfile, pathlib, shutil
from unittest.mock import patch, MagicMock

from wiki_sync import sync_files


def test_sync_files_copies_new_file():
    with tempfile.TemporaryDirectory() as src_tmp, \
         tempfile.TemporaryDirectory() as dst_tmp:
        src_dir = pathlib.Path(src_tmp)
        dst_projects = pathlib.Path(dst_tmp) / "projects"
        dst_projects.mkdir()

        (src_dir / "BTC.md").write_text("# BTC content")
        changed = sync_files(src_dir, pathlib.Path(dst_tmp))

        assert "BTC" in changed
        assert (dst_projects / "BTC.md").read_text() == "# BTC content"


def test_sync_files_skips_unchanged_file():
    with tempfile.TemporaryDirectory() as src_tmp, \
         tempfile.TemporaryDirectory() as dst_tmp:
        src_dir = pathlib.Path(src_tmp)
        dst_projects = pathlib.Path(dst_tmp) / "projects"
        dst_projects.mkdir()

        content = "# BTC content"
        (src_dir / "BTC.md").write_text(content)
        (dst_projects / "BTC.md").write_text(content)

        changed = sync_files(src_dir, pathlib.Path(dst_tmp))
        assert changed == []


def test_sync_files_detects_updated_content():
    with tempfile.TemporaryDirectory() as src_tmp, \
         tempfile.TemporaryDirectory() as dst_tmp:
        src_dir = pathlib.Path(src_tmp)
        dst_projects = pathlib.Path(dst_tmp) / "projects"
        dst_projects.mkdir()

        (src_dir / "BTC.md").write_text("# BTC new content")
        (dst_projects / "BTC.md").write_text("# BTC old content")

        changed = sync_files(src_dir, pathlib.Path(dst_tmp))
        assert "BTC" in changed


def test_sync_files_returns_empty_when_no_wiki_files():
    with tempfile.TemporaryDirectory() as src_tmp, \
         tempfile.TemporaryDirectory() as dst_tmp:
        changed = sync_files(pathlib.Path(src_tmp), pathlib.Path(dst_tmp))
        assert changed == []
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd /path/to/web3-news-push && python -m pytest test/test_wiki_sync.py -v
# 预期：ImportError — wiki_sync 不存在
```

- [ ] **Step 3: 实现 `src/wiki_sync.py`（仅 sync_files）**

新建 `src/wiki_sync.py`：

```python
import logging
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

logger = logging.getLogger(__name__)

WIKI_DIR = Path(__file__).parent.parent / "wiki" / "projects"
WORKING_DIR = Path(os.environ.get("WIKI_WORKING_DIR", str(Path.home() / ".wiki-cache/crypto-wiki-private")))
BARE_REPO = os.environ.get("WIKI_BARE_REPO", "/opt/crypto-wiki-private.git")


def sync_files(wiki_dir: Path, working_dir: Path) -> list[str]:
    """Copy changed .md files to working_dir/projects/. Returns stem names of changed files."""
    projects_dst = working_dir / "projects"
    projects_dst.mkdir(parents=True, exist_ok=True)

    changed = []
    for src in sorted(wiki_dir.glob("*.md")):
        dst = projects_dst / src.name
        new_content = src.read_text(encoding="utf-8")
        if not dst.exists() or dst.read_text(encoding="utf-8") != new_content:
            shutil.copy2(src, dst)
            changed.append(src.stem)
    return changed
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
python -m pytest test/test_wiki_sync.py::test_sync_files_copies_new_file \
                 test/test_wiki_sync.py::test_sync_files_skips_unchanged_file \
                 test/test_wiki_sync.py::test_sync_files_detects_updated_content \
                 test/test_wiki_sync.py::test_sync_files_returns_empty_when_no_wiki_files -v
# 预期：4 passed
```

### 3b：`ensure_clone` — 首次克隆检测

- [ ] **Step 5: 追加 ensure_clone 测试**

在 `test/test_wiki_sync.py` 末尾追加：

```python
from wiki_sync import ensure_clone


def test_ensure_clone_skips_if_already_cloned():
    with tempfile.TemporaryDirectory() as tmpdir:
        working_dir = pathlib.Path(tmpdir)
        (working_dir / ".git").mkdir()  # simulate existing clone

        with patch("subprocess.run") as mock_run:
            ensure_clone("/opt/crypto-wiki-private.git", working_dir)
            mock_run.assert_not_called()


def test_ensure_clone_runs_git_clone_if_missing():
    with tempfile.TemporaryDirectory() as tmpdir:
        working_dir = pathlib.Path(tmpdir) / "new-clone"  # does not exist

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            ensure_clone("/opt/crypto-wiki-private.git", working_dir)
            args = mock_run.call_args[0][0]
            assert args[0] == "git"
            assert "clone" in args
```

- [ ] **Step 6: 运行测试，确认失败**

```bash
python -m pytest test/test_wiki_sync.py::test_ensure_clone_skips_if_already_cloned \
                 test/test_wiki_sync.py::test_ensure_clone_runs_git_clone_if_missing -v
# 预期：ImportError or AttributeError — ensure_clone 未定义
```

- [ ] **Step 7: 在 `src/wiki_sync.py` 追加 ensure_clone**

在 `sync_files` 函数后追加：

```python
def ensure_clone(bare_repo: str, working_dir: Path) -> None:
    """Clone bare_repo into working_dir if not already cloned."""
    if (working_dir / ".git").exists():
        return
    working_dir.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", bare_repo, str(working_dir)], check=True)
```

- [ ] **Step 8: 运行测试，确认通过**

```bash
python -m pytest test/test_wiki_sync.py::test_ensure_clone_skips_if_already_cloned \
                 test/test_wiki_sync.py::test_ensure_clone_runs_git_clone_if_missing -v
# 预期：2 passed
```

### 3c：`commit_and_push` — git commit + push

- [ ] **Step 9: 追加 commit_and_push 测试**

在 `test/test_wiki_sync.py` 末尾追加：

```python
from wiki_sync import commit_and_push


def test_commit_and_push_returns_false_when_nothing_to_commit():
    with tempfile.TemporaryDirectory() as tmpdir:
        working_dir = pathlib.Path(tmpdir)

        def fake_run(cmd, **kwargs):
            mock = MagicMock()
            if "--cached" in cmd and "--quiet" in cmd:
                mock.returncode = 0  # nothing staged
            else:
                mock.returncode = 0
            return mock

        with patch("subprocess.run", side_effect=fake_run):
            result = commit_and_push(working_dir)
            assert result is False


def test_commit_and_push_returns_true_when_changes_exist():
    with tempfile.TemporaryDirectory() as tmpdir:
        working_dir = pathlib.Path(tmpdir)

        def fake_run(cmd, **kwargs):
            mock = MagicMock()
            if "--cached" in cmd and "--quiet" in cmd:
                mock.returncode = 1  # changes staged
            else:
                mock.returncode = 0
            return mock

        with patch("subprocess.run", side_effect=fake_run):
            result = commit_and_push(working_dir)
            assert result is True
```

- [ ] **Step 10: 运行测试，确认失败**

```bash
python -m pytest test/test_wiki_sync.py::test_commit_and_push_returns_false_when_nothing_to_commit \
                 test/test_wiki_sync.py::test_commit_and_push_returns_true_when_changes_exist -v
# 预期：ImportError or AttributeError
```

- [ ] **Step 11: 在 `src/wiki_sync.py` 追加 commit_and_push**

```python
def commit_and_push(working_dir: Path) -> bool:
    """Stage all, commit, push. Returns True if a commit was made."""
    cwd = str(working_dir)
    subprocess.run(["git", "-C", cwd, "add", "."], check=True)
    result = subprocess.run(["git", "-C", cwd, "diff", "--cached", "--quiet"])
    if result.returncode == 0:
        return False  # nothing staged
    date_str = datetime.now().strftime("%Y-%m-%d")
    subprocess.run(
        ["git", "-C", cwd, "commit", "-m", f"wiki: auto-update {date_str}"],
        check=True,
    )
    subprocess.run(["git", "-C", cwd, "push", "origin", "main"], check=True)
    return True
```

- [ ] **Step 12: 运行测试，确认通过**

```bash
python -m pytest test/test_wiki_sync.py::test_commit_and_push_returns_false_when_nothing_to_commit \
                 test/test_wiki_sync.py::test_commit_and_push_returns_true_when_changes_exist -v
# 预期：2 passed
```

### 3d：`send_notification` — Telegram 通知

- [ ] **Step 13: 追加 send_notification 测试**

在 `test/test_wiki_sync.py` 末尾追加：

```python
from wiki_sync import send_notification


def test_send_notification_posts_to_telegram():
    with patch("httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True}
        mock_post.return_value = mock_resp

        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "test-token",
            "TELEGRAM_ADMIN_CHAT_ID": "123456",
        }):
            send_notification(["BTC", "ARB", "FET"])

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        body = call_kwargs["json"]
        assert body["chat_id"] == "123456"
        assert "BTC" in body["text"]
        assert "3" in body["text"]


def test_send_notification_skips_when_token_missing():
    with patch("httpx.post") as mock_post:
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("TELEGRAM_BOT_TOKEN", None)
            send_notification(["BTC"])
        mock_post.assert_not_called()
```

- [ ] **Step 14: 运行测试，确认失败**

```bash
python -m pytest test/test_wiki_sync.py::test_send_notification_posts_to_telegram \
                 test/test_wiki_sync.py::test_send_notification_skips_when_token_missing -v
# 预期：ImportError or AttributeError
```

- [ ] **Step 15: 在 `src/wiki_sync.py` 追加 send_notification**

```python
def send_notification(changed: list[str]) -> None:
    """Send Telegram message listing changed projects. No-op if env vars missing."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    admin_chat_id = os.environ.get("TELEGRAM_ADMIN_CHAT_ID", "")
    if not bot_token or not admin_chat_id:
        logger.warning("TELEGRAM_BOT_TOKEN or TELEGRAM_ADMIN_CHAT_ID not set — notification skipped")
        return

    import httpx

    names = ", ".join(changed[:5])
    if len(changed) > 5:
        names += f" 等{len(changed)}个"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    text = f"✅ Wiki 已同步 | 更新 {len(changed)} 个项目文件（{names}）| {now}"

    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": admin_chat_id, "text": text, "parse_mode": "Markdown"}
        resp = httpx.post(url, json=payload, timeout=15)
        if resp.status_code != 200 or not resp.json().get("ok"):
            payload.pop("parse_mode")
            httpx.post(url, json=payload, timeout=15)
    except Exception as e:
        logger.warning(f"Failed to send wiki sync notification: {e}")
```

- [ ] **Step 16: 运行测试，确认通过**

```bash
python -m pytest test/test_wiki_sync.py::test_send_notification_posts_to_telegram \
                 test/test_wiki_sync.py::test_send_notification_skips_when_token_missing -v
# 预期：2 passed
```

### 3e：`main` — 串联主流程

- [ ] **Step 17: 追加 main 集成测试**

在 `test/test_wiki_sync.py` 末尾追加：

```python
import wiki_sync
from wiki_sync import main


def test_main_skips_when_no_wiki_files(tmp_path):
    with patch.object(wiki_sync, "WIKI_DIR", tmp_path), \
         patch.object(wiki_sync, "WORKING_DIR", tmp_path / "working"), \
         patch.object(wiki_sync, "BARE_REPO", "/opt/crypto-wiki-private.git"), \
         patch("wiki_sync.ensure_clone") as mock_clone, \
         patch("wiki_sync.send_notification") as mock_notify:
        main()
        mock_clone.assert_not_called()
        mock_notify.assert_not_called()


def test_main_calls_full_pipeline_when_files_exist(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "BTC.md").write_text("# BTC")

    with patch.object(wiki_sync, "WIKI_DIR", wiki_dir), \
         patch.object(wiki_sync, "WORKING_DIR", tmp_path / "working"), \
         patch.object(wiki_sync, "BARE_REPO", "/opt/crypto-wiki-private.git"), \
         patch("wiki_sync.ensure_clone") as mock_clone, \
         patch("wiki_sync.sync_files", return_value=["BTC"]) as mock_sync, \
         patch("wiki_sync.commit_and_push", return_value=True) as mock_push, \
         patch("wiki_sync.send_notification") as mock_notify:
        main()
        mock_clone.assert_called_once()
        mock_sync.assert_called_once()
        mock_push.assert_called_once()
        mock_notify.assert_called_once_with(["BTC"])


def test_main_skips_notification_when_nothing_committed(tmp_path):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "BTC.md").write_text("# BTC")

    with patch.object(wiki_sync, "WIKI_DIR", wiki_dir), \
         patch.object(wiki_sync, "WORKING_DIR", tmp_path / "working"), \
         patch.object(wiki_sync, "BARE_REPO", "/opt/crypto-wiki-private.git"), \
         patch("wiki_sync.ensure_clone"), \
         patch("wiki_sync.sync_files", return_value=["BTC"]), \
         patch("wiki_sync.commit_and_push", return_value=False), \
         patch("wiki_sync.send_notification") as mock_notify:
        main()
        mock_notify.assert_not_called()
```

- [ ] **Step 18: 运行测试，确认失败**

```bash
python -m pytest test/test_wiki_sync.py::test_main_skips_when_no_wiki_files \
                 test/test_wiki_sync.py::test_main_calls_full_pipeline_when_files_exist \
                 test/test_wiki_sync.py::test_main_skips_notification_when_nothing_committed -v
# 预期：ImportError or AttributeError — main 未定义
```

- [ ] **Step 19: 在 `src/wiki_sync.py` 追加 main**

```python
def main() -> None:
    if not WIKI_DIR.exists() or not list(WIKI_DIR.glob("*.md")):
        logger.info("No wiki files to sync — skipping")
        return

    ensure_clone(BARE_REPO, WORKING_DIR)
    changed = sync_files(WIKI_DIR, WORKING_DIR)

    if not changed:
        logger.info("No wiki changes detected — skipping commit")
        return

    pushed = commit_and_push(WORKING_DIR)
    if pushed:
        send_notification(changed)
        logger.info(f"Wiki synced: {changed}")
    else:
        logger.info("Nothing committed after sync")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
```

- [ ] **Step 20: 运行全部测试**

```bash
python -m pytest test/test_wiki_sync.py -v
# 预期：全部 passed（约 13 个测试）
```

- [ ] **Step 21: 提交**

```bash
git add src/wiki_sync.py test/test_wiki_sync.py
git commit -m "feat: add wiki_sync — commit wiki files to bare repo + Telegram notify"
```

---

## Task 4：更新 `openclaw-cron.yaml`

**Files:**
- Modify: `openclaw-cron.yaml`

- [ ] **Step 1: 在 `openclaw-cron.yaml` 追加 wiki_sync 调度**

在现有 `cron:` 列表末尾追加（注意 YAML 缩进与现有条目一致）：

```yaml
  - schedule: "0 22 * * *"
    task: "cd /path/to/web3-news-push && /usr/bin/python3 src/wiki_sync.py"
    label: "wiki-obsidian-sync"
    runtime: "subagent"
    agentId: "wiki-sync"
    timeoutSeconds: 120
    cleanup: "keep"
```

> 将 `/path/to/web3-news-push` 替换为 VPS 上实际项目路径（与现有 `web3-news-push` 条目一致）。

- [ ] **Step 2: 验证 YAML 语法**

```bash
python -c "import yaml; yaml.safe_load(open('openclaw-cron.yaml'))" && echo "YAML OK"
# 预期：YAML OK
```

- [ ] **Step 3: 提交**

```bash
git add openclaw-cron.yaml
git commit -m "chore: schedule wiki_sync daily at 22:00 UTC"
```

---

## Task 5：Mac 侧一次性配置（手动操作）

**Files:** 无（Obsidian 插件配置）

- [ ] **Step 1: 在 Obsidian 安装 Git 社区插件**

Obsidian → Settings → Community plugins → Browse → 搜索 "Obsidian Git" → Install → Enable

- [ ] **Step 2: 在 vault 内创建落点目录并 clone**

```bash
mkdir -p ~/path/to/vault/Web3/Project_Tracking
cd ~/path/to/vault/Web3/Project_Tracking
git clone user@vps-ip:/opt/crypto-wiki-private.git .
```

> 确保 Mac 的 SSH 公钥已加入 VPS `~/.ssh/authorized_keys`

- [ ] **Step 3: 配置 Obsidian Git 插件**

Settings → Obsidian Git：
- **Vault root** 指向 `Web3/Project_Tracking/`（插件 Custom base path 设为此路径）
- **Auto pull interval (minutes):** 30
- **Pull on startup:** 开启

- [ ] **Step 4: 手动触发一次 pull 验证**

Obsidian Command Palette → `Obsidian Git: Pull` → 确认 `Web3/Project_Tracking/projects/` 下出现 `.md` 文件

---

## Task 6：端到端验证（VPS）

- [ ] **Step 1: 确保 `.env` 变量正确**

```bash
grep WIKI /path/to/web3-news-push/.env
# 预期：WIKI_BARE_REPO=/opt/crypto-wiki-private.git
#       WIKI_WORKING_DIR=/root/.wiki-cache/crypto-wiki-private（或对应路径）
```

- [ ] **Step 2: 手动触发 wiki_sync 一次**

```bash
cd /path/to/web3-news-push
python src/wiki_sync.py
# 预期 log：Wiki synced: ['BTC', 'ARB', ...]
# 预期：Telegram 收到通知
```

- [ ] **Step 3: 确认文件已推送到 bare repo**

```bash
git -C /opt/crypto-wiki-private.git log --oneline -3
# 预期：最新 commit 为 "wiki: auto-update YYYY-MM-DD"
```

- [ ] **Step 4: 在 Mac 触发 Obsidian Git pull，确认文件同步**

Obsidian Command Palette → `Obsidian Git: Pull` → 查看 `Web3/Project_Tracking/projects/BTC.md` 是否更新

- [ ] **Step 5: 运行完整测试套件，确认无回归**

```bash
python -m pytest test/ -v
# 预期：全部 passed
```
