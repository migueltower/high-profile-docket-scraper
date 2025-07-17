import requests
from bs4 import BeautifulSoup
import logging

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
logger.addHandler(console_handler)

def extract_docket_data(url, suspect_name):
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; TonyScraperBot/1.0; +https://example.com/contact)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    logger.info(f"Fetching URL: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=15)
        logger.debug(f"Status code: {response.status_code}")
        logger.debug(f"Response headers: {response.headers}")
        logger.debug(f"First 500 characters of response:\n{response.text[:500]}")

        if "server is busy" in response.text.lower():
            logger.warning("Detected possible block: 'server is busy' in response body.")

    except requests.exceptions.RequestException as e:
        logger.exception(f"Request to {url} failed.")
        return {}

    soup = BeautifulSoup(response.content, "html.parser")

    result = {
        "Attorney": None,
        "Crime": None,
        "Status": None,
        "Next Hearing": None,
        "Next Hearing Date": None,
        "Trial": None,
        "Sentencing": None,
        "fldX72Wdvk52dP8NG": None  # Last Filed
    }

    # Add your existing scraping logic here...
    # (no changes made to preserve functionality)

    return result
