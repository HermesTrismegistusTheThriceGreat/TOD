#!/usr/bin/env python3
"""
Capture Trade Summary Cards - Scroll to view the P&L summary
"""

import asyncio
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright


async def capture_trade_summary():
    """Navigate to Trade Stats and capture summary cards"""

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

            # Click on TRADE STATS tab
            print("Looking for TRADE STATS button...")
            buttons = await page.query_selector_all('button, a, [role="tab"]')
            for btn in buttons:
                text = await btn.text_content()
                if text and 'TRADE' in text.upper() and 'STAT' in text.upper():
                    print(f"Clicking TRADE STATS...")
                    await btn.click()
                    await asyncio.sleep(2)
                    break

            # Scroll to top to see summary cards
            print("Scrolling to top to see summary cards...")
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(1)

            # Take screenshot 1 - top of page
            screenshot_path1 = screenshot_dir / f"trade-summary-top-{timestamp}.png"
            await page.screenshot(path=str(screenshot_path1))
            print(f"Screenshot 1 (top) saved: {screenshot_path1}")

            # Scroll down a bit to see trade cards
            print("Scrolling down to see trade cards...")
            await page.evaluate("window.scrollBy(0, 300)")
            await asyncio.sleep(1)

            # Take screenshot 2 - middle
            screenshot_path2 = screenshot_dir / f"trade-summary-cards-{timestamp}.png"
            await page.screenshot(path=str(screenshot_path2))
            print(f"Screenshot 2 (cards) saved: {screenshot_path2}")

            # Scroll down more to see different trades
            print("Scrolling down more...")
            await page.evaluate("window.scrollBy(0, 400)")
            await asyncio.sleep(1)

            # Take screenshot 3 - showing more trades
            screenshot_path3 = screenshot_dir / f"trade-summary-more-{timestamp}.png"
            await page.screenshot(path=str(screenshot_path3))
            print(f"Screenshot 3 (more trades) saved: {screenshot_path3}")

            # Get page HTML to check for key fields
            page_html = await page.content()

            # Look for specific patterns
            checks = {
                'opening_credit in HTML': 'opening_credit' in page_html,
                'closing_debit in HTML': 'closing_debit' in page_html,
                'opening label': 'opening' in page_html.lower(),
                'closing label': 'closing' in page_html.lower(),
                'GLD present': 'GLD' in page_html,
                'Trade summary found': 'TradeStatsSummary' in page_html or 'summary' in page_html.lower(),
            }

            print(f"\nPage Content Checks:")
            for key, found in checks.items():
                print(f"  - {key}: {found}")

            return {
                "status": "success",
                "screenshots": [
                    str(screenshot_path1),
                    str(screenshot_path2),
                    str(screenshot_path3)
                ],
                "checks": checks
            }

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "error": str(e)
            }
        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(capture_trade_summary())
    print(f"\nFinal Result:")
    print(f"  Status: {result['status']}")
    if result['status'] == 'success':
        print(f"  Screenshots:")
        for i, ss in enumerate(result['screenshots'], 1):
            print(f"    {i}: {ss}")
