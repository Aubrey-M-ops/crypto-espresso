# 部署指南

## 模块说明

| 文件 | 功能 |
|------|------|
| `src/scraper.py` | RSS 抓取（4 个新闻源） |
| `src/dedup.py` | SQLite 去重（7 天窗口） |
| `src/summarizer.py` | Claude API 摘要生成 |
| `src/classifier.py` | 文章分类（必读 / 进阶） |
| `src/digest.py` | Telegram 消息格式化 |
| `src/main.py` | 主入口编排 |
| `run.sh` | Cron 调用入口，负责加载 `.env` 和写日志 |

---

## 部署步骤

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`：

```bash
ANTHROPIC_API_KEY=sk-ant-...        # Claude API Key
TELEGRAM_BOT_TOKEN=...              # Telegram Bot Token
TELEGRAM_CHANNEL_ID=@your_channel   # 频道 ID 或 @username
TELEGRAM_API_ID=...                 # Telegram App ID（来自 my.telegram.org，KOL 抓取用）
TELEGRAM_API_HASH=...               # Telegram App Hash（KOL 抓取用）
```

### 3. 干跑测试（不发送到 Telegram）

```bash
python src/main.py --dry-run --max-articles 3 --verbose
```

### 4. 真实运行（单次）

```bash
bash run.sh
```

### 5. 安装系统 Cron（每天 08:00 和 17:00）

```bash
chmod +x run.sh
(crontab -l 2>/dev/null; echo "0 8,17 * * * $(pwd)/run.sh") | crontab -
```

验证已安装：

```bash
crontab -l
```

---

## 验证

### 检查 Cron 是否注册

```bash
crontab -l
# 应看到：0 8,17 * * * .../run.sh
```

### 手动触发一次（完整流程）

```bash
bash run.sh
```

### 查看当天日志

```bash
tail -f logs/cron_$(date +%Y%m%d).log
```

### 确认消息已发出

打开你的 Telegram 频道，检查是否有新消息。

### 检查去重数据库

```bash
sqlite3 db/articles.db "SELECT title, timestamp FROM seen_articles ORDER BY timestamp DESC LIMIT 10;"
```

---

## 故障排除

### 脚本没有执行

```bash
# 检查 crontab
crontab -l

# 检查 run.sh 是否可执行
ls -l run.sh

# 手动执行确认无报错
bash run.sh
```

### Telegram 发送失败

```bash
# 检查 Bot 是否已加入频道并具有发送权限
# 在 Telegram 中：频道设置 → 管理员 → 确认 Bot 在列表中

# 检查环境变量是否正确加载
grep TELEGRAM .env
```

### API Key 不工作

```bash
source .env
echo $ANTHROPIC_API_KEY
```

---

## 成本参考

- **Claude API**：约 $0.05–0.10 / 次（处理 5–10 篇文章）
- **每天两次推送**：约 $0.10–0.20 / 天
- **无服务器费用**：本地 cron 运行，不需要 VPS
