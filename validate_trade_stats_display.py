#!/usr/bin/env python3
"""
Trade Stats Display Validation Script
Validates the Trade Stats section on the orchestrator application
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright


async def validate_trade_stats():
    """Navigate to application and capture Trade Stats display"""

    # Setup directories
    screenshot_dir = Path("/Users/muzz/Desktop/tac/TOD/screenshots")
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d")
    screenshot_filename = f"trade-stats-updated-{timestamp}.png"
    screenshot_path = screenshot_dir / screenshot_filename

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Navigate to the application
            print(f"Navigating to http://127.0.0.1:5175...")
            await page.goto("http://127.0.0.1:5175", wait_until="networkidle", timeout=30000)

            # Wait for page to fully load
            print("Waiting for page to load (2 seconds)...")
            await asyncio.sleep(2)

            # Take screenshot to see current state
            print("Taking initial screenshot...")
            await page.screenshot(path=str(screenshot_path))

            # Get page content to analyze
            content = await page.content()

            # Check for Trade Stats related content
            has_trade_stats = "trade" in content.lower() or "stats" in content.lower()
            has_pnl = "pnl" in content.lower() or "p&l" in content.lower()

            # Try to find Trade Stats or related elements
            trade_stats_elements = await page.query_selector_all('[class*="trade"], [class*="stats"], [class*="pnl"]')

            print(f"\nValidation Results:")
            print(f"  - Screenshot saved to: {screenshot_path}")
            print(f"  - Page contains 'trade' or 'stats': {has_trade_stats}")
            print(f"  - Page contains 'pnl' or 'p&l': {has_pnl}")
            print(f"  - Trade/Stats related elements found: {len(trade_stats_elements)}")

            # Create a report
            report_content = f"""# Trade Stats Display Validation Report
Date: {datetime.now().isoformat()}
URL: http://127.0.0.1:5175

## Validation Results
- Status: SUCCESS
- Screenshot captured: {screenshot_filename}
- Full path: {screenshot_path}

## Observations
- Page loaded successfully
- Trade/Stats content detected: {has_trade_stats}
- P&L content detected: {has_pnl}
- Related elements found: {len(trade_stats_elements)}

## Screenshot Location
{screenshot_path}

## Next Steps
Review the screenshot to verify Trade Stats display is functioning correctly.
"""

            report_path = screenshot_dir / f"validation-report-{timestamp}.md"
            with open(report_path, "w") as f:
                f.write(report_content)

            print(f"\nReport saved to: {report_path}")
            print(f"\nScreenshot path: {screenshot_path}")

            return {
                "status": "success",
                "screenshot_path": str(screenshot_path),
                "report_path": str(report_path)
            }

        except Exception as e:
            print(f"Error during validation: {e}")
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
    result = asyncio.run(validate_trade_stats())
    print(f"\nFinal Result: {result}")
