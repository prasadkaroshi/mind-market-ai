# screener_navigator.py
import asyncio
import sys
import os
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright, Page

from config import RAW_DATA_DIR, SCREENER_LOGIN_URL, SCREENER_DASHBOARD_URL, HEADLESS_BROWSER, BROWSER_USER_AGENT

async def login_to_screener(page: Page) -> bool:
    """Handles the login process on Screener.in using credentials from environment variables."""
    email = os.environ.get("SCREENER_EMAIL")
    password = os.environ.get("SCREENER_PASSWORD")

    if not email or not password:
        print("CRITICAL: SCREENER_EMAIL or SCREENER_PASSWORD not found in environment.")
        return False
        
    print("Attempting to log into Screener.in...")
    try:
        await page.goto(SCREENER_LOGIN_URL, timeout=60000)
        await page.fill("#id_username", email)
        await page.fill("#id_password", password)
        await page.click("button.button-primary[type='submit']")
        await page.wait_for_url(lambda url: SCREENER_DASHBOARD_URL in url or "login" not in url.lower(), timeout=20000)
        
        if SCREENER_DASHBOARD_URL in page.url or "login" not in page.url.lower():
            print("Login successful.")
            return True
        print("Login failed: Could not verify dashboard URL after submit.")
        return False
    except Exception as e:
        print(f"Error during login: {e}")
        return False

async def navigate_to_company_page(page: Page, company_id: str) -> bool:
    company_url = f"https://www.screener.in/company/{company_id.upper()}/consolidated/"
    print(f"Navigating to {company_id.upper()} page...")
    try:
        response = await page.goto(company_url, timeout=60000)
        if response and response.status == 200 and f"/company/{company_id.upper()}/" in page.url:
            print(f"Successfully on {company_id.upper()}'s page.")
            return True
        print(f"Failed to navigate to {company_id.upper()}'s page. URL or status code did not match.")
        return False
    except Exception as e:
        print(f"Error navigating to {company_id.upper()}'s page: {e}")
        return False

async def export_company_data_to_excel(page: Page, company_id: str) -> Optional[Path]:
    print(f"Attempting to export Excel for {company_id.upper()}...")
    try:
        export_button = page.locator("button:has-text('Export to Excel')")
        await export_button.wait_for(state="visible", timeout=10000)
        async with page.expect_download(timeout=30000) as download_info:
            await export_button.click()
        download = await download_info.value
        filename = "".join(c if c.isalnum() or c in ['.', '-', '_'] else '_' for c in download.suggested_filename)
        download_path = RAW_DATA_DIR / filename
        await download.save_as(download_path)
        print(f"Excel downloaded successfully: {download_path.name}")
        return download_path
    except Exception as e:
        print(f"Could not export Excel for {company_id.upper()}. The 'Export to Excel' button may not be available for this company, or a timeout occurred.")
        print(f"Underlying error: {repr(e)}")
        return None

async def download_excel_for_stock_async(stock_ticker: str) -> Optional[Path]:
    """The main asynchronous pipeline function to download a stock's data."""
    print(f"\n--- Starting ASYNC Web Scraping for: {stock_ticker} ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS_BROWSER)
        context = await browser.new_context(user_agent=BROWSER_USER_AGENT, accept_downloads=True)
        page = await context.new_page()
        downloaded_path = None
        try:
            if await login_to_screener(page):
                if await navigate_to_company_page(page, stock_ticker):
                    await asyncio.sleep(1) 
                    downloaded_path = await export_company_data_to_excel(page, stock_ticker)
        except Exception as e:
            print(f"An unexpected error occurred in the Playwright pipeline: {e}")
        finally:
            print("Closing browser.")
            await context.close()
            await browser.close()
            return downloaded_path

if __name__ == "__main__":
    if len(sys.argv) > 1:
        ticker_arg = sys.argv[1]
        asyncio.run(download_excel_for_stock_async(ticker_arg))
    else:
        print("Please provide a stock ticker for testing.")