"""Google Maps URL parser and validator"""
import re
from urllib.parse import urlparse, parse_qs, unquote
from typing import Dict, Optional
import requests


def parse_google_maps_url(url: str) -> Dict:
    """
    Parse and validate Google Maps URL

    Handles formats:
    - https://www.google.com/maps/place/Business+Name/@31.123,34.123,17z
    - https://maps.app.goo.gl/abc123 (short URLs - follows redirect)
    - https://www.google.com/search?q=business+name&... (search URLs)

    Returns:
        {
            'is_valid': bool,
            'original_url': str,
            'final_url': str,  # After following redirects
            'business_name': str or None,
            'place_id': str or None,
            'coordinates': {'lat': float, 'lng': float} or None
        }
    """
    result = {
        'is_valid': False,
        'original_url': url,
        'final_url': url,
        'business_name': None,
        'place_id': None,
        'coordinates': None
    }

    if not url or not isinstance(url, str):
        return result

    # Check if it's a Google Maps URL
    if not is_google_maps_url(url):
        return result

    # Handle short URLs (goo.gl) - follow redirect
    if 'goo.gl' in url or 'maps.app.goo.gl' in url:
        try:
            final_url = follow_redirect(url)
            result['final_url'] = final_url
            url = final_url
        except Exception as e:
            print(f"Error following redirect: {e}")
            return result

    parsed = urlparse(url)

    # Extract business name from /place/ path
    place_match = re.search(r'/place/([^/@]+)', parsed.path)
    if place_match:
        business_name = place_match.group(1)
        # Decode URL encoding and replace + with spaces
        business_name = unquote(business_name).replace('+', ' ')
        result['business_name'] = business_name

    # Extract coordinates from @lat,lng format
    coords_match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', parsed.path)
    if coords_match:
        lat, lng = coords_match.groups()
        result['coordinates'] = {'lat': float(lat), 'lng': float(lng)}

    # Extract place_id from query parameters
    query_params = parse_qs(parsed.query)
    if 'ftid' in query_params:
        result['place_id'] = query_params['ftid'][0]
    elif 'cid' in query_params:
        result['place_id'] = query_params['cid'][0]

    # Mark as valid if we found at least business name or coordinates
    if result['business_name'] or result['coordinates']:
        result['is_valid'] = True

    return result


def is_google_maps_url(url: str) -> bool:
    """Check if URL is a Google Maps URL"""
    google_maps_patterns = [
        r'google\.com/maps',
        r'maps\.google\.com',
        r'goo\.gl',
        r'maps\.app\.goo\.gl',
        r'google\.com/search.*maps'
    ]

    return any(re.search(pattern, url, re.IGNORECASE) for pattern in google_maps_patterns)


def follow_redirect(url: str, max_redirects: int = 5) -> str:
    """
    Follow URL redirects and return final URL

    Args:
        url: Short URL to follow
        max_redirects: Maximum number of redirects to follow

    Returns:
        Final URL after all redirects
    """
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        return response.url
    except Exception as e:
        # If HEAD fails, try GET
        try:
            response = requests.get(url, allow_redirects=True, timeout=10)
            return response.url
        except Exception:
            raise e


def normalize_url(url: str) -> str:
    """
    Normalize Google Maps URL for caching/comparison

    Removes unnecessary parameters and standardizes format
    """
    parsed_result = parse_google_maps_url(url)

    if not parsed_result['is_valid']:
        return url

    # Use final URL after redirects
    return parsed_result['final_url']


# Example usage and testing
if __name__ == '__main__':
    # Test URLs
    test_urls = [
        'https://www.google.com/maps/place/Business+Name/@31.123456,34.123456,17z',
        'https://maps.app.goo.gl/abc123',
        'https://www.google.com/search?q=business+name',
        'https://example.com',  # Invalid
        '',  # Invalid
    ]

    for test_url in test_urls:
        print(f"\nTesting: {test_url}")
        result = parse_google_maps_url(test_url)
        print(f"Valid: {result['is_valid']}")
        if result['is_valid']:
            print(f"  Business: {result['business_name']}")
            print(f"  Coordinates: {result['coordinates']}")
