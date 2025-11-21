# Stock Bot

Automated stock screening bot that monitors [Chartink.com](https://chartink.com) for Indian stocks matching custom criteria and sends real-time notifications via Discord and/or Telegram.

## Features

- 🔍 **Automated Scanning** - Runs custom Chartink scans on a schedule
- 🔔 **Multi-Platform Notifications** - Discord and/or Telegram alerts (toggle either or both)
- 💾 **Persistent Tracking** - Remembers seen stocks to avoid duplicates
- 🌐 **Browser Automation** - Selenium-based web scraping
- ⚡ **Context Manager Support** - Automatic resource cleanup
- 📅 **Weekend Skip** - Automatically pauses on Saturdays and Sundays
- 🔄 **Daily Reset** - Clears seen stocks after market close
- 🎯 **Multi-Scan Support** - Run up to 3 independent scans simultaneously

## Setup

### Prerequisites

- Python 3.8+
- Microsoft Edge browser
- Edge WebDriver (included in `drivers/` folder)

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd Stock_Bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root:
```env
CHARTINK_EMAIL=your_email@example.com
CHARTINK_PASSWORD=your_password

# Notification Platform Toggles (enable at least one)
ENABLE_DISCORD=true
ENABLE_TELEGRAM=false

# Discord Configuration
DISCORD_WEBHOOK=https://discord.com/api/webhooks/your-webhook-url
PING_HERE=true

# Telegram Configuration (optional)
TELEGRAM_BOT_TOKEN=123456789:YOUR_BOT_TOKEN_HERE
TELEGRAM_CHAT_ID=YOUR_CHAT_ID_HERE

# Scan Configuration
SCAN_URL_1=https://chartink.com/screener/your-scan-url
SCAN_NAME_1=EMA scan
ENABLE_SCAN_1=true

HEADLESS=true
ALWAYS_NOTIFY=false
```

### Getting Your Discord Webhook

1. Go to your Discord server settings
2. Navigate to **Integrations** → **Webhooks**
3. Click **New Webhook** or **Copy Webhook URL**

### Getting Your Telegram Bot Credentials

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the **bot token** (e.g., `123456789:ABCdef...`)
4. For your **chat ID**:
   - Search for **@userinfobot** on Telegram
   - Start a chat - it will show your Chat ID
5. Start a chat with your bot (send `/start`) before running the script

## Usage

Run the bot as a module:
```bash
python -m src.main
```

The bot will:
1. Login to Chartink
2. Load previously seen stocks
3. Run the scan every 15 minutes (configurable)
4. Send Discord alerts for new stocks
5. Save seen stocks to `seen_stocks.json`

## Running & Scheduling (India Time)

- The bot runs on fixed 15‑minute slots during Indian market hours (Asia/Kolkata):
	- 09:15, 09:30, 09:45, …, 15:15.
- If started outside this window, it waits until 09:15 and then runs every 15 minutes.
- Notifications are sent immediately after each scan.

Start in foreground (Git Bash):
```bash
conda activate C:/Swdtools/conda_envs/python_3.13
cd /c/Sandbox/VSCode_Projects/Stock_Bot/src
python main.py
```

Start in background and log to file:
```bash
conda activate C:/Swdtools/conda_envs/python_3.13
cd /c/Sandbox/VSCode_Projects/Stock_Bot
mkdir -p logs
cd src
nohup python main.py > ../logs/bot.log 2>&1 &
echo "PID: $!"
```

Tail logs:
```bash
tail -f ../logs/bot.log
```

Stop background process:
```bash
kill <PID>
```

## Project Structure

```
Stock_Bot/
├── src/
│   ├── __init__.py             # Package initialization
│   ├── main.py                 # Entry point and orchestration
│   ├── chartink.py             # Web scraping client
│   ├── notifier.py             # Discord integration
│   ├── telegram_notifier.py    # Telegram integration
│   ├── storage.py              # Persistent storage
│   └── chartink_selectors.py  # CSS/XPath selectors
├── drivers/
│   └── msedgedriver.exe        # Edge WebDriver (auto-managed)
├── .env                        # Environment variables (create this)
├── .env.example                # Environment template
├── requirements.txt            # Python dependencies
├── run_bot.sh                  # Linux/Mac launcher
├── run_bot.bat                 # Windows launcher
├── deploy.sh                   # Deployment script for cloud VPS
└── README.md
```

## Configuration

### Environment Variables

**Required:**
- `CHARTINK_EMAIL` — Chartink account email
- `CHARTINK_PASSWORD` — Chartink account password

**Notification Platforms (enable at least one):**
- `ENABLE_DISCORD=true` — Enable Discord notifications
- `ENABLE_TELEGRAM=false` — Enable Telegram notifications
- `DISCORD_WEBHOOK` — Discord webhook URL (required if Discord enabled)
- `TELEGRAM_BOT_TOKEN` — Telegram bot token from @BotFather (required if Telegram enabled)
- `TELEGRAM_CHAT_ID` — Your Telegram chat ID (required if Telegram enabled)

**Scan Configuration:**
- `SCAN_URL_1` — First Chartink scan URL
- `SCAN_NAME_1=EMA scan` — Label for first scan
- `ENABLE_SCAN_1=true` — Enable/disable first scan
- `SCAN_URL_2`, `SCAN_NAME_2`, `ENABLE_SCAN_2` — Second scan (optional)
- `SCAN_URL_3`, `SCAN_NAME_3`, `ENABLE_SCAN_3` — Third scan (optional)

**Behavior:**
- `HEADLESS=true` — Run browser hidden (default true)
- `COOKIES_PATH=cookies.json` — File to persist/reuse login session
- `ALWAYS_NOTIFY=false` — When true, send all stocks each run; when false, only new ones
- `PING_HERE=true` — Prepend @here to Discord messages (triggers sounds)

**Simulation Mode (for testing outside market hours):**
- `SIMULATE=false` — When true, bypasses market window and runs compressed loops
- `SIMULATION_RUNS=3` — Number of simulation scans
- `SIMULATION_INTERVAL_SECONDS=60` — Seconds between simulation scans

## Headless & Session Reuse

- The bot runs headless by default and caches login cookies to `cookies.json`.
- On start it attempts to load cookies and go straight to the scan.
- If cookies are invalid/expired, it performs a headless login once and re‑saves cookies automatically.

## Notification Platforms

### Discord
- Webhook messages make sounds only if the channel/user's notification settings allow it or if the message includes a mention.
- Use `PING_HERE=true` to trigger sounds for online members (subject to user/server settings).
- Toggle: Set `ENABLE_DISCORD=false` to disable Discord notifications.

### Telegram
- Messages are sent via Telegram Bot API with Markdown formatting.
- Supports personal chats, groups, and channels.
- Toggle: Set `ENABLE_TELEGRAM=true` to enable Telegram notifications.
- **Note:** You must start a chat with your bot (send `/start`) before it can send you messages.

### Dual-Platform Mode
- You can enable **both** Discord and Telegram simultaneously.
- Notifications will be sent to all enabled platforms.
- To use only one platform, set the other to `false` in `.env`.

## Code Quality

All modules include:
- ✅ Comprehensive docstrings
- ✅ Type hints
- ✅ Error handling with specific exceptions
- ✅ Context manager support (where applicable)
- ✅ PEP 8 compliance

## Troubleshooting

### Import Errors
Make sure to run as a module: `python -m src.main`

### WebDriver Issues
- Ensure Edge browser is installed
- Update `msedgedriver.exe` if needed: [Download Edge Driver](https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/)

### Login Failures
- Verify Chartink credentials in `.env`
- Check if Chartink's login page structure changed (update selectors in `selectors.py`)

### Discord Not Receiving Alerts
- Verify webhook URL is correct
- Check Discord server permissions

## License

MIT License - feel free to modify and distribute.
