import requests
from bs4 import BeautifulSoup
import logging
import time
import random

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
logger.addHandler(console_handler)

# Header pool to rotate user-agent + headers
HEADER_POOL = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:110.0) Gecko/20100101 Firefox/110.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Referer": "https://www.superiorcourt.maricopa.gov/"
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Referer": "https://www.superiorcourt.maricopa.gov/"
    },
    {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Referer": "https://www.superiorcourt.maricopa.gov/"
    }
]

def extract_docket_data(url, suspect_name):
    """
    Fetches and parses a docket page from the Maricopa County Superior Court site.

    Parameters:
    - url (str): The case detail page to visit.
    - suspect_name (str): Name for logging (not used in logic).

    Returns:
    - dict: Placeholder result with court-related fields.
    """

    headers = random.choice(HEADER_POOL)

    logger.info(f"Fetching URL: {url}")
    try:
        session = requests.Session()

        # Warm up session with homepage to get cookies
        session.get("https://www.superiorcourt.maricopa.gov/", headers=headers, timeout=10)

        # Human-like delay
        time.sleep(random.uniform(4, 7))

        # Request target page
        response = session.get(url, headers=headers, timeout=15)

        # Log basic info
        logger.debug(f"Status code: {response.status_code}")
        logger.debug(f"First 500 characters of response:\n{response.text[:500]}")

        # Check for block message
        if "server is busy" in response.text.lower():
            logger.warning("🚨 Detected 'server is busy' message in response body.")

    except requests.exceptions.RequestException as e:
        logger.exception(f"❌ Request to {url} failed.")
        return {}

    soup = BeautifulSoup(response.content, "html.parser")

    # Return placeholder structure
    return {
        "Attorney": None,
        "Crime": None,
        "Status": None,
        "Next Hearing": None,
        "Next Hearing Date": None,
        "Trial": None,
        "Sentencing": None,
        "fldX72Wdvk52dP8NG": None
    }
