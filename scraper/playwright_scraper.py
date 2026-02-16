"""Google Maps reviews scraper using Playwright"""
import asyncio
import random
import re
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from playwright.async_api import async_playwright, Page, Browser
import logging

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MAX_REVIEWS_TO_SCRAPE

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GoogleMapsScraper:
    """Scraper for Google Maps reviews using Playwright"""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None

    async def initialize(self):
        """Launch Playwright browser"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )

        context = await self.browser.new_context(
            locale='en-US',
            timezone_id='America/New_York',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        self.page = await context.new_page()
        logger.info("Browser initialized successfully")

    async def close(self):
        """Close browser and cleanup"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser closed")

    async def scrape_business(self, url: str) -> Dict:
        """
        Main scraping workflow

        Args:
            url: Google Maps business URL

        Returns:
            {
                'business': {name, address, category, total_reviews, average_rating},
                'reviews': [{text, rating, timestamp, reviewer_name, reviewer_total_reviews, language}, ...]
            }
        """
        if not self.page:
            await self.initialize()

        logger.info(f"Navigating to: {url}")

        # Navigate to URL
        await self.page.goto(url, wait_until='domcontentloaded', timeout=60000)
        await self._random_delay(3, 5)

        # Take screenshot for debugging
        await self.page.screenshot(path='debug_after_load.png')
        logger.info("Screenshot saved: debug_after_load.png")

        # Extract business info
        business_data = await self._extract_business_info()
        logger.info(f"Business: {business_data['name']}")

        # Try multiple approaches to get to reviews section
        logger.info("Attempting to navigate to reviews section...")

        # WAIT for page to fully load including dynamic content
        logger.info("Waiting for page to fully load (5 seconds)...")
        await asyncio.sleep(5)  # Give dynamic content time to load

        # Method 1: Click Reviews tab
        reviews_visible = False
        try:
            clicked = await self._click_reviews_tab()
            if clicked:
                await self._random_delay(2, 3)
                await self.page.screenshot(path='debug_after_click.png')
                logger.info("✓ Clicked Reviews tab, screenshot saved")
                reviews_visible = True
        except Exception as e:
            logger.warning(f"Method 1 failed: {e}")

        # Method 2: Try scrolling down to find reviews
        if not reviews_visible:
            logger.info("Trying to scroll to find reviews...")
            try:
                await self.page.evaluate('window.scrollTo(0, 800)')
                await self._random_delay(1, 2)
            except Exception as e:
                logger.warning(f"Scroll failed: {e}")

        # Sort by "Newest" (more reliable for fraud detection)
        try:
            await self._sort_by_newest()
            await self._random_delay(1, 2)
        except Exception as e:
            logger.warning(f"Could not sort by newest: {e}")

        # Scrape all reviews
        reviews = await self._scrape_all_reviews()
        logger.info(f"Scraped {len(reviews)} reviews")

        return {
            'business': business_data,
            'reviews': reviews
        }

    async def _extract_business_info(self) -> Dict:
        """Extract business name, address, rating, etc."""
        business_data = {
            'name': None,
            'address': None,
            'category': None,
            'total_reviews': 0,
            'average_rating': 0.0
        }

        try:
            # Business name - try multiple selectors
            name_selectors = [
                'h1.DUwDvf',
                'h1[class*="fontHeadline"]',
                'h1',
            ]

            for selector in name_selectors:
                try:
                    name_elem = await self.page.wait_for_selector(selector, timeout=5000)
                    if name_elem:
                        business_data['name'] = await name_elem.text_content()
                        break
                except:
                    continue

            # Average rating
            try:
                rating_elem = await self.page.query_selector('span.ceNzKf')
                if rating_elem:
                    rating_text = await rating_elem.get_attribute('aria-label')
                    if rating_text:
                        rating_match = re.search(r'(\\d+\\.\\d+)', rating_text)
                        if rating_match:
                            business_data['average_rating'] = float(rating_match.group(1))
            except Exception as e:
                logger.warning(f"Could not extract rating: {e}")

            # Total reviews count
            try:
                reviews_elem = await self.page.query_selector('span.F7nice')
                if reviews_elem:
                    reviews_text = await reviews_elem.text_content()
                    reviews_match = re.search(r'([\\d,]+)', reviews_text)
                    if reviews_match:
                        business_data['total_reviews'] = int(reviews_match.group(1).replace(',', ''))
            except Exception as e:
                logger.warning(f"Could not extract review count: {e}")

            # Address
            try:
                address_elem = await self.page.query_selector('button[data-item-id="address"]')
                if address_elem:
                    business_data['address'] = await address_elem.get_attribute('aria-label')
            except Exception as e:
                logger.warning(f"Could not extract address: {e}")

        except Exception as e:
            logger.error(f"Error extracting business info: {e}")

        return business_data

    async def _click_reviews_tab(self) -> bool:
        """
        Click the Reviews tab to show reviews
        Returns True if successfully clicked, False otherwise
        """
        # Try to find and click "Reviews" button/tab (English + Hebrew)
        # Note: May be button, div, or other element
        review_button_selectors = [
            # Specific aria-labels
            'button[aria-label*="Reviews"]',
            'button[aria-label*="ביקורות"]',  # Hebrew
            # Role=tab with text (most reliable)
            '[role="tab"]:has-text("ביקורות")',  # Hebrew reviews tab
            '[role="tab"]:has-text("Reviews")',  # English reviews tab
            # has-text for buttons
            'button:has-text("ביקורות")',  # Hebrew
            'button:has-text("Reviews")',  # English
            # Generic tab buttons
            'button.hh2c6',
            'button[jsaction*="review"]',
            # Clickable divs
            'div[role="tab"]:has-text("Reviews")',
            'div[role="tab"]:has-text("ביקורות")',
            # Tab containers
            'div.RWPxGd button',
            'button[data-tab-index]',
            # Try ANY element with reviews text (last resort)
            '*:has-text("ביקורות")',
        ]

        logger.info("Searching for Reviews button...")
        for selector in review_button_selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                logger.info(f"  Selector '{selector}': found {len(elements)} elements")

                # Check ALL matching elements, not just the first one
                for i, button in enumerate(elements):
                    try:
                        text = await button.text_content()
                        text = text.strip().lower() if text else ""
                        logger.info(f"    Element {i}: text = '{text}'")

                        # Only click if text contains "review" or Hebrew "ביקורות"
                        if 'review' in text or 'ביקורות' in text:
                            await button.click()
                            logger.info(f"✓ Clicked Reviews tab using '{selector}' (text: '{text}')")
                            return True
                        else:
                            logger.debug(f"    Skipping (not a reviews button)")
                    except Exception as e:
                        logger.debug(f"    Element {i} error: {e}")
                        continue

            except Exception as e:
                logger.debug(f"  Selector '{selector}' failed: {e}")
                continue

        # FALLBACK: Get ALL clickable elements and check manually
        logger.info("Trying fallback: checking ALL clickable elements...")
        try:
            # Get all buttons, divs, spans that might be clickable
            all_clickables = await self.page.query_selector_all('button, div[role="tab"], div[role="button"], span[role="button"], [onclick], [jsaction]')
            logger.info(f"  Found {len(all_clickables)} clickable elements total")

            # Log ALL element texts that contain Hebrew characters
            logger.info("  Logging ALL elements with Hebrew text:")
            hebrew_count = 0
            for i, elem in enumerate(all_clickables):
                try:
                    text = await elem.text_content()
                    text = text.strip()[:100] if text else ""
                    # Check if contains Hebrew characters
                    has_hebrew = any('\u0590' <= c <= '\u05FF' for c in text)
                    if has_hebrew and text:
                        logger.info(f"    [{i}] '{text}'")
                        hebrew_count += 1
                        # Stop after 50 to avoid spam
                        if hebrew_count >= 50:
                            break
                except:
                    pass
            logger.info(f"  Found {hebrew_count} elements with Hebrew text")

            for i, elem in enumerate(all_clickables):
                try:
                    # Get BOTH text_content and inner_text (different methods)
                    text_content = await elem.text_content()
                    inner_text = await elem.inner_text() if elem else ""

                    # Clean up both texts
                    text_content = text_content.strip() if text_content else ""
                    inner_text = inner_text.strip() if inner_text else ""

                    # Check both versions (don't lowercase Hebrew!)
                    if ('ביקורות' in text_content or 'ביקורות' in inner_text or
                        'review' in text_content.lower() or 'review' in inner_text.lower()):
                        logger.info(f"  ✓ FOUND IT! Element {i}: text_content='{text_content[:50]}', inner_text='{inner_text[:50]}'")
                        await elem.click()
                        logger.info(f"✓ Clicked Reviews tab using fallback method")
                        return True
                except:
                    continue

        except Exception as e:
            logger.error(f"Fallback method error: {e}")

        logger.warning("✗ Could not find Reviews tab button even with fallback")
        return False

    async def _sort_by_newest(self):
        """Sort reviews by newest"""
        try:
            # Click sort button
            sort_button = await self.page.query_selector('button[data-value="Sort"]')
            if sort_button:
                await sort_button.click()
                await self._random_delay(0.5, 1)

                # Click "Newest" option
                newest_button = await self.page.query_selector('div[data-index="1"]')
                if newest_button:
                    await newest_button.click()
                    logger.info("Sorted by newest")
        except Exception as e:
            logger.warning(f"Could not sort by newest: {e}")

    async def _scrape_all_reviews(self) -> List[Dict]:
        """
        Infinite scroll to load and scrape all reviews

        Returns:
            List of review dictionaries
        """
        reviews = []

        # Find reviews container (scrollable element)
        reviews_container_selectors = [
            'div.m6QErb.DxyBCb.kA9KIf.dS8AEf',  # 2026 selector
            'div[role="feed"]',
            'div.review-dialog-list',
            'div[class*="scrollable"]',
            'div[aria-label*="Reviews"]',
            'div[aria-label*="ביקורות"]',  # Hebrew
        ]

        reviews_container = None
        logger.info("Searching for reviews container...")
        for selector in reviews_container_selectors:
            try:
                reviews_container = await self.page.wait_for_selector(selector, timeout=10000)
                if reviews_container:
                    logger.info(f"✓ Found reviews container: {selector}")
                    break
            except Exception as e:
                logger.debug(f"  Selector '{selector}' not found")
                continue

        if not reviews_container:
            logger.error("✗ Could not find reviews container. Taking debug screenshot.")
            await self.page.screenshot(path='debug_no_container.png')
            return reviews

        last_count = 0
        no_new_reviews_count = 0
        max_scrolls = 100  # Safety limit

        # Try multiple selectors for individual review elements
        review_element_selectors = [
            'div.jftiEf',  # Old selector
            'div.fontBodyMedium',
            'div[data-review-id]',
            'div[jslog*="review"]',
            'div.MyEned',  # Possible new selector
        ]

        working_selector = None
        for selector in review_element_selectors:
            test_elements = await reviews_container.query_selector_all(selector)
            if len(test_elements) > 0:
                working_selector = selector
                logger.info(f"✓ Using review element selector: '{selector}' ({len(test_elements)} found)")
                break

        if not working_selector:
            logger.error("✗ Could not find review element selector")
            await self.page.screenshot(path='debug_no_reviews.png')
            return reviews

        for scroll_iteration in range(max_scrolls):
            # Get all review elements with the working selector
            review_elements = await reviews_container.query_selector_all(working_selector)

            logger.info(f"Scroll {scroll_iteration + 1}: Found {len(review_elements)} review elements")

            # Extract new reviews
            for elem in review_elements[last_count:]:
                review_data = await self._extract_review_data(elem)
                if review_data:
                    reviews.append(review_data)

                # Check if we've reached the maximum limit
                if len(reviews) >= MAX_REVIEWS_TO_SCRAPE:
                    logger.info(f"✓ Reached maximum review limit ({MAX_REVIEWS_TO_SCRAPE}), stopping")
                    return reviews

            # Check if new reviews loaded
            current_count = len(review_elements)
            if current_count == last_count:
                no_new_reviews_count += 1
                if no_new_reviews_count >= 3:
                    logger.info("No new reviews after 3 scrolls, stopping")
                    break
            else:
                no_new_reviews_count = 0

            last_count = current_count

            # Scroll to bottom of container
            await reviews_container.evaluate('el => el.scrollTop = el.scrollHeight')
            await self._random_delay(2, 4)

        logger.info(f"Total reviews scraped: {len(reviews)}")
        return reviews

    async def _extract_review_data(self, element) -> Optional[Dict]:
        """
        Extract individual review data

        Returns:
            {
                'text': str,
                'rating': int (1-5),
                'timestamp': datetime,
                'reviewer_name': str,
                'reviewer_total_reviews': int,
                'language': str ('he' or 'en')
            }
        """
        try:
            review_data = {}

            # Extract reviewer name
            try:
                name_elem = await element.query_selector('div.d4r55')
                if name_elem:
                    review_data['reviewer_name'] = await name_elem.text_content()
            except:
                review_data['reviewer_name'] = 'Unknown'

            # Extract rating (count filled stars)
            try:
                rating_elem = await element.query_selector('span.kvMYJc')
                if rating_elem:
                    rating_aria = await rating_elem.get_attribute('aria-label')
                    if rating_aria:
                        rating_match = re.search(r'(\\d+) star', rating_aria)
                        if rating_match:
                            review_data['rating'] = int(rating_match.group(1))
            except:
                review_data['rating'] = 5  # Default if can't extract

            # Extract review text (click "More" button if truncated)
            try:
                more_button = await element.query_selector('button.w8nwRe')
                if more_button:
                    await more_button.click()
                    await self._random_delay(0.3, 0.7)

                text_elem = await element.query_selector('span.wiI7pd')
                if text_elem:
                    review_data['text'] = await text_elem.text_content()
                else:
                    review_data['text'] = ''
            except:
                review_data['text'] = ''

            # Extract timestamp (relative time like "2 weeks ago")
            try:
                time_elem = await element.query_selector('span.rsqaWe')
                if time_elem:
                    timestamp_text = await time_elem.text_content()
                    review_data['timestamp'] = self._parse_relative_time(timestamp_text)
            except:
                review_data['timestamp'] = datetime.now()

            # Extract reviewer total reviews (from profile)
            try:
                # Click reviewer name to open profile
                reviewer_button = await element.query_selector('button.WEBjve')
                if reviewer_button:
                    await reviewer_button.click()
                    await self._random_delay(0.5, 1)

                    # Extract total reviews from profile popup
                    profile_reviews_elem = await self.page.query_selector('div.RfnDt')
                    if profile_reviews_elem:
                        profile_text = await profile_reviews_elem.text_content()
                        reviews_match = re.search(r'([\\d,]+)\\s+review', profile_text, re.IGNORECASE)
                        if reviews_match:
                            review_data['reviewer_total_reviews'] = int(reviews_match.group(1).replace(',', ''))
                        else:
                            review_data['reviewer_total_reviews'] = 1
                    else:
                        review_data['reviewer_total_reviews'] = 1

                    # Close profile popup
                    close_button = await self.page.query_selector('button[aria-label="Close"]')
                    if close_button:
                        await close_button.click()
                        await self._random_delay(0.3, 0.5)
                else:
                    review_data['reviewer_total_reviews'] = 1
            except Exception as e:
                logger.warning(f"Could not extract reviewer total reviews: {e}")
                review_data['reviewer_total_reviews'] = 1

            # Detect language
            review_data['language'] = self._detect_language(review_data['text'])

            return review_data

        except Exception as e:
            logger.error(f"Error extracting review: {e}")
            return None

    def _parse_relative_time(self, text: str) -> datetime:
        """
        Convert relative time strings to datetime

        Examples: "2 weeks ago", "1 month ago", "3 days ago"
        """
        text = text.lower()
        now = datetime.now()

        # Extract number and unit
        match = re.search(r'(\\d+)\\s+(second|minute|hour|day|week|month|year)', text)

        if not match:
            return now

        amount = int(match.group(1))
        unit = match.group(2)

        if 'second' in unit:
            delta = timedelta(seconds=amount)
        elif 'minute' in unit:
            delta = timedelta(minutes=amount)
        elif 'hour' in unit:
            delta = timedelta(hours=amount)
        elif 'day' in unit:
            delta = timedelta(days=amount)
        elif 'week' in unit:
            delta = timedelta(weeks=amount)
        elif 'month' in unit:
            delta = timedelta(days=amount * 30)
        elif 'year' in unit:
            delta = timedelta(days=amount * 365)
        else:
            return now

        return now - delta

    def _detect_language(self, text: str) -> str:
        """
        Detect if text is Hebrew or English

        Hebrew Unicode range: U+0590 to U+05FF
        """
        if not text:
            return 'en'

        hebrew_chars = sum(1 for c in text if '\\u0590' <= c <= '\\u05FF')
        total_chars = len(text)

        # If more than 30% Hebrew characters, consider it Hebrew
        if total_chars > 0 and (hebrew_chars / total_chars) > 0.3:
            return 'he'
        else:
            return 'en'

    async def _random_delay(self, min_sec: float, max_sec: float):
        """Random delay to avoid detection"""
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)


# Example usage
async def main():
    """Test scraper with example URL"""
    scraper = GoogleMapsScraper(headless=False)

    try:
        # Test URL (replace with actual Google Maps URL)
        test_url = "https://www.google.com/maps/place/..."

        result = await scraper.scrape_business(test_url)

        print(f"\\n===== BUSINESS INFO =====")
        print(f"Name: {result['business']['name']}")
        print(f"Address: {result['business']['address']}")
        print(f"Average Rating: {result['business']['average_rating']}")
        print(f"Total Reviews: {result['business']['total_reviews']}")

        print(f"\\n===== REVIEWS ({len(result['reviews'])}) =====")
        for i, review in enumerate(result['reviews'][:5], 1):
            print(f"\\nReview {i}:")
            print(f"  Reviewer: {review['reviewer_name']} ({review['reviewer_total_reviews']} reviews)")
            print(f"  Rating: {review['rating']}⭐")
            print(f"  Date: {review['timestamp']}")
            print(f"  Language: {review['language']}")
            print(f"  Text: {review['text'][:100]}...")

    finally:
        await scraper.close()


if __name__ == '__main__':
    asyncio.run(main())
