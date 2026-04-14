# Telegram KOL 抓取配置指南

## 第一步：获取 Telegram API 凭证

### 1. 访问 https://my.telegram.org

### 2. 登录你的 Telegram 账号
- 输入手机号（国际格式，如 `+86 138 0013 8000`）
- 输入收到的验证码

### 3. 进入 API Development Tools
- 点击 "API development tools"

### 4. 创建应用
填写表单：
- **App title**: `Web3 News Scraper`（随便填）
- **Short name**: `web3news`（随便填）
- **Platform**: 选择 `Desktop`
- **Description**: （可选）

点击 **Create application**

### 5. 复制凭证
创建成功后会显示：
- **api_id**: 一串数字（如 `12345678`）
- **api_hash**: 一串字符串（如 `a1b2c3d4e5f6...`）

**⚠️ 重要**: 保管好这些凭证，不要泄露！

---

## 第二步：配置环境变量

编辑 `.env` 文件，添加：

```bash
# Telegram API 凭证（从 my.telegram.org 获取）
TELEGRAM_API_ID=12345678                          # 你的 api_id（纯数字）
TELEGRAM_API_HASH=a1b2c3d4e5f6g7h8i9j0k1l2m3n4    # 你的 api_hash
TELEGRAM_PHONE=+8613800138000                     # 你的手机号（国际格式，带 +）

# Telegram 抓取配置（可选）
TELEGRAM_FOLDER_ID=Z2Y4z_t47LlhZTdl               # 你的 Telegram folder ID（可选）
TELEGRAM_MAX_MESSAGES_PER_CHANNEL=10              # 每个频道最多抓取消息数（默认 10）
TELEGRAM_HOURS_BACK=24                            # 抓取多少小时内的消息（默认 24）
```

---

## 第三步：首次登录认证

第一次运行时，需要手动输入验证码：

```bash
cd /Users/limohan/code_projects/web3/web3-news-push
python3 src/telegram_auth.py
```

**交互流程**:
1. 脚本会发送验证码到你的 Telegram
2. 输入收到的验证码
3. 如果启用了两步验证，输入密码
4. 认证成功后，会话保存到 `./sessions/telegram.session`

**后续运行**: 会话会自动复用，不需要重复输入验证码。

---

## 第四步：测试 Telegram 抓取

### 测试单独模块

```bash
# 测试认证
python3 src/telegram_auth.py

# 测试抓取（需要先完成认证）
python3 -c "
import asyncio
from src.telegram_scraper import scrape_telegram_sources
messages = asyncio.run(scrape_telegram_sources())
print(f'抓取到 {len(messages)} 条消息')
"

# 测试过滤
python3 -c "
from src.telegram_filter import filter_crypto_messages
test_msgs = [
    {'title': 'BTC突破10万', 'content': '比特币价格...', 'url': 'https://...'},
    {'title': '今天天气不错', 'content': '阳光明媚', 'url': 'https://...'}
]
filtered = filter_crypto_messages(test_msgs)
print(f'过滤结果: {len(filtered)} 条加密货币相关')
"
```

### 测试完整流程

```bash
# 干跑测试（不发送到 Telegram）
python3 src/main.py --dry-run --max-articles 5

# 如果一切正常，会看到:
# ✅ Added X Telegram messages
```

---

## Telegram Folder ID 说明

你提供的链接: `https://t.me/addlist/Z2Y4z_t47LlhZTdl`

- **Folder ID**: `Z2Y4z_t47LlhZTdl`
- 这个 ID 代表一个 Telegram 文件夹（包含多个频道）
- 配置后，脚本会自动抓取该文件夹内所有频道的消息

**如果不配置 Folder ID**:
- 脚本会抓取你订阅的所有公开频道
- 可以在 `telegram_scraper.py` 中手动配置频道列表

---

## 故障排除

### 错误: `TELEGRAM_API_ID not found`
→ 检查 `.env` 文件是否正确配置

### 错误: `Session expired`
→ 删除 `./sessions/telegram.session`，重新运行 `telegram_auth.py`

### 错误: `FloodWaitError`
→ Telegram API 限流，等待几分钟后重试

### 没有抓取到消息
→ 检查:
1. 频道是否公开（私有频道需要先加入）
2. 时间范围是否太短（默认 24 小时）
3. 消息是否太短（<50 字符会被过滤）

---

## 安全提示

- ⚠️ **不要泄露 API 凭证**: `api_id` 和 `api_hash` 是敏感信息
- ⚠️ **不要提交到 Git**: 确保 `.env` 在 `.gitignore` 中
- ⚠️ **会话文件安全**: `sessions/telegram.session` 包含登录状态，不要分享

---

## 进阶配置

### 自定义频道列表

如果不想用 Folder ID，可以手动配置频道：

编辑 `src/telegram_scraper.py`:

```python
DEFAULT_CHANNELS = [
    "crypto_news_channel",      # 频道用户名（不带 @）
    "bitcoin_updates",
    "defi_alpha",
    "1234567890"                # 或者使用频道 ID（数字）
]
```

### 调整过滤关键词

编辑 `src/telegram_filter.py`:

```python
KEYWORDS_CN = [
    '比特币', 'ETH', '加密货币',
    '你的自定义关键词',  # 添加更多
]
```

---

完成配置后，运行 `python3 src/main.py --dry-run` 测试完整流程！
