"""Fraud detection orchestrator - runs all fraud detection rules"""
import sys
import os
from typing import Dict, List

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fraud_detection.rules.text_similarity import TextSimilarityRule
from fraud_detection.rules.timing_analysis import TimingAnalysisRule


class FraudDetector:
    """
    Orchestrates fraud detection analysis

    Runs all enabled fraud detection rules and collects results
    """

    def __init__(self):
        """Initialize with fraud detection rules"""
        self.rules = [
            TextSimilarityRule(),
            TimingAnalysisRule()
        ]

    def analyze_business(self, reviews: List[Dict], business_data: Dict) -> Dict:
        """
        Run all fraud detection rules

        Args:
            reviews: List of review dictionaries from database
            business_data: Business information dictionary

        Returns:
            {
                'TextSimilarityRule': {'score', 'flagged_items', 'reasoning'},
                'TimingAnalysisRule': {'score', 'flagged_items', 'reasoning'},
                ...
            }
        """
        results = {}

        for rule in self.rules:
            rule_name = rule.get_name()
            try:
                result = rule.analyze(reviews, business_data)
                results[rule_name] = result
            except Exception as e:
                # If a rule fails, log error and continue
                print(f"Error running {rule_name}: {e}")
                results[rule_name] = {
                    'score': 0.0,
                    'flagged_items': [],
                    'reasoning': f"Error: {str(e)}"
                }

        return results

    def get_enabled_rules(self) -> List[str]:
        """Get list of enabled rule names"""
        return [rule.get_name() for rule in self.rules]
