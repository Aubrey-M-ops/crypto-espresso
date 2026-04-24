#!/usr/bin/env python3
"""
KOL Setup Script

One-time setup that:
1. Authenticates with Telegram (saves session for future use)
2. Resolves a Telegram folder invite link (t.me/addlist/...)
3. Lists all channels in the folder
4. Updates TELEGRAM_CHANNELS in .env
"""

import asyncio
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

sys.path.insert(0, str(Path(__file__).parent))
from telegram_auth import TelegramAuth


def extract_slug(url: str) -> str:
    """Extract slug from t.me/addlist/<slug> URL."""
    match = re.search(r't\.me/addlist/([A-Za-z0-9_-]+)', url)
    if not match:
        raise ValueError(f"Invalid folder invite URL: {url}")
    return match.group(1)


def update_env_channels(channels: list[str]):
    """Write TELEGRAM_CHANNELS into .env file."""
    env_path = ROOT / ".env"
    content = env_path.read_text(encoding="utf-8")
    value = ",".join(channels)
    # Replace existing TELEGRAM_CHANNELS= line
    if re.search(r'^TELEGRAM_CHANNELS=.*$', content, flags=re.MULTILINE):
        content = re.sub(
            r'^TELEGRAM_CHANNELS=.*$',
            f'TELEGRAM_CHANNELS={value}',
            content,
            flags=re.MULTILINE
        )
    else:
        content += f'\nTELEGRAM_CHANNELS={value}\n'
    env_path.write_text(content, encoding="utf-8")
    print(f"\n✅ .env 已更新: TELEGRAM_CHANNELS={value}")


async def main():
    folder_url = None

    # Accept URL as CLI argument or prompt
    if len(sys.argv) > 1:
        folder_url = sys.argv[1]
    else:
        folder_url = input("\n请输入 Telegram 文件夹邀请链接 (t.me/addlist/...): ").strip()

    try:
        slug = extract_slug(folder_url)
    except ValueError as e:
        print(f"❌ {e}")
        return 1

    print(f"\n📁 文件夹 slug: {slug}")
    print("🔐 正在连接 Telegram（首次需要输入验证码）...\n")

    auth = TelegramAuth(interactive=True)
    try:
        client = await auth.get_client()
    except Exception as e:
        print(f"❌ 认证失败: {e}")
        return 1

    print("\n✅ 已登录 Telegram\n")
    print(f"🔍 正在解析文件夹链接...\n")

    try:
        from telethon.tl.functions.chatlists import CheckChatlistInviteRequest
        result = await client(CheckChatlistInviteRequest(slug=slug))
    except Exception as e:
        print(f"❌ 无法解析文件夹: {e}")
        await auth.disconnect()
        return 1

    chats = result.chats
    if not chats:
        print("⚠️  文件夹里没有频道")
        await auth.disconnect()
        return 0

    print(f"📋 文件夹包含 {len(chats)} 个频道/群组:\n")
    channels = []
    for chat in chats:
        name = getattr(chat, 'title', '?')
        username = getattr(chat, 'username', None)
        chat_id = getattr(chat, 'id', None)

        if username:
            handle = username
            display = f"@{username}"
        else:
            # Use numeric ID for private channels (no username)
            handle = str(chat_id)
            display = f"(私有频道, id={chat_id})"

        channels.append(handle)
        print(f"  • {name} {display}")

    print()
    confirm = input(f"将以上 {len(channels)} 个频道写入 .env 的 TELEGRAM_CHANNELS？[y/N] ").strip().lower()
    if confirm == 'y':
        update_env_channels(channels)
    else:
        value = ",".join(channels)
        print(f"\n未写入。你可以手动添加到 .env:\n  TELEGRAM_CHANNELS={value}")

    await auth.disconnect()
    return 0


if __name__ == "__main__":
    code = asyncio.run(main())
    sys.exit(code)
