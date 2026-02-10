"""Text similarity detection rule - finds duplicate/copied reviews"""
from typing import Dict, List
from itertools import combinations
from fuzzywuzzy import fuzz
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fraud_detection.base import FraudRule
from config import TEXT_SIMILARITY_THRESHOLD


class TextSimilarityRule(FraudRule):
    """
    Detects duplicate or highly similar reviews

    Uses Levenshtein distance to compare all review pairs.
    Flags reviews with >85% similarity as potential fraud.
    """

    def __init__(self, threshold: int = TEXT_SIMILARITY_THRESHOLD):
        """
        Args:
            threshold: Similarity percentage threshold (0-100)
        """
        self.threshold = threshold

    def analyze(self, reviews: List[Dict], business_data: Dict) -> Dict:
        """
        Find similar review pairs

        Returns:
            {
                'score': 0-100 (percentage of reviews involved in similar pairs),
                'flagged_items': [{'review1_id', 'review2_id', 'similarity', 'text1', 'text2'}],
                'reasoning': str
            }
        """
        if len(reviews) < 2:
            return {
                'score': 0.0,
                'flagged_items': [],
                'reasoning': 'Insufficient reviews for comparison'
            }

        similar_pairs = []

        # Compare all review pairs
        for r1, r2 in combinations(reviews, 2):
            # Skip if same reviewer (could be legitimate edits)
            if r1.get('reviewer_id') == r2.get('reviewer_id'):
                continue

            # Skip if either review is too short
            text1 = r1.get('review_text', '')
            text2 = r2.get('review_text', '')

            if len(text1) < 20 or len(text2) < 20:
                continue

            # Calculate similarity using fuzzywuzzy
            similarity = fuzz.ratio(text1, text2)

            if similarity >= self.threshold:
                similar_pairs.append({
                    'review1_id': r1.get('id'),
                    'review2_id': r2.get('id'),
                    'similarity': similarity,
                    'text1': text1[:150],  # First 150 chars for preview
                    'text2': text2[:150],
                    'reviewer1': r1.get('reviewer_name', 'Unknown'),
                    'reviewer2': r2.get('reviewer_name', 'Unknown')
                })

        # Calculate score based on percentage of reviews involved
        unique_flagged_reviews = set()
        for pair in similar_pairs:
            unique_flagged_reviews.add(pair['review1_id'])
            unique_flagged_reviews.add(pair['review2_id'])

        score = (len(unique_flagged_reviews) / len(reviews)) * 100 if reviews else 0

        # Generate reasoning
        if len(similar_pairs) == 0:
            reasoning = "No duplicate or similar reviews detected"
        else:
            reasoning = f"Found {len(similar_pairs)} pairs of highly similar reviews (>{self.threshold}% match)"

        return {
            'score': min(score, 100.0),
            'flagged_items': similar_pairs[:10],  # Limit to top 10 for display
            'reasoning': reasoning
        }
