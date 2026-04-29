#!/usr/bin/env python3
"""
Wiki 生成器集成测试

用一条包含项目提及的硬编码 KOL 消息，走完完整链路：
  Claude AI 解读 → 提取 projects → 生成 wiki/projects/*.md

运行方式:
    make test-wiki
    # 或
    python test/test_wiki_generator.py

需要:
  - ANTHROPIC_API_KEY（实际调用 Claude API）
  - 不需要 Telegram 或 Supabase
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

SAMPLE_CHANNEL = "TestKOL"
SAMPLE_MESSAGE = """\
$FET 现在是 AI + Web3 赛道里最纯正的标的，Fetch.ai 的去中心化 AI Agent 网络已经跑起来了，
生态进展比市场预期快得多。我在 0.38 建仓，目前拿着不动。

$ARB 短期面临解锁压力，但 Arbitrum 的 TVL 和活跃地址数都在稳步增长，
如果大盘不崩，Q2 底部就是好的入场机会，风险可控。

Bitcoin 整体在积累区间，宏观不确定性还高，建议仓位保守，
不要 All-in，等更多确认信号。
"""


def check_env() -> bool:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        print("❌ ANTHROPIC_API_KEY 未配置，请在 .env 中设置")
        return False
    print(f"✅ ANTHROPIC_API_KEY 已配置 ({key[:8]}...)")
    return True


def main() -> int:
    print("=" * 60)
    print("KOL Wiki 生成器集成测试")
    print("=" * 60)

    if not check_env():
        return 1

    from summarizer import SummarizerClient
    from kol_tracker import save_project_mentions

    wiki_dir = Path(__file__).resolve().parent.parent / "wiki" / "projects"
    wiki_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n📨 KOL 频道：@{SAMPLE_CHANNEL}")
    print(f"📝 消息内容（前 100 字）：{SAMPLE_MESSAGE[:100].strip()}...\n")

    # Step 1: AI 解读
    print("🤖 Step 1/3: Claude AI 解读中...")
    client = SummarizerClient()
    try:
        result = client.summarize_kol(channel=SAMPLE_CHANNEL, content=SAMPLE_MESSAGE)
    except Exception as e:
        print(f"❌ AI 解读失败: {e}")
        return 1

    print(f"   💬 摘要: {result.plain_summary}")
    if result.projects:
        print(f"   🔍 提取到 {len(result.projects)} 个项目:")
        for p in result.projects:
            print(f"      - {p.project_name} ({p.sentiment}): {p.context[:50]}")
    else:
        print("   ⚠️  未提取到任何项目，可能需要调整 prompt 或消息内容")
        return 1

    # Step 2: 生成 wiki
    print("\n📝 Step 2/3: 生成 wiki 文件...")
    from datetime import datetime
    mention_date = datetime.now().strftime("%Y-%m-%d")

    save_project_mentions(
        kol_name=SAMPLE_CHANNEL,
        mention_date=mention_date,
        projects=result.projects,
        wiki_dir=wiki_dir,
    )

    # Step 3: 打印结果
    print("\n📄 Step 3/3: 生成的 wiki 文件内容：")
    print("=" * 60)
    for p in result.projects:
        safe_name = p.project_name.replace(" ", "_")
        wiki_file = wiki_dir / f"{safe_name}.md"
        if wiki_file.exists():
            print(f"\n── {wiki_file.relative_to(Path(__file__).resolve().parent.parent)} ──")
            print(wiki_file.read_text(encoding="utf-8"))
        else:
            print(f"⚠️  未找到 wiki 文件: {wiki_file}")

    print("=" * 60)
    print(f"✅ 测试完成！Wiki 已写入 wiki/projects/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
