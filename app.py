"""Flask application for fraud review detection"""
from flask import Flask, render_template, request, redirect, url_for
import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper.url_parser import parse_google_maps_url
from scraper.playwright_scraper import GoogleMapsScraper
from fraud_detection.detector import FraudDetector
from fraud_detection.scoring import FraudScorer
from database.models import (
    get_db_connection, save_business, save_reviewer,
    save_reviews, save_analysis_results, get_business_by_url,
    get_reviews_by_business, get_latest_analysis
)
from config import DATABASE_PATH

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'


@app.route('/')
def index():
    """Home page with URL input form"""
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    """Analyze a business from Google Maps URL"""
    url = request.form.get('url', '').strip()

    # Validate URL
    parsed = parse_google_maps_url(url)
    if not parsed['is_valid']:
        return render_template('index.html', error="Invalid Google Maps URL. Please check and try again.")

    # Use final URL after redirects
    final_url = parsed['final_url']

    # Check if already analyzed (caching)
    conn = get_db_connection(DATABASE_PATH)
    existing_business = get_business_by_url(conn, final_url)

    if existing_business and existing_business.get('last_analyzed'):
        # Use cached results
        business_id = existing_business['id']
        return redirect(url_for('report', business_id=business_id))

    # Scrape reviews
    try:
        scraper = GoogleMapsScraper(headless=True)
        result = asyncio.run(scrape_and_analyze(scraper, final_url))
    except Exception as e:
        return render_template('index.html', error=f"Error scraping reviews: {str(e)}")

    # Save to database
    try:
        business_data = result['business']
        business_data['url'] = final_url
        business_id = save_business(conn, business_data)

        # Save reviews
        reviews_to_save = []
        for review in result['reviews']:
            # Save reviewer first
            reviewer_data = {
                'name': review['reviewer_name'],
                'total_reviews_count': review.get('reviewer_total_reviews', 1)
            }
            reviewer_id = save_reviewer(conn, reviewer_data)

            reviews_to_save.append({
                'reviewer_id': reviewer_id,
                'review_text': review['text'],
                'rating': review['rating'],
                'review_date': review['timestamp'],
                'language': review.get('language', 'en')
            })

        save_reviews(conn, business_id, reviews_to_save)

        # Run fraud detection
        reviews_from_db = get_reviews_by_business(conn, business_id)
        detector = FraudDetector()
        rule_results = detector.analyze_business(reviews_from_db, business_data)

        # Calculate score
        scorer = FraudScorer()
        final_score = scorer.calculate_score(rule_results)

        # Save analysis results
        save_analysis_results(
            conn,
            business_id,
            final_score['overall_score'],
            final_score['breakdown'],
            rule_results
        )

        # Update last_analyzed timestamp
        from database.models import update_business_analyzed_time
        update_business_analyzed_time(conn, business_id)

        conn.close()

        return redirect(url_for('report', business_id=business_id))

    except Exception as e:
        return render_template('index.html', error=f"Error analyzing reviews: {str(e)}")


@app.route('/report/<int:business_id>')
def report(business_id):
    """Display fraud detection report"""
    conn = get_db_connection(DATABASE_PATH)

    # Get business data
    from database.models import get_business_by_id
    business = get_business_by_id(conn, business_id)

    if not business:
        return "Business not found", 404

    # Get reviews
    reviews = get_reviews_by_business(conn, business_id)

    # Get analysis results
    analysis = get_latest_analysis(conn, business_id)

    if not analysis:
        return "Analysis not found", 404

    conn.close()

    # Prepare data for template
    return render_template(
        'report.html',
        business=business,
        reviews=reviews,
        analysis=analysis,
        total_reviews=len(reviews)
    )


async def scrape_and_analyze(scraper, url):
    """Helper function to scrape reviews"""
    try:
        await scraper.initialize()
        result = await scraper.scrape_business(url)
        return result
    finally:
        await scraper.close()


if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
