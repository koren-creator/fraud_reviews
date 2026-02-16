"""Direct test to diagnose scraping issue"""
import asyncio
import sys
sys.path.insert(0, '.')

from scraper.playwright_scraper import GoogleMapsScraper

async def test_scrape(url):
    print(f"Testing URL: {url}\n")

    scraper = GoogleMapsScraper(headless=True)
    try:
        await scraper.initialize()
        result = await scraper.scrape_business(url)

        print(f"\n=== RESULTS ===")
        print(f"Business Name: {result['business']['name']}")
        print(f"Total Reviews in DB: {result['business'].get('total_reviews', 0)}")
        print(f"Reviews Scraped: {len(result['reviews'])}")

        if len(result['reviews']) == 0:
            print("\n❌ NO REVIEWS SCRAPED")
            print("Check debug_*.png screenshots")
        else:
            print("\n✓ SUCCESS")
            print(f"First review: {result['reviews'][0]['text'][:100]}...")

        return result
    finally:
        await scraper.close()

if __name__ == '__main__':
    url = "https://www.google.com/maps/place/%D7%99%D7%A8%D7%99%D7%93+%D7%94%D7%97%D7%A9%D7%9E%D7%9C%E2%80%AD/@31.991078,34.876977,17z/data=!4m8!3m7!1s0x1502caba776b7693:0x70f05b0377467d37!8m2!3d31.991078!4d34.876977!9m1!1b1!16s%2Fg%2F11h7s42pz3?entry=ttu&g_ep=EgoyMDI2MDIxMS4wIKXMDSoASAFQAw%3D%3D"

    result = asyncio.run(test_scrape(url))
