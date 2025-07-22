import requests
from bs4 import BeautifulSoup
from pyairtable import Api
import logging
import time
import random
import os

# Logging setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
logger.addHandler(console_handler)

logger.info("📢 Scraper started")

AIRTABLE_API_KEY = os.environ["AIRTABLE_API_KEY"]
BASE_ID = "appwbCU6BAWOA1AQX"
TABLE_ID = "tblb0yIYr91PzghXQ"
BASE_URL = "https://www.superiorcourt.maricopa.gov/docket/CriminalCourtCases/caseInfo.asp?caseNumber="

def extract_docket_data(url, suspect_name):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.superiorcourt.maricopa.gov/",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

    logger.info(f"Fetching URL: {url}")
    try:
        session = requests.Session()
        time.sleep(random.uniform(1.2, 3.5))
        response = session.get(url, headers=headers, timeout=15)

        logger.debug(f"Status code: {response.status_code}")
        logger.debug(f"First 500 characters of response:\n{response.text[:500]}")

        if "server is busy" in response.text.lower():
            logger.warning("Detected 'server is busy' in response body.")

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
        "fldX72Wdvk52dP8NG": None
    }

    # Add scraping logic here if needed

    return result

def main():
    api = Api(AIRTABLE_API_KEY)
    table = api.table(BASE_ID, TABLE_ID)

    logger.info("🔍 Pulling Airtable records...")
    records = table.all(fields=["Suspect Name", "Case #"])

    for record in records:
        fields = record.get("fields", {})
        case_number = fields.get("Case #")
        suspect = fields.get("Suspect Name", "Unknown")

        if not case_number:
            continue

        url = BASE_URL + case_number
        result = extract_docket_data(url, suspect)

        logger.info(f"🎯 Case {case_number} | Suspect: {suspect}")
        logger.info(f"➡️ Scraped Result: {result}")

if __name__ == "__main__":
    main()
