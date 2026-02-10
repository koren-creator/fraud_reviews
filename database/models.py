"""Database models and CRUD operations"""
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
import json


def get_db_connection(db_path: str) -> sqlite3.Connection:
    """Create database connection with row factory"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn


# ==================== BUSINESSES ====================

def save_business(conn: sqlite3.Connection, business_data: Dict) -> int:
    """
    Insert or update business, return business_id

    Args:
        business_data: {'url', 'name', 'address', 'category', 'total_reviews', 'average_rating'}

    Returns:
        business_id
    """
    cursor = conn.cursor()

    # Check if business exists
    cursor.execute('SELECT id FROM businesses WHERE url = ?', (business_data['url'],))
    existing = cursor.fetchone()

    if existing:
        # Update existing business
        cursor.execute('''
            UPDATE businesses
            SET name = ?, address = ?, category = ?, total_reviews = ?,
                average_rating = ?, scraped_at = CURRENT_TIMESTAMP
            WHERE url = ?
        ''', (
            business_data['name'],
            business_data.get('address'),
            business_data.get('category'),
            business_data.get('total_reviews'),
            business_data.get('average_rating'),
            business_data['url']
        ))
        conn.commit()
        return existing['id']
    else:
        # Insert new business
        cursor.execute('''
            INSERT INTO businesses (url, name, address, category, total_reviews, average_rating)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            business_data['url'],
            business_data['name'],
            business_data.get('address'),
            business_data.get('category'),
            business_data.get('total_reviews'),
            business_data.get('average_rating')
        ))
        conn.commit()
        return cursor.lastrowid


def get_business_by_url(conn: sqlite3.Connection, url: str) -> Optional[Dict]:
    """Get business by URL"""
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM businesses WHERE url = ?', (url,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_business_by_id(conn: sqlite3.Connection, business_id: int) -> Optional[Dict]:
    """Get business by ID"""
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM businesses WHERE id = ?', (business_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def update_business_analyzed_time(conn: sqlite3.Connection, business_id: int):
    """Update last_analyzed timestamp"""
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE businesses SET last_analyzed = CURRENT_TIMESTAMP WHERE id = ?',
        (business_id,)
    )
    conn.commit()


# ==================== REVIEWERS ====================

def save_reviewer(conn: sqlite3.Connection, reviewer_data: Dict) -> int:
    """
    Insert or update reviewer, return reviewer_id

    Args:
        reviewer_data: {'name', 'google_id', 'total_reviews_count', 'account_age_days'}

    Returns:
        reviewer_id
    """
    cursor = conn.cursor()

    # Try to find existing reviewer
    if reviewer_data.get('google_id'):
        cursor.execute('SELECT id FROM reviewers WHERE google_id = ?', (reviewer_data['google_id'],))
        existing = cursor.fetchone()
        if existing:
            return existing['id']

    # Check by name and total_reviews_count (composite uniqueness)
    cursor.execute(
        'SELECT id FROM reviewers WHERE name = ? AND total_reviews_count = ?',
        (reviewer_data['name'], reviewer_data.get('total_reviews_count'))
    )
    existing = cursor.fetchone()

    if existing:
        return existing['id']
    else:
        # Insert new reviewer
        cursor.execute('''
            INSERT INTO reviewers (name, google_id, total_reviews_count, account_age_days)
            VALUES (?, ?, ?, ?)
        ''', (
            reviewer_data['name'],
            reviewer_data.get('google_id'),
            reviewer_data.get('total_reviews_count'),
            reviewer_data.get('account_age_days')
        ))
        conn.commit()
        return cursor.lastrowid


# ==================== REVIEWS ====================

def save_reviews(conn: sqlite3.Connection, business_id: int, reviews: List[Dict]):
    """
    Bulk insert reviews

    Args:
        reviews: List of {'reviewer_id', 'review_text', 'rating', 'review_date', 'language'}
    """
    cursor = conn.cursor()

    review_tuples = [
        (
            business_id,
            review['reviewer_id'],
            review['review_text'],
            review['rating'],
            review['review_date'],
            review.get('language')
        )
        for review in reviews
    ]

    cursor.executemany('''
        INSERT INTO reviews (business_id, reviewer_id, review_text, rating, review_date, language)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', review_tuples)

    conn.commit()


def get_reviews_by_business(conn: sqlite3.Connection, business_id: int) -> List[Dict]:
    """Get all reviews for a business"""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            r.id,
            r.business_id,
            r.reviewer_id,
            r.review_text,
            r.rating,
            r.review_date,
            r.language,
            rv.name as reviewer_name,
            rv.total_reviews_count as reviewer_total_reviews
        FROM reviews r
        JOIN reviewers rv ON r.reviewer_id = rv.id
        WHERE r.business_id = ?
        ORDER BY r.review_date DESC
    ''', (business_id,))

    rows = cursor.fetchall()
    return [dict(row) for row in rows]


# ==================== ANALYSIS RESULTS ====================

def save_analysis_results(
    conn: sqlite3.Connection,
    business_id: int,
    fraud_score: float,
    breakdown: Dict,
    rule_results: Dict
):
    """
    Save fraud analysis results

    Args:
        business_id: Business ID
        fraud_score: Overall fraud score (0-100)
        breakdown: Score breakdown from FraudScorer
        rule_results: Raw results from all fraud rules
    """
    cursor = conn.cursor()

    # Extract individual scores
    text_similarity_score = breakdown.get('TextSimilarityRule', {}).get('score', 0)
    ai_generated_score = breakdown.get('AIGeneratedRule', {}).get('score', 0)
    rating_distribution_score = breakdown.get('RatingDistributionRule', {}).get('score', 0)
    account_age_score = breakdown.get('ReviewerProfileRule', {}).get('score', 0)
    timing_burst_score = breakdown.get('TimingAnalysisRule', {}).get('score', 0)
    emoji_density_score = breakdown.get('EmojiDensityRule', {}).get('score', 0)

    # Extract flagged items as JSON
    similar_review_pairs = json.dumps(
        rule_results.get('TextSimilarityRule', {}).get('flagged_items', [])
    )
    timing_clusters = json.dumps(
        rule_results.get('TimingAnalysisRule', {}).get('flagged_items', [])
    )
    suspicious_reviewers = json.dumps(
        rule_results.get('ReviewerProfileRule', {}).get('flagged_items', [])
    )
    ai_flagged_reviews = json.dumps(
        rule_results.get('AIGeneratedRule', {}).get('flagged_items', [])
    )

    # Count flagged reviews (rough estimate)
    flagged_reviews_count = len(rule_results.get('TextSimilarityRule', {}).get('flagged_items', []))

    # Get total reviews analyzed
    reviews = get_reviews_by_business(conn, business_id)
    total_reviews_analyzed = len(reviews)

    # Insert analysis results
    cursor.execute('''
        INSERT INTO analysis_results (
            business_id, fraud_score, total_reviews_analyzed, flagged_reviews_count,
            text_similarity_score, ai_generated_score, rating_distribution_score,
            account_age_score, timing_burst_score, emoji_density_score,
            similar_review_pairs, timing_clusters, suspicious_reviewers, ai_flagged_reviews
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        business_id, fraud_score, total_reviews_analyzed, flagged_reviews_count,
        text_similarity_score, ai_generated_score, rating_distribution_score,
        account_age_score, timing_burst_score, emoji_density_score,
        similar_review_pairs, timing_clusters, suspicious_reviewers, ai_flagged_reviews
    ))

    conn.commit()


def get_latest_analysis(conn: sqlite3.Connection, business_id: int) -> Optional[Dict]:
    """Get the latest analysis results for a business"""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM analysis_results
        WHERE business_id = ?
        ORDER BY analysis_timestamp DESC
        LIMIT 1
    ''', (business_id,))

    row = cursor.fetchone()
    if not row:
        return None

    result = dict(row)

    # Parse JSON fields
    result['similar_review_pairs'] = json.loads(result.get('similar_review_pairs', '[]'))
    result['timing_clusters'] = json.loads(result.get('timing_clusters', '[]'))
    result['suspicious_reviewers'] = json.loads(result.get('suspicious_reviewers', '[]'))
    result['ai_flagged_reviews'] = json.loads(result.get('ai_flagged_reviews', '[]'))

    return result
