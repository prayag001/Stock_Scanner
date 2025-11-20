"""CSS and XPath selectors for Chartink web scraping."""

# Login page selectors (Chartink uses Vue.js/Inertia - updated selectors)
LOGIN_EMAIL_INPUT = "input[type='email']#login-email"
LOGIN_PASSWORD_INPUT = "input[type='password']#login-password"
LOGIN_SUBMIT_BUTTON = "button.primary-button"

# On the screener page
RUN_SCAN_BUTTON_XPATH = "//button[contains(., 'Run Scan')]"

# Stocks table: anchor tags inside table rows
STOCK_ROW_LINKS = "table.table.table-striped.table-hover tbody tr td a"
