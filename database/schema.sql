-- Fraud Review Detection System Database Schema

-- Businesses table
CREATE TABLE IF NOT EXISTS businesses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    address TEXT,
    category TEXT,
    total_reviews INTEGER,
    average_rating REAL,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_analyzed TIMESTAMP
);

-- Reviewers table
CREATE TABLE IF NOT EXISTS reviewers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    google_id TEXT UNIQUE,
    total_reviews_count INTEGER,
    account_age_days INTEGER,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, total_reviews_count)
);

-- Reviews table
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id INTEGER NOT NULL,
    reviewer_id INTEGER NOT NULL,
    review_text TEXT,
    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    review_date TIMESTAMP NOT NULL,
    language TEXT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE,
    FOREIGN KEY (reviewer_id) REFERENCES reviewers(id) ON DELETE CASCADE
);

-- Analysis results table
CREATE TABLE IF NOT EXISTS analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id INTEGER NOT NULL,
    fraud_score REAL NOT NULL CHECK(fraud_score BETWEEN 0 AND 100),
    total_reviews_analyzed INTEGER,
    flagged_reviews_count INTEGER,

    -- Individual signal scores (0-100 each)
    text_similarity_score REAL,
    ai_generated_score REAL,
    rating_distribution_score REAL,
    account_age_score REAL,
    timing_burst_score REAL,
    emoji_density_score REAL,

    -- Detailed findings (JSON)
    similar_review_pairs TEXT,
    timing_clusters TEXT,
    suspicious_reviewers TEXT,
    ai_flagged_reviews TEXT,

    analysis_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_businesses_url ON businesses(url);
CREATE INDEX IF NOT EXISTS idx_reviews_business ON reviews(business_id);
CREATE INDEX IF NOT EXISTS idx_reviews_reviewer ON reviews(reviewer_id);
CREATE INDEX IF NOT EXISTS idx_reviews_date ON reviews(review_date);
CREATE INDEX IF NOT EXISTS idx_analysis_business ON analysis_results(business_id);
