"""Debug script to diagnose scraper issues"""
import asyncio
from playwright.async_api import async_playwright

async def debug_scrape(url):
    """Debug scraper with visual browser and screenshots"""
    print(f"\n=== DEBUG SCRAPER ===")
    print(f"URL: {url}\n")

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=False,  # Show browser window
        args=['--disable-blink-features=AutomationControlled']
    )

    context = await browser.new_context(
        locale='en-US',
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    )

    page = await context.new_page()

    # Navigate
    print(f"1. Navigating to URL...")
    await page.goto(url, wait_until='domcontentloaded', timeout=60000)
    await asyncio.sleep(3)
    await page.screenshot(path='debug_1_initial.png')
    print(f"   ✓ Screenshot saved: debug_1_initial.png")

    # Check for business name
    print(f"\n2. Looking for business name...")
    name_selectors = ['h1.DUwDvf', 'h1[class*="fontHeadline"]', 'h1']
    for selector in name_selectors:
        try:
            elem = await page.query_selector(selector)
            if elem:
                name = await elem.text_content()
                print(f"   ✓ Found with '{selector}': {name}")
                break
        except:
            pass

    # Check for reviews button
    print(f"\n3. Looking for Reviews button...")
    review_button_selectors = [
        'button[aria-label*="Reviews"]',
        'button[aria-label*="ביקורות"]',  # Hebrew
        'button:has-text("Reviews")',
        'button:has-text("ביקורות")',
        'button.hh2c6',
    ]

    review_button = None
    for selector in review_button_selectors:
        try:
            buttons = await page.query_selector_all(selector)
            print(f"   - Trying '{selector}': Found {len(buttons)} elements")
            if len(buttons) > 0:
                review_button = buttons[0]
                text = await review_button.text_content()
                print(f"     ✓ Button text: '{text}'")
                break
        except Exception as e:
            print(f"   - Error with '{selector}': {e}")

    if review_button:
        print(f"\n4. Clicking Reviews button...")
        await review_button.click()
        await asyncio.sleep(3)
        await page.screenshot(path='debug_2_after_click.png')
        print(f"   ✓ Screenshot saved: debug_2_after_click.png")
    else:
        print(f"   ✗ Could not find Reviews button")
        await page.screenshot(path='debug_2_no_button.png')
        print(f"   ✓ Screenshot saved: debug_2_no_button.png")

    # Check for reviews container
    print(f"\n5. Looking for reviews container...")
    container_selectors = [
        'div.m6QErb.DxyBCb.kA9KIf.dS8AEf',
        'div[role="feed"]',
        'div.review-dialog-list',
        'div[class*="scrollable"]',
    ]

    container = None
    for selector in container_selectors:
        try:
            elem = await page.wait_for_selector(selector, timeout=5000)
            if elem:
                print(f"   ✓ Found container with '{selector}'")
                container = elem
                break
        except:
            print(f"   - '{selector}': Not found")

    if not container:
        print(f"   ✗ Could not find reviews container")
        print(f"\n   Trying to find ANY scrollable div...")
        all_divs = await page.query_selector_all('div')
        print(f"   Total divs on page: {len(all_divs)}")

    # Check for review elements
    print(f"\n6. Looking for review elements...")
    if container:
        review_selectors = [
            'div.jftiEf',
            'div.fontBodyMedium',
            'div[data-review-id]',
            'div[class*="review"]',
        ]

        for selector in review_selectors:
            try:
                reviews = await container.query_selector_all(selector)
                print(f"   - '{selector}': Found {len(reviews)} elements")
            except Exception as e:
                print(f"   - '{selector}': Error - {e}")
    else:
        print(f"   ✗ Skipped (no container)")

    await page.screenshot(path='debug_3_final.png')
    print(f"\n✓ Final screenshot saved: debug_3_final.png")

    print(f"\n=== MANUAL INSPECTION ===")
    print(f"Browser window is open. Please:")
    print(f"1. Look at the browser window")
    print(f"2. Check if reviews are visible")
    print(f"3. Right-click on a review → Inspect")
    print(f"4. Find the parent container class")
    print(f"5. Find the individual review element class")
    print(f"\nPress Enter to close browser...")
    input()

    await browser.close()
    await playwright.stop()

    print(f"\n✓ Debug complete. Check screenshots for details.")


if __name__ == '__main__':
    # Replace with your URL
    url = "https://www.google.com/maps/place/%D7%99%D7%A8%D7%99%D7%93+%D7%94%D7%97%D7%A9%D7%9E%D7%9C%E2%80%AD/@31.991078,34.876977,17z/data=!3m1!4b1!4m6!3m5!1s0x1502caba776b7693:0x70f05b0377467d37!8m2!3d31.991078!4d34.876977!16s%2Fg%2F11h7s42pz3?entry=ttu&g_ep=EgoyMDI2MDIxMS4wIKXMDSoASAFQAw%3D%3D"

    asyncio.run(debug_scrape(url))
