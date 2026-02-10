"""Base class for fraud detection rules"""
from typing import Dict, List, Any
from abc import ABC, abstractmethod


class FraudRule(ABC):
    """Base class for all fraud detection rules"""

    @abstractmethod
    def analyze(self, reviews: List[Dict], business_data: Dict) -> Dict:
        """
        Analyze reviews and return fraud indicators

        Args:
            reviews: List of review dictionaries
            business_data: Business information

        Returns:
            {
                'score': float (0-100, higher = more suspicious),
                'flagged_items': list (specific flagged items),
                'reasoning': str (human-readable explanation)
            }
        """
        pass

    def get_name(self) -> str:
        """Get rule name"""
        return self.__class__.__name__
