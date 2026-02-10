"""Fraud scoring system - combines rule results into final score"""
from typing import Dict, List


class FraudScorer:
    """
    Calculates weighted fraud score from rule results

    For POC, using simple 50/50 split between Text Similarity and Timing Analysis
    """

    # Rule weights (must sum to 1.0)
    WEIGHTS = {
        'TextSimilarityRule': 0.6,      # 60% - Most reliable indicator
        'TimingAnalysisRule': 0.4,      # 40% - Strong indicator
    }

    def calculate_score(self, rule_results: Dict) -> Dict:
        """
        Calculate weighted fraud score (0-100)

        Args:
            rule_results: Dict of {rule_name: {'score', 'flagged_items', 'reasoning'}}

        Returns:
            {
                'overall_score': float (0-100),
                'risk_level': str ('MINIMAL', 'LOW', 'MEDIUM', 'HIGH'),
                'breakdown': {rule_name: {'score', 'weight', 'contribution', 'reasoning'}},
                'reasoning': [list of primary fraud indicators],
                'total_reviews_analyzed': int
            }
        """
        weighted_sum = 0.0
        breakdown = {}

        # Calculate weighted score
        for rule_name, result in rule_results.items():
            weight = self.WEIGHTS.get(rule_name, 0)
            score = result.get('score', 0)
            contribution = score * weight

            weighted_sum += contribution

            breakdown[rule_name] = {
                'score': round(score, 1),
                'weight': weight,
                'contribution': round(contribution, 1),
                'reasoning': result.get('reasoning', '')
            }

        # Sort by contribution to identify main fraud indicators
        sorted_rules = sorted(
            breakdown.items(),
            key=lambda x: x[1]['contribution'],
            reverse=True
        )

        # Generate primary reasoning (top contributors with score > 10)
        reasoning = []
        for rule_name, data in sorted_rules:
            if data['score'] > 10:  # Only include significant contributors
                # Clean up rule name for display
                display_name = rule_name.replace('Rule', '')
                reasoning.append(f"{display_name}: {data['reasoning']}")

        if not reasoning:
            reasoning.append("No significant fraud indicators detected")

        overall_score = round(weighted_sum, 1)

        return {
            'overall_score': overall_score,
            'risk_level': self._get_risk_level(overall_score),
            'breakdown': breakdown,
            'reasoning': reasoning
        }

    def _get_risk_level(self, score: float) -> str:
        """
        Convert numeric score to risk level

        Args:
            score: Fraud score (0-100)

        Returns:
            Risk level string
        """
        if score >= 75:
            return 'HIGH'
        elif score >= 50:
            return 'MEDIUM'
        elif score >= 25:
            return 'LOW'
        else:
            return 'MINIMAL'
