"""Chartink web scraping client for automated stock scanning."""
import json
import time
from pathlib import Path
from typing import List, Optional, Tuple

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from chartink_selectors import (
    LOGIN_EMAIL_INPUT, LOGIN_PASSWORD_INPUT, LOGIN_SUBMIT_BUTTON,
    RUN_SCAN_BUTTON_XPATH
)


class ChartinkMaintenanceError(Exception):
    """Raised when Chartink scanner is under maintenance."""
    pass

class ChartinkClient:
    """Selenium-based client for automating Chartink stock screening."""

    def __init__(self, email: str, password: str, driver_path: Path = None,
                 headless: bool = False, cookies_path: Optional[Path] = None):
        """Initialize the Chartink client with Edge WebDriver.

        Args:
            email: Chartink account email
            password: Chartink account password
            driver_path: Path to the Edge WebDriver executable (optional,
                        uses Selenium Manager if not provided)
            headless: Run browser in headless mode when True
            cookies_path: Optional path to persist session cookies
        """
        options = webdriver.EdgeOptions()
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--start-maximized")
        if headless:
            options.add_argument("--headless=new")

        # Use Selenium Manager if no driver path provided
        if driver_path:
            self.driver = webdriver.Edge(
                service=EdgeService(str(driver_path)),
                options=options
            )
        else:
            # Selenium 4.6+ automatically downloads correct driver
            self.driver = webdriver.Edge(options=options)
        self.wait = WebDriverWait(self.driver, 20)
        self.email = email
        self.password = password
        self.cookies_path: Optional[Path] = cookies_path

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures browser cleanup."""
        self.close()
        return False

    def close(self):
        """Close the browser and clean up resources."""
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass

    def login(self):
        """Log into Chartink using provided credentials.

        Raises:
            Exception: If login fails due to timeout or WebDriver error
        """
        try:
            # Chartink login page
            self.driver.get("https://chartink.com/login")
            # Wait for inputs and fill credentials
            email_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, LOGIN_EMAIL_INPUT))
            )
            email_input.send_keys(self.email)
            self.driver.find_element(
                By.CSS_SELECTOR, LOGIN_PASSWORD_INPUT
            ).send_keys(self.password)
            self.driver.find_element(
                By.CSS_SELECTOR, LOGIN_SUBMIT_BUTTON
            ).click()
            # Wait until logged in (e.g., user menu visible or redirected)
            self.wait.until(EC.url_contains("chartink.com"))
        except TimeoutException as e:
            raise Exception(f"Login failed: timeout waiting for elements - {e}") from e
        except WebDriverException as e:
            raise Exception(f"Login failed: WebDriver error - {e}") from e

    def _save_cookies(self):
        """Persist cookies to disk if cookies_path is set."""
        if not self.cookies_path:
            return
        try:
            cookies = self.driver.get_cookies()
            self.cookies_path.write_text(json.dumps(cookies, indent=2), encoding="utf-8")
        except Exception:
            # Non-fatal: continue without persistence
            pass

    def _load_cookies(self):
        """Load cookies from disk if available."""
        if not self.cookies_path or not self.cookies_path.exists():
            return
        try:
            # Must be on the domain before adding cookies
            self.driver.get("https://chartink.com/")
            raw = self.cookies_path.read_text(encoding="utf-8")
            cookies = json.loads(raw)
            for c in cookies:
                # Selenium expects fields like name, value, domain, path, expiry(optional)
                try:
                    self.driver.add_cookie(c)
                except Exception:
                    # Skip cookies that fail to add
                    continue
            self.driver.refresh()
        except Exception:
            # Ignore and proceed without cookies
            pass

    def ensure_session(self, scan_url: str):
        """Ensure we are authenticated for the scan URL using cookie cache.

        Attempts to reuse cookies; if redirected to login, performs login and re-saves cookies.
        """
        # Try with cookies first
        self._load_cookies()
        self.driver.get(scan_url)
        time.sleep(1)
        if "login" in (self.driver.current_url or ""):
            # Need to login
            self.login()
            self._save_cookies()
            # Navigate again now that we're logged in
            self.driver.get(scan_url)

    def open_scan(self, scan_url: str):
        """Navigate to a Chartink scan page.

        Args:
            scan_url: Full URL of the Chartink scan to open

        Raises:
            Exception: If scan page fails to load
        """
        try:
            self.driver.get(scan_url)
            # Wait for the stock table to be present (page auto-loads)
            self.wait.until(
                EC.presence_of_element_located((By.TAG_NAME, "tbody"))
            )
        except TimeoutException as e:
            raise Exception(f"Failed to open scan page: timeout - {e}") from e

    def click_run_scan(self):
        """Click the 'Run Scan' button and wait for results to load.

        Raises:
            Exception: If button click fails
        """
        try:
            btn = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, RUN_SCAN_BUTTON_XPATH))
            )
            btn.click()
            # Wait for results to appear/refresh
            time.sleep(3)
        except TimeoutException as e:
            raise Exception(f"Failed to click run scan button: timeout - {e}") from e

    def get_stocks(self) -> List[str]:
        """Parse the current page and extract stock symbols from results table.

        Returns:
            List of stock symbol strings
        """
        # Use current DOM; allow time for dynamic content to load
        time.sleep(2)
        html = self.driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        
        # Check for maintenance message
        self._check_for_maintenance(soup)
        
        # Extract stock symbols from URL parameters in links
        stocks = set()
        import re
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if 'symbol=' in href:
                # Extract symbol from URL like "&symbol=PNB"
                match = re.search(r'symbol=([A-Z]+)', href)
                if match:
                    stocks.add(match.group(1))
        
        stock_list = sorted(list(stocks))
        return stock_list
    
    def _check_for_maintenance(self, soup: Optional[BeautifulSoup] = None) -> bool:
        """Check if Chartink is showing a maintenance message.
        
        Args:
            soup: Optional BeautifulSoup object of page. If None, parses current page.
            
        Returns:
            True if maintenance detected
            
            Raises:
            ChartinkMaintenanceError: If maintenance message is detected
        """
        if soup is None:
            html = self.driver.page_source
            soup = BeautifulSoup(html, "html.parser")
        
        # Check for maintenance indicators
        page_text = soup.get_text().lower()
        maintenance_keywords = [
            "under maintenance",
            "scanner under maintenance",
            "please re-try",
            "please retry",
            "service unavailable",
            "temporarily unavailable",
            "server is busy",
            "too many requests"
        ]
        
        for keyword in maintenance_keywords:
            if keyword in page_text:
                # Try to extract the full message
                for element in soup.find_all(['div', 'p', 'span', 'h1', 'h2', 'h3']):
                    text = element.get_text(strip=True)
                    if keyword in text.lower():
                        raise ChartinkMaintenanceError(f"Chartink: {text}")
                raise ChartinkMaintenanceError(f"Chartink scanner is under maintenance. Please retry later.")
        
        return False

    def run_scan_and_fetch(self, scan_url: str, max_retries: int = 3, retry_delay: int = 60) -> Tuple[List[str], bool]:
        """Execute a complete scan workflow: open and fetch results.

        Args:
            scan_url: Full URL of the Chartink scan
            max_retries: Maximum number of retries on maintenance (default: 3)
            retry_delay: Seconds to wait between retries (default: 60)

        Returns:
            Tuple of (List of stock symbols, maintenance_encountered bool)
            
        Note:
            If maintenance is encountered and all retries fail, returns empty list
            with maintenance_encountered=True instead of raising exception.
        """
        for attempt in range(max_retries):
            try:
                self.open_scan(scan_url)
                # Page auto-loads scan results, no button click needed
                # Small sleep to ensure AJAX content is loaded
                time.sleep(1)
                stocks = self.get_stocks()
                return stocks, False  # Success, no maintenance
                
            except ChartinkMaintenanceError as e:
                if attempt < max_retries - 1:
                    print(f"  ⚠️  {e}")
                    print(f"  ⏳ Waiting {retry_delay}s before retry ({attempt + 1}/{max_retries})...")
                    time.sleep(retry_delay)
                else:
                    print(f"  ❌ {e}")
                    print(f"  ❌ Max retries ({max_retries}) reached. Skipping this scan slot.")
                    return [], True  # Return empty with maintenance flag
                    
        return [], True  # Should not reach here, but safety fallback
