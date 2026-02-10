"""Timing analysis rule - detects review clusters posted simultaneously"""
from typing import Dict, List
from datetime import datetime
from collections import defaultdict
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fraud_detection.base import FraudRule


class TimingAnalysisRule(FraudRule):
    """
    Detects suspicious timing patterns

    Flags clusters where multiple reviews are posted within the same minute,
    which is a strong indicator of coordinated bot activity or paid review campaigns.
    """

    def __init__(self, min_cluster_size: int = 2):
        """
        Args:
            min_cluster_size: Minimum reviews in same minute to flag as cluster
        """
        self.min_cluster_size = min_cluster_size

    def analyze(self, reviews: List[Dict], business_data: Dict) -> Dict:
        """
        Find timing clusters

        Returns:
            {
                'score': 0-100 (percentage of reviews in suspicious clusters),
                'flagged_items': [{'timestamp', 'count', 'review_ids', 'reviewers'}],
                'reasoning': str
            }
        """
        if len(reviews) < 2:
            return {
                'score': 0.0,
                'flagged_items': [],
                'reasoning': 'Insufficient reviews for timing analysis'
            }

        # Group reviews by minute-level timestamp
        timestamp_buckets = defaultdict(list)

        for review in reviews:
            timestamp = review.get('review_date')

            # Handle both datetime objects and strings
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp)
                except:
                    continue
            elif not isinstance(timestamp, datetime):
                continue

            # Round to minute (remove seconds and microseconds)
            minute_timestamp = timestamp.replace(second=0, microsecond=0)
            timestamp_buckets[minute_timestamp].append(review)

        # Find clusters (multiple reviews in same minute)
        clusters = []
        for timestamp, reviews_in_bucket in timestamp_buckets.items():
            if len(reviews_in_bucket) >= self.min_cluster_size:
                clusters.append({
                    'timestamp': timestamp.isoformat(),
                    'count': len(reviews_in_bucket),
                    'review_ids': [r.get('id') for r in reviews_in_bucket],
                    'reviewers': [r.get('reviewer_name', 'Unknown') for r in reviews_in_bucket]
                })

        # Calculate score based on percentage of reviews in clusters
        reviews_in_clusters = sum(c['count'] for c in clusters)
        score = (reviews_in_clusters / len(reviews)) * 100 if reviews else 0

        # Generate reasoning
        if len(clusters) == 0:
            reasoning = "No suspicious timing patterns detected"
        else:
            max_cluster = max(clusters, key=lambda c: c['count'])
            reasoning = f"Found {len(clusters)} timing clusters. Largest cluster: {max_cluster['count']} reviews posted at {max_cluster['timestamp']}"

        return {
            'score': min(score, 100.0),
            'flagged_items': sorted(clusters, key=lambda c: c['count'], reverse=True)[:10],  # Top 10 clusters
            'reasoning': reasoning
        }
