import requests
from bs4 import BeautifulSoup
import logging
import time
import random

# Configure logger to output debug-level messages to the console
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
logger.addHandler(console_handler)

# Function to extract docket data from a Maricopa County case URL
def extract_docket_data(url, suspect_name):
    """
    Sends a GET request to the provided case URL and parses the response for specific
    content such as server errors. Returns a dictionary with placeholders for relevant court data.

    Parameters:
    - url (str): The case information page URL.
    - suspect_name (str): The name of the person associated with the case (currently unused in logic).

    Returns:
    - dict: A dictionary containing fields for attorney, crime, court dates, and other relevant info.
    """

    # Use more realistic browser-like headers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.superiorcourt.maricopa.gov/",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

    # Log the URL being fetched
    logger.info(f"Fetching URL: {url}")

    try:
        # Create a session and sleep briefly to mimic human browsing
        session = requests.Session()
        time.sleep(random.uniform(1.2, 3.5))  # Random delay to reduce bot-like behavior
        response = session.get(url, headers=headers, timeout=15)

        # Log response details for debugging
        logger.debug(f"Status code: {response.status_code}")
        logger.debug(f"Response headers: {response.headers}")
        logger.debug(f"First 500 characters of response:\n{response.text[:500]}")

        # Check if site is throttling requests with "server is busy" message
        if "server is busy" in response.text.lower():
            logger.warning("Detected possible block: 'server is busy' in response body.")

    except requests.exceptions.RequestException as e:
        # Log any request failures and return an empty result
        logger.exception(f"Request to {url} failed.")
        return {}

    # Parse the HTML using BeautifulSoup
    soup = BeautifulSoup(response.content, "html.parser")

    # Initialize empty result dictionary with standard court-related fields
    result = {
        "Attorney": None,
        "Crime": None,
        "Status": None,
        "Next Hearing": None,
        "Next Hearing Date": None,
        "Trial": None,
        "Sentencing": None,
        "fldX72Wdvk52dP8NG": None  # This may be a field ID for "Last Filed"
    }

    return result
