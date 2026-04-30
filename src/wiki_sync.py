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


def ensure_clone(bare_repo: str, working_dir: Path) -> None:
    """Clone bare_repo into working_dir if not already cloned."""
    if (working_dir / ".git").exists():
        return
    working_dir.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", bare_repo, str(working_dir)], check=True)


def commit_and_push(working_dir: Path) -> bool:
    """Stage all, commit, push. Returns True if a commit was made."""
    cwd = str(working_dir)
    subprocess.run(["git", "-C", cwd, "pull", "--rebase", "origin", "main"], check=True)
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
