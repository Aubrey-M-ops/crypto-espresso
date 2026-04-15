# 测试命令

```bash
# 只发 KOL，不去重（发全部）
python src/main.py --kol-only --no-dedup

# 只发 KOL，正常去重
python src/main.py --kol-only

# 完整推送但跳过去重
python src/main.py --no-dedup

# 加 --dry-run 预览不发送
python src/main.py --kol-only --no-dedup --dry-run
```
