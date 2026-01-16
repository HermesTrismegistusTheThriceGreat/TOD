#!/usr/bin/env python3
"""
Final screenshot showing the updated Trade Stats page
"""

import asyncio
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright


async def final_screenshot():
    """Capture final Trade Stats view"""

    screenshot_dir = Path("/Users/muzz/Desktop/tac/TOD/screenshots")
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d")

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1600, 'height': 1000})

        try:
            await page.goto("http://127.0.0.1:5175", wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)

            # Click TRADE STATS
            buttons = await page.query_selector_all('button, a')
            for btn in buttons:
                text = await btn.text_content()
                if text and 'TRADE' in text.upper() and 'STAT' in text.upper():
                    await btn.click()
                    await asyncio.sleep(2)
                    break

            # Take screenshot showing full Trade Stats view
            screenshot_path = screenshot_dir / f"orchestrator-trade-stats-updated-{timestamp}.png"
            await page.screenshot(path=str(screenshot_path), full_page=False)

            print(f"✅ Screenshot captured: {screenshot_path}")

            # Try to find trade stat summary elements and display their content
            try:
                html = await page.inner_html('body')

                # Check for key indicators
                checks = {
                    'TRADE STATS tab active': 'TRADE' in html and 'STAT' in html,
                    'GLD trades present': 'GLD' in html,
                    'opening/closing labels': ('opening' in html.lower() or 'closing' in html.lower()),
                    'P&L values': ('$' in html and ('P/' in html or 'P&L' in html)),
                }

                print("\n✅ Page Validation Results:")
                for check, result in checks.items():
                    status = "✓" if result else "✗"
                    print(f"  {status} {check}")

            except Exception as e:
                print(f"Could not validate page content: {e}")

            return {"status": "success", "path": str(screenshot_path)}

        except Exception as e:
            print(f"❌ Error: {e}")
            return {"status": "error", "error": str(e)}
        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(final_screenshot())
    if result['status'] == 'success':
        print(f"\n📸 Screenshot saved to: {result['path']}")
