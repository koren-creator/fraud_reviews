# QA Testing Guide

## Purpose
This guide helps you verify that the fraud review detection system is working correctly.

## Quick Test Steps

### 1. Test URL Parser
Open your browser and navigate to:
```
http://localhost:5000/qa/test-scraper
```

Paste your Google Maps URL and click "Test Scrape".

**Expected Results:**
- ✓ URL should be valid
- ✓ Business name should be extracted
- ✓ Reviews should be scraped (check count > 0)
- ✓ Should show first 3 reviews with text

**If you see 0 reviews:**
- The Google Maps page structure may have changed
- Selectors in the scraper need to be updated
- The URL might not point to a business with reviews

### 2. Check Console Output

When running `python app.py`, watch the console for:

```
=== STARTING SCRAPE ===
URL: https://www.google.com/maps/...
✓ Scraped X reviews successfully
✓ Business: [Business Name]
```

**Red Flags:**
- ❌ `ERROR: No reviews found`
- ❌ `Traceback` errors
- ❌ `Could not find reviews container`

### 3. Manual Scraper Test

Run this command directly to test scraping:

```bash
cd C:\Users\Shirazi\fraud_review
python -c "
import asyncio
from scraper.playwright_scraper import GoogleMapsScraper

async def test():
    scraper = GoogleMapsScraper(headless=False)  # headless=False to see browser
    await scraper.initialize()

    # Replace with your URL
    url = 'https://www.google.com/maps/place/...'

    result = await scraper.scrape_business(url)

    print(f'Business: {result[\"business\"][\"name\"]}')
    print(f'Reviews scraped: {len(result[\"reviews\"])}')

    if len(result['reviews']) > 0:
        print('\nFirst review:')
        print(result['reviews'][0])

    await scraper.close()

asyncio.run(test())
"
```

### 4. Check Database

After a successful analysis, verify data was saved:

```bash
cd C:\Users\Shirazi\fraud_review
python -c "
import sqlite3
conn = sqlite3.connect('data/fraud_detection.db')
cursor = conn.cursor()

# Check businesses
cursor.execute('SELECT COUNT(*) FROM businesses')
print(f'Businesses: {cursor.fetchone()[0]}')

# Check reviews
cursor.execute('SELECT COUNT(*) FROM reviews')
print(f'Reviews: {cursor.fetchone()[0]}')

# Check analysis
cursor.execute('SELECT business_id, fraud_score, total_reviews_analyzed FROM analysis_results ORDER BY id DESC LIMIT 1')
result = cursor.fetchone()
if result:
    print(f'Latest analysis: Business {result[0]}, Score: {result[1]}%, Reviews: {result[2]}')
else:
    print('No analysis results found')

conn.close()
"
```

### 5. Common Issues & Fixes

#### Issue: "No reviews found"
**Cause:** Google Maps page structure changed
**Fix:** Update selectors in `scraper/playwright_scraper.py`
- Open Google Maps in Chrome
- Right-click on a review → Inspect
- Find the parent container class
- Update line 237: `review_elements = await reviews_container.query_selector_all('NEW_SELECTOR')`

#### Issue: "Could not find reviews container"
**Cause:** Reviews tab not clicked or page not loaded
**Fix:**
1. Set `headless=False` in scraper initialization (line 55 of app.py)
2. Watch what happens in the browser
3. Manually check if reviews are visible

#### Issue: Scraper returns 0 reviews but they exist on the page
**Cause:** Selector for review elements is wrong
**Fix:**
1. Run manual test with `headless=False`
2. Take screenshot with `await self.page.screenshot(path='debug.png')`
3. Inspect actual page structure
4. Update selectors

## Expected Behavior

For a business with 50+ reviews:

1. **Scraping phase:** 2-5 minutes
   - Browser launches
   - Navigates to URL
   - Clicks reviews tab
   - Scrolls through all reviews
   - Extracts text, rating, timestamp

2. **Analysis phase:** < 1 second
   - Runs text similarity detection
   - Runs timing cluster detection
   - Calculates weighted score

3. **Report phase:** Instant
   - Shows fraud score
   - Shows risk level (color-coded)
   - Lists flagged reviews
   - Shows timing clusters

## Validation Checklist

- [ ] URL parser correctly extracts business name
- [ ] Scraper finds reviews container
- [ ] Scraper extracts > 0 reviews
- [ ] Reviews have text, rating, timestamp
- [ ] Database saves business info
- [ ] Database saves all reviews
- [ ] Fraud detector runs without errors
- [ ] Analysis results saved to database
- [ ] Report page displays correctly
- [ ] Fraud score is calculated (not 0 if reviews are suspicious)
- [ ] Hebrew text displays correctly (no garbled characters)

## Debug Mode

To see what the browser is doing:

1. Edit `app.py` line 61
2. Change: `scraper = GoogleMapsScraper(headless=True)`
3. To: `scraper = GoogleMapsScraper(headless=False)`
4. Restart Flask app
5. Submit URL - you'll see browser window open

## Getting Help

If scraping still fails:

1. Run QA test endpoint: `/qa/test-scraper`
2. Copy console error output
3. Check if Google Maps layout changed
4. Update selectors based on current page structure
