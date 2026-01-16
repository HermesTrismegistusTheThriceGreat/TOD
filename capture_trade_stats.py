#!/usr/bin/env python3
"""
Capture Trade Stats Display - Enhanced Script
Searches for and captures the Trade Stats section
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright


async def capture_trade_stats():
    """Navigate and capture Trade Stats display"""

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

            # Check for Trade Stats related elements and scroll to find them
            print("Looking for Trade Stats elements...")

            # Try to find and click on a trades or stats nav item if it exists
            nav_items = await page.query_selector_all('nav a, nav button, [role="tab"], [class*="nav"] a')

            print(f"Found {len(nav_items)} navigation items, searching for Trade Stats...")

            # Look for any button/link with 'trade', 'stats', or related text
            for nav_item in nav_items:
                text = await nav_item.text_content()
                print(f"  Nav item: {text}")
                if text and any(word in text.lower() for word in ['trade', 'stat', 'history', 'closed']):
                    print(f"  Clicking on: {text}")
                    await nav_item.click()
                    await asyncio.sleep(1)
                    break

            # Scroll down to see if Trade Stats are below the fold
            print("Scrolling down to look for Trade Stats...")
            await page.evaluate("window.scrollBy(0, 500)")
            await asyncio.sleep(1)

            # Take screenshot of current view
            screenshot_path = screenshot_dir / f"trade-stats-main-{timestamp}.png"
            await page.screenshot(path=str(screenshot_path))
            print(f"Screenshot 1 saved: {screenshot_path}")

            # Look for trade/stats cards or elements
            trade_elements = await page.query_selector_all('[class*="Card"], [class*="card"], [class*="trade"], [class*="Trade"]')
            print(f"Found {len(trade_elements)} card/trade elements")

            # Try to find the Trade Stats Grid or similar
            page_html = await page.content()

            if 'TradeStats' in page_html or 'trade-stats' in page_html.lower():
                print("TradeStats component found in page!")
                screenshot_path2 = screenshot_dir / f"trade-stats-component-{timestamp}.png"
                await page.screenshot(path=str(screenshot_path2))
                print(f"Screenshot 2 saved: {screenshot_path2}")

            # Check all text content for opening_credit or closing_debit
            full_text = await page.text_content()

            has_opening_credit = 'opening' in full_text.lower() and 'credit' in full_text.lower()
            has_closing_debit = 'closing' in full_text.lower() and 'debit' in full_text.lower()

            print(f"\nValidation Results:")
            print(f"  - Opening credit field found: {has_opening_credit}")
            print(f"  - Closing debit field found: {has_closing_debit}")
            print(f"  - Trade related elements: {len(trade_elements)}")

            return {
                "status": "success",
                "screenshot_path": str(screenshot_path),
                "has_opening_credit": has_opening_credit,
                "has_closing_debit": has_closing_debit
            }

        except Exception as e:
            print(f"Error during capture: {e}")
            error_screenshot = screenshot_dir / f"error-{timestamp}.png"
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
    result = asyncio.run(capture_trade_stats())
    print(f"\nFinal Result: {result}")
