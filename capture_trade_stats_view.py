#!/usr/bin/env python3
"""
Capture Trade Stats View - Click on Trade Stats Tab
"""

import asyncio
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright


async def capture_trade_stats_view():
    """Navigate to Trade Stats tab and capture display"""

    # Setup directories
    screenshot_dir = Path("/Users/muzz/Desktop/tac/TOD/screenshots")
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d")

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1400, 'height': 900})

        try:
            # Navigate to the application
            print(f"Navigating to http://127.0.0.1:5175...")
            await page.goto("http://127.0.0.1:5175", wait_until="networkidle", timeout=30000)

            # Wait for page to fully load
            print("Waiting for page to load...")
            await asyncio.sleep(2)

            # Look for TRADE STATS tab/button and click it
            print("Looking for TRADE STATS button...")

            # Try multiple selectors to find the Trade Stats button
            trade_stats_button = None

            # Try text content matching
            buttons = await page.query_selector_all('button, a, [role="tab"]')
            for btn in buttons:
                text = await btn.text_content()
                if text and 'TRADE' in text.upper() and 'STAT' in text.upper():
                    trade_stats_button = btn
                    print(f"Found button: {text}")
                    break

            if trade_stats_button:
                print("Clicking on TRADE STATS button...")
                await trade_stats_button.click()
                await asyncio.sleep(2)
            else:
                print("TRADE STATS button not found, scrolling and waiting...")
                await asyncio.sleep(1)

            # Take screenshot
            screenshot_path = screenshot_dir / f"trade-stats-view-{timestamp}.png"
            await page.screenshot(path=str(screenshot_path))
            print(f"Screenshot saved: {screenshot_path}")

            # Check for the updated field names
            page_html = await page.content()

            # Look for the specific field names or values
            checks = {
                'opening_credit': 'opening_credit' in page_html or 'opening' in page_html.lower(),
                'closing_debit': 'closing_debit' in page_html or 'closing' in page_html.lower(),
                'GLD': 'GLD' in page_html,
                'Iron Butterfly': 'Iron Butterfly' in page_html or 'iron_butterfly' in page_html.lower(),
            }

            print(f"\nPage Content Checks:")
            for key, found in checks.items():
                print(f"  - {key}: {found}")

            return {
                "status": "success",
                "screenshot_path": str(screenshot_path),
                "checks": checks
            }

        except Exception as e:
            print(f"Error during capture: {e}")
            import traceback
            traceback.print_exc()
            error_screenshot = screenshot_dir / f"error-trade-stats-{timestamp}.png"
            try:
                await page.screenshot(path=str(error_screenshot))
                print(f"Error screenshot saved to: {error_screenshot}")
            except:
                pass
            return {
                "status": "error",
                "error": str(e)
            }
        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(capture_trade_stats_view())
    print(f"\nFinal Result:")
    print(f"  Status: {result['status']}")
    if result['status'] == 'success':
        print(f"  Screenshot: {result['screenshot_path']}")
        print(f"  Checks: {result['checks']}")
    else:
        print(f"  Error: {result.get('error', 'Unknown error')}")
