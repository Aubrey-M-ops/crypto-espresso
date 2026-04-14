# 部署指南

## 当前状态

✅ **代码已完成** - 所有核心模块已实现
- `src/scraper.py` - RSS 抓取（4 个新闻源）
- `src/dedup.py` - SQLite 去重（7 天窗口）
- `src/summarizer.py` - Claude API 摘要生成
- `src/classifier.py` - 文章分类（必读/进阶）
- `src/digest.py` - Telegram 消息格式化
- `src/main.py` - 主入口编排

❌ **待完成**:
1. 安装依赖
2. 配置环境变量
3. 测试运行
4. 部署到 OpenClaw cron

---

## 部署步骤

### 1. 安装依赖

```bash
cd /Users/limohan/code_projects/web3/web3-news-push
pip3 install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 填入:
```bash
TELEGRAM_CHANNEL_ID=-1001234567890    # 从 @userinfobot 获取
ANTHROPIC_API_KEY=sk-ant-...          # Claude API key
```

### 3. 测试导入

```bash
python3 test_import.py
```

### 4. 干跑测试（不发送到 Telegram）

```bash
python3 src/main.py --dry-run --max-articles 3 --verbose
```

### 5. 真实运行（单次）

```bash
python3 src/main.py --max-articles 5
```

### 6. 部署到 OpenClaw Cron

编辑 `~/.openclaw/config.yaml`:

```yaml
cron:
  - schedule: "0 8 * * *"  # 每天早上 8:00
    task: "cd /Users/limohan/code_projects/web3/web3-news-push && /usr/bin/python3 src/main.py"
    runtime: "subagent"
    agentId: "main"
    timeoutSeconds: 600
    cleanup: "keep"
```

重启 OpenClaw:
```bash
openclaw gateway restart
```

---

## 验证部署

### 查看 cron 日志
```bash
tail -f ~/.openclaw/logs/cron.log | grep "web3-news"
```

### 手动触发测试
```bash
cd /Users/limohan/code_projects/web3/web3-news-push
python3 src/main.py --dry-run
```

### 检查数据库
```bash
sqlite3 db/articles.db "SELECT COUNT(*) FROM seen_articles;"
```

---

## 故障排除

### 依赖安装失败
```bash
# 升级 pip
pip3 install --upgrade pip

# 逐个安装
pip3 install feedparser httpx anthropic python-dotenv
```

### API Key 不工作
```bash
# 验证环境变量
source .env
echo $ANTHROPIC_API_KEY
```

### Telegram 发送失败
```bash
# 测试 OpenClaw message tool
openclaw message send --channel telegram --target $TELEGRAM_CHANNEL_ID --message "测试"
```

---

## 成本估算

- **Claude API**: ~$0.05-0.10 / 天
  - 假设处理 5-10 篇文章
  - 每篇 ~1k tokens input + ~500 tokens output
  - Sonnet-4-5: $3/M input, $15/M output
  - 计算: (10 * 1000 * 3 + 10 * 500 * 15) / 1,000,000 ≈ $0.10

- **无额外服务器成本** - 运行在本地 OpenClaw 实例

---

## 下一步优化

- [ ] 添加单元测试（`tests/`目录）
- [ ] 错误通知（失败时发 Telegram 告警）
- [ ] 用户订阅管理（允许加入/退出）
- [ ] 多语言支持（英文摘要）
- [ ] Web 仪表盘（查看历史摘要）
