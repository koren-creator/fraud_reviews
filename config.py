"""Configuration settings for Fraud Review Detection System"""
import os

# Base directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Database
DATABASE_PATH = os.path.join(BASE_DIR, 'data', 'fraud_detection.db')

# Flask settings
SECRET_KEY = 'dev-secret-key-change-in-production'
DEBUG = True

# Scraping settings
SCRAPING_DELAY_MIN = 2  # Minimum delay in seconds
SCRAPING_DELAY_MAX = 5  # Maximum delay in seconds
MAX_REVIEWS_TO_SCRAPE = 100  # Maximum number of reviews to scrape per business (for performance)
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Cache settings
CACHE_DURATION_HOURS = 24  # Re-scrape if data older than 24 hours

# Fraud detection thresholds
TEXT_SIMILARITY_THRESHOLD = 85  # Percent similarity to flag duplicate reviews
EMOJI_DENSITY_THRESHOLD = 3  # Emojis per 100 characters
REVIEW_BURST_MULTIPLIER = 3  # Flag days with 3x average reviews
