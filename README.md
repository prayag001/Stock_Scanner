# Stock Bot

Automated stock screening bot that monitors [Chartink.com](https://chartink.com) for Indian stocks matching custom criteria and sends real-time Discord alerts.

## Features

- 🔍 **Automated Scanning** - Runs custom Chartink scans on a schedule
- 🔔 **Discord Notifications** - Real-time alerts for new stocks
- 💾 **Persistent Tracking** - Remembers seen stocks to avoid duplicates
- 🌐 **Browser Automation** - Selenium-based web scraping
- ⚡ **Context Manager Support** - Automatic resource cleanup

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
SCAN_URL=https://chartink.com/screener/your-scan-url
DISCORD_WEBHOOK=https://discord.com/api/webhooks/your-webhook-url
REFRESH_MINUTES=15
```

### Getting Your Discord Webhook

1. Go to your Discord server settings
2. Navigate to **Integrations** → **Webhooks**
3. Click **New Webhook** or **Copy Webhook URL**

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
│   ├── __init__.py        # Package initialization
│   ├── main.py            # Entry point and orchestration
│   ├── chartink.py        # Web scraping client
│   ├── notifier.py        # Discord integration
│   ├── storage.py         # Persistent storage
│   └── chartink_selectors.py # CSS/XPath selectors
├── drivers/
│   └── msedgedriver.exe   # Edge WebDriver
├── .env                   # Environment variables (create this)
├── requirements.txt       # Python dependencies
└── README.md
```

## Configuration

### Environment Variables

Required:
- `CHARTINK_EMAIL` — Chartink account email
- `CHARTINK_PASSWORD` — Chartink account password
- `SCAN_URL` — Full Chartink scan URL
- `DISCORD_WEBHOOK` — Discord webhook URL

Scheduling and behavior:
- `HEADLESS=true` — run browser hidden (default true)
- `COOKIES_PATH=cookies.json` — file to persist/reuse login session
- `ALWAYS_NOTIFY=false` — when true, send all stocks each run; when false, only new ones

Audible alerts (optional):
- `PING_HERE=true` — prepend @here to trigger sounds for online members
- `MENTION_ROLE_ID=<roleId>` — ping a role (requires permission)
- `MENTION_USER_ID=<userId>` — ping a specific user

Simulation (for quick testing outside market hours):
- `SIMULATE=false` — when true, bypasses market window and runs compressed loops
- `SIMULATION_RUNS=3` — number of simulation scans
- `SIMULATION_INTERVAL_SECONDS=60` — seconds between simulation scans

Note: The bot uses fixed 15‑minute slots during market hours; `REFRESH_MINUTES` is not used in scheduled mode.

## Headless & Session Reuse

- The bot runs headless by default and caches login cookies to `cookies.json`.
- On start it attempts to load cookies and go straight to the scan.
- If cookies are invalid/expired, it performs a headless login once and re‑saves cookies automatically.

## Discord Audible Alerts

- Webhook messages make sounds only if the channel/user’s notification settings allow it or if the message includes a mention.
- Use `PING_HERE=true` or set `MENTION_ROLE_ID`/`MENTION_USER_ID` to trigger sounds (subject to user/server settings).

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
