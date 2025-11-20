"""Main entry point for the Stock Bot application.

Runs the scan every 15 minutes between 09:15 and 15:15 India time.
Sends immediate Discord notifications for new stocks (or all if ALWAYS_NOTIFY=true).
Daily reset at 15:30 clears all seen stocks for fresh start next day.
"""
import os
import time
import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

from dotenv import load_dotenv

from chartink import ChartinkClient
from notifier import format_stock_alert, send_discord
from storage import load_seen, save_seen


def main():
    """Run the stock scanning bot with continuous monitoring."""
    load_dotenv()

    email = os.getenv("CHARTINK_EMAIL")
    password = os.getenv("CHARTINK_PASSWORD")
    webhook = os.getenv("DISCORD_WEBHOOK")
    always_notify = os.getenv("ALWAYS_NOTIFY", "false").lower() in ("1", "true", "yes")
    simulate = os.getenv("SIMULATE", "false").lower() in ("1", "true", "yes")
    simulation_runs = int(os.getenv("SIMULATION_RUNS", "3"))
    simulation_interval_seconds = int(os.getenv("SIMULATION_INTERVAL_SECONDS", "60"))
    headless = os.getenv("HEADLESS", "true").lower() in ("1", "true", "yes")
    cookies_path = Path(os.getenv("COOKIES_PATH", "cookies.json"))

    # Multi-scan configuration
    scan_url_1 = os.getenv("SCAN_URL_1")
    scan_name_1 = os.getenv("SCAN_NAME_1", "Scan 1")
    enable_scan_1 = os.getenv("ENABLE_SCAN_1", "true").lower() in ("1", "true", "yes")

    scan_url_2 = os.getenv("SCAN_URL_2")
    scan_name_2 = os.getenv("SCAN_NAME_2", "Scan 2")
    enable_scan_2 = os.getenv("ENABLE_SCAN_2", "true").lower() in ("1", "true", "yes")

    # Optional third scan
    scan_url_3 = os.getenv("SCAN_URL_3")
    scan_name_3 = os.getenv("SCAN_NAME_3", "Scan 3")
    enable_scan_3 = os.getenv("ENABLE_SCAN_3", "true").lower() in ("1", "true", "yes")

    if not all([email, password, webhook]):
        raise RuntimeError(
            "Missing env vars: CHARTINK_EMAIL, CHARTINK_PASSWORD, DISCORD_WEBHOOK"
        )

    # Build list of enabled scans
    scans = []
    if enable_scan_1 and scan_url_1:
        scans.append({"url": scan_url_1, "name": scan_name_1})
    if enable_scan_2 and scan_url_2:
        scans.append({"url": scan_url_2, "name": scan_name_2})
    if enable_scan_3 and scan_url_3:
        scans.append({"url": scan_url_3, "name": scan_name_3})

    if not scans:
        raise RuntimeError("No scans enabled. Set ENABLE_SCAN_1/2/3=true with corresponding SCAN_URL_*")

    # Use Selenium Manager (auto-downloads correct driver)
    # or specify custom driver path if needed
    driver_path = None  # Let Selenium Manager handle it
    # Uncomment to use custom driver:
    # driver_path = Path("drivers/msedgedriver.exe")
    # if not driver_path.exists():
    #     raise RuntimeError(f"Edge driver not found at {driver_path}")

    # Scheduling parameters (India time)
    tz = ZoneInfo("Asia/Kolkata")
    trading_start = datetime.time(9, 15)
    trading_end = datetime.time(15, 15)  # inclusive
    daily_reset_time = datetime.time(15, 30)  # Clear seen stocks at 15:30

    def next_trading_start(after: datetime.datetime) -> datetime.datetime:
        """Return next trading day start datetime in tz after given datetime.
        
        Skips weekends (Saturday=5, Sunday=6) and moves to next Monday.
        """
        target_date = after.date()
        # If we're already past today's end, move to next day
        if after.time() > trading_end:
            target_date += datetime.timedelta(days=1)
        
        # Skip weekends: if Saturday (5) or Sunday (6), move to Monday
        while target_date.weekday() >= 5:  # 5=Saturday, 6=Sunday
            target_date += datetime.timedelta(days=1)
        
        return datetime.datetime.combine(target_date, trading_start, tzinfo=tz)

    def next_slot(current: datetime.datetime) -> datetime.datetime:
        """Compute next 15-min slot inside trading window or next day start."""
        # If before start -> first slot
        if current.time() < trading_start:
            return datetime.datetime.combine(current.date(), trading_start, tzinfo=tz)
        # If after end -> next day start
        if current.time() > trading_end:
            return next_trading_start(current)
        # Inside window: align to exact slot boundaries (09:15, 09:30, 09:45, 10:00, ...)
        # Slots: minute must be 0, 15, 30, or 45
        hour = current.hour
        minute = current.minute
        # Calculate next slot minute
        if minute < 15:
            next_minute = 15
        elif minute < 30:
            next_minute = 30
        elif minute < 45:
            next_minute = 45
        else:  # minute >= 45
            next_minute = 0
            hour += 1
        
        next_time = datetime.time(hour, next_minute)
        # Check if next slot exceeds trading end
        if next_time > trading_end:
            return next_trading_start(current)
        
        next_dt = datetime.datetime.combine(current.date(), next_time, tzinfo=tz)
        # If we're already past this slot (e.g., current is 09:30:05), move to next
        if next_dt <= current:
            if next_minute == 45:
                hour += 1
                next_minute = 0
            else:
                next_minute += 15
            next_time = datetime.time(hour, next_minute)
            if next_time > trading_end:
                return next_trading_start(current)
            next_dt = datetime.datetime.combine(current.date(), next_time, tzinfo=tz)
        
        return next_dt

    with ChartinkClient(email=email, password=password, driver_path=driver_path,
                        headless=headless, cookies_path=cookies_path) as client:
        print("Logging into Chartink...")
        # Reuse session via cookies when possible; falls back to login as needed
        client.ensure_session(scans[0]["url"])
        print("Logged in.")

        # Load separate seen stocks for each scan
        seen_stocks = {}
        for scan in scans:
            scan_key = scan["name"].replace(" ", "_").lower()
            seen_path = Path(f"seen_stocks_{scan_key}.json")
            if seen_path.exists():
                seen_stocks[scan["name"]] = load_seen(seen_path)
            else:
                seen_stocks[scan["name"]] = set()
        print(f"Loaded seen stocks: {', '.join([f'{name}={len(s)}' for name, s in seen_stocks.items()])}")

        # Track if reset was done today
        last_reset_date = None

        # Simulation mode: run compressed multiple scans immediately regardless of market hours.
        if simulate:
            print(f"SIMULATION MODE ENABLED: performing {simulation_runs} scan(s) every {simulation_interval_seconds}s (market hour restrictions bypassed).")
            for run_index in range(1, simulation_runs + 1):
                print(f"[Simulation] Run {run_index}/{simulation_runs}")
                for scan in scans:
                    scan_name = scan["name"]
                    scan_url = scan["url"]
                    print(f"  Running {scan_name}...")
                    stocks = client.run_scan_and_fetch(scan_url)
                    current_set = set(stocks)
                    seen = seen_stocks[scan_name]
                    new_stocks = sorted(list(current_set - seen))
                    if always_notify:
                        target_stocks = sorted(list(current_set))  # Use deduplicated set
                        print(f"  ALWAYS_NOTIFY enabled. Sending {len(target_stocks)} stock(s): {target_stocks}")
                    else:
                        target_stocks = new_stocks
                        if target_stocks:
                            print(f"  New stocks detected: {target_stocks}")
                        else:
                            print(f"  No new stocks for {scan_name}.")
                    for stock in target_stocks:
                        msg = format_stock_alert(stock, scan_url, scan_name)
                        send_discord(webhook, msg)
                    if target_stocks:
                        print(f"  Discord notifications dispatched for {scan_name}.")
                    seen |= current_set
                    seen_stocks[scan_name] = seen
                    scan_key = scan_name.replace(" ", "_").lower()
                    save_seen(seen, Path(f"seen_stocks_{scan_key}.json"))
                if run_index < simulation_runs:
                    print(f"Waiting {simulation_interval_seconds}s before next simulation run...")
                    time.sleep(simulation_interval_seconds)
            print("Simulation complete. Exiting.")
            return

        while True:
            now = datetime.datetime.now(tz)
            
            # Skip weekends (Saturday=5, Sunday=6)
            if now.weekday() >= 5:
                next_monday = next_trading_start(now)
                sleep_seconds = (next_monday - now).total_seconds()
                day_name = "Saturday" if now.weekday() == 5 else "Sunday"
                print(f"Weekend ({day_name}). Market closed. Sleeping until Monday {next_monday.time()} ({int(sleep_seconds)}s / {int(sleep_seconds/3600)} hours)...")
                time.sleep(sleep_seconds)
                continue
            
            # Daily reset: Clear all seen stocks at 15:30 once per day
            if (now.time().hour == 15 and now.time().minute == 30 and 
                now.date() != last_reset_date):
                print(f"\n{'='*60}")
                print(f"DAILY RESET @ {now.time().strftime('%H:%M:%S')} - Clearing all seen stocks")
                print(f"{'='*60}")
                for scan_name in seen_stocks.keys():
                    seen_stocks[scan_name] = set()
                    scan_key = scan_name.replace(" ", "_").lower()
                    save_seen(set(), Path(f"seen_stocks_{scan_key}.json"))
                    print(f"  ✓ Cleared: {scan_name}")
                print("Daily reset complete. All scans will treat stocks as new tomorrow.")
                print(f"{'='*60}\n")
                last_reset_date = now.date()
                # Sleep past 15:30 to avoid re-triggering
                time.sleep(60)
                continue
            
            if now.time() < trading_start or now.time() > trading_end:
                next_start = next_trading_start(now)
                sleep_seconds = (next_start - now).total_seconds()
                print(f"Outside trading window ({now.time()}). Sleeping until {next_start.time()} ({int(sleep_seconds)}s)...")
                time.sleep(sleep_seconds)
                continue

            # Align execution to slot boundaries: if not exactly on a slot, wait until next slot
            # Slots: 9:15, 9:30, 9:45, ... 15:15
            slot_minutes = {15, 30, 45, 0}
            if now.minute not in slot_minutes or now.second != 0:
                target = next_slot(now)
                sleep_seconds = (target - now).total_seconds()
                print(f"Waiting {int(sleep_seconds)}s for next slot at {target.time()}...")
                time.sleep(sleep_seconds)
                continue

            # Execute all enabled scans at this slot
            run_time = datetime.datetime.now(tz)
            print(f"Running scans @ {run_time.time()} Asia/Kolkata")
            
            for scan in scans:
                scan_name = scan["name"]
                scan_url = scan["url"]
                print(f"  [{scan_name}] Scanning...")
                stocks = client.run_scan_and_fetch(scan_url)
                current_set = set(stocks)
                seen = seen_stocks[scan_name]
                new_stocks = sorted(list(current_set - seen))

                if always_notify:
                    target_stocks = sorted(list(current_set))  # Use deduplicated set
                    print(f"  [{scan_name}] ALWAYS_NOTIFY enabled. Sending {len(target_stocks)} stock(s): {target_stocks}")
                else:
                    target_stocks = new_stocks
                    if target_stocks:
                        print(f"  [{scan_name}] New stocks detected: {target_stocks}")
                    else:
                        print(f"  [{scan_name}] No new stocks this slot.")

                for stock in target_stocks:
                    msg = format_stock_alert(stock, scan_url, scan_name)
                    send_discord(webhook, msg)
                if target_stocks:
                    print(f"  [{scan_name}] Discord notifications dispatched.")

                # Update seen repository for this scan
                seen |= current_set
                seen_stocks[scan_name] = seen
                scan_key = scan_name.replace(" ", "_").lower()
                save_seen(seen, Path(f"seen_stocks_{scan_key}.json"))

            # Determine next slot sleep
            nxt = next_slot(datetime.datetime.now(tz))
            if nxt.time() > trading_end:
                # Will sleep until next trading day start in next loop iteration
                print("End of trading day reached. Preparing for next day.")
            else:
                sleep_seconds = (nxt - datetime.datetime.now(tz)).total_seconds()
                print(f"Sleeping until next slot {nxt.time()} ({int(sleep_seconds)}s)...")
                time.sleep(sleep_seconds)

if __name__ == "__main__":
    main()
