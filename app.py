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
        print(f"\n=== STARTING SCRAPE ===")
        print(f"URL: {final_url}")
        scraper = GoogleMapsScraper(headless=True)
        result = asyncio.run(scrape_and_analyze(scraper, final_url))

        # VALIDATION: Check if scraping actually worked
        if not result:
            return render_template('index.html', error="Scraping failed: No data returned")

        if 'reviews' not in result or len(result['reviews']) == 0:
            error_msg = f"No reviews found. Business data: {result.get('business', {}).get('name', 'Unknown')}"
            print(f"ERROR: {error_msg}")
            print(f"DEBUG: Result keys: {result.keys()}")
            print(f"DEBUG: Business data: {result.get('business', {})}")

            # Save debug screenshots to help diagnose
            print(f"DEBUG: Check debug_*.png screenshots in the fraud_review folder")

            return render_template('index.html', error=error_msg + " - Check console logs and debug screenshots for details")

        print(f"✓ Scraped {len(result['reviews'])} reviews successfully")
        print(f"✓ Business: {result['business']['name']}")

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR during scraping:\n{error_details}")
        return render_template('index.html', error=f"Error scraping reviews: {str(e)}")

    # Save to database
    try:
        print(f"\n=== SAVING TO DATABASE ===")
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

    # Reconstruct breakdown dict for template
    from fraud_detection.scoring import FraudScorer
    scorer = FraudScorer()

    analysis['breakdown'] = {}
    analysis['reasoning'] = []

    # Reconstruct breakdown for each rule
    if analysis.get('text_similarity_score', 0) > 0:
        weight = scorer.WEIGHTS.get('TextSimilarityRule', 0)
        score = analysis['text_similarity_score']
        analysis['breakdown']['TextSimilarityRule'] = {
            'score': score,
            'weight': weight,
            'contribution': round(score * weight, 1),
            'reasoning': 'Text similarity analysis'
        }
        if score > 10:
            analysis['reasoning'].append(f"Text Similarity: {score:.1f}% of reviews are similar")

    if analysis.get('timing_burst_score', 0) > 0:
        weight = scorer.WEIGHTS.get('TimingAnalysisRule', 0)
        score = analysis['timing_burst_score']
        analysis['breakdown']['TimingAnalysisRule'] = {
            'score': score,
            'weight': weight,
            'contribution': round(score * weight, 1),
            'reasoning': 'Timing cluster analysis'
        }
        if score > 10:
            analysis['reasoning'].append(f"Timing Clusters: {score:.1f}% of reviews in suspicious clusters")

    # Add overall_score and risk_level if not already present
    if 'overall_score' not in analysis:
        analysis['overall_score'] = analysis.get('fraud_score', 0)

    if 'risk_level' not in analysis:
        score = analysis['overall_score']
        if score >= 75:
            analysis['risk_level'] = 'HIGH'
        elif score >= 50:
            analysis['risk_level'] = 'MEDIUM'
        elif score >= 25:
            analysis['risk_level'] = 'LOW'
        else:
            analysis['risk_level'] = 'MINIMAL'

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


@app.route('/qa/test-scraper', methods=['GET', 'POST'])
def qa_test_scraper():
    """QA endpoint to test scraper directly"""
    if request.method == 'GET':
        return '''
        <html dir="rtl">
        <head><title>QA: Test Scraper</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h1>🔧 QA: Test Scraper</h1>
            <form method="POST">
                <input type="text" name="url" placeholder="Google Maps URL" style="width: 500px; padding: 10px;">
                <button type="submit" style="padding: 10px 20px;">Test Scrape</button>
            </form>
        </body>
        </html>
        '''

    url = request.form.get('url', '').strip()
    if not url:
        return "Error: No URL provided", 400

    try:
        from scraper.url_parser import parse_google_maps_url
        parsed = parse_google_maps_url(url)

        output = []
        output.append("<html><body style='font-family: monospace; padding: 20px;'>")
        output.append("<h2>QA Test Results</h2>")
        output.append(f"<p><strong>Original URL:</strong> {url}</p>")
        output.append(f"<p><strong>Parsed valid:</strong> {parsed['is_valid']}</p>")
        output.append(f"<p><strong>Final URL:</strong> {parsed['final_url']}</p>")
        output.append(f"<p><strong>Business name:</strong> {parsed.get('business_name', 'N/A')}</p>")

        if not parsed['is_valid']:
            output.append("<p style='color: red;'><strong>ERROR: Invalid URL</strong></p>")
            output.append("</body></html>")
            return ''.join(output)

        output.append("<hr><h3>Starting scraper...</h3>")
        output.append("<pre>")

        scraper = GoogleMapsScraper(headless=True)
        result = asyncio.run(scrape_and_analyze(scraper, parsed['final_url']))

        output.append(f"Business Name: {result['business']['name']}\n")
        output.append(f"Total Reviews: {result['business'].get('total_reviews', 0)}\n")
        output.append(f"Average Rating: {result['business'].get('average_rating', 0)}\n")
        output.append(f"\nReviews Scraped: {len(result['reviews'])}\n\n")

        if len(result['reviews']) > 0:
            output.append("First 3 reviews:\n")
            for i, review in enumerate(result['reviews'][:3], 1):
                output.append(f"\nReview {i}:\n")
                output.append(f"  Reviewer: {review['reviewer_name']}\n")
                output.append(f"  Rating: {review['rating']}\n")
                output.append(f"  Date: {review['timestamp']}\n")
                output.append(f"  Text: {review['text'][:100]}...\n")
        else:
            output.append("<span style='color: red;'>WARNING: No reviews found!</span>\n")

        output.append("</pre>")
        output.append("<p style='color: green;'><strong>✓ Test completed</strong></p>")
        output.append("</body></html>")

        return ''.join(output)

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"<html><body style='font-family: monospace; padding: 20px;'><h2 style='color: red;'>Error</h2><pre>{error_details}</pre></body></html>"


if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
