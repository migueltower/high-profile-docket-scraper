import os
import time
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Enable debug logging for HTTP requests
import http.client as http_client
http_client.HTTPConnection.debuglevel = 1
logging.getLogger("urllib3").setLevel(logging.DEBUG)

TODAY = datetime.today()

# --- Enhanced session ---
session = requests.Session()
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
retries = Retry(
    total=5,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504],
    raise_on_status=False,
)
session.mount("https://", HTTPAdapter(max_retries=retries))
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.superiorcourt.maricopa.gov/",
    "Connection": "keep-alive",
    "DNT": "1",
    "TE": "trailers",
    # Add cookie string if needed
    # "Cookie": "insert_your_updated_cookie_here"
})

def extract_docket_data(url, suspect_name):
    time.sleep(4)
    logging.info(f"Hitting {url}")
    logging.info(f"Request headers: {session.headers}")

    try:
        start_time = time.time()
        response = session.get(url, timeout=30)
        duration = round(time.time() - start_time, 2)
        logging.info(f"Received {response.status_code} from {url} in {duration}s")
    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed: {e}")
        return {}

    page_text = response.text.lower()
    known_fail_phrases = [
        "server is busy", "try again later", "temporarily unavailable",
        "an error has occurred", "could not be found", "unavailable"
    ]
    if any(phrase in page_text for phrase in known_fail_phrases):
        logging.warning(f"⚠️ Blocking message detected at {url}")
        preview = response.text[:1000].strip().replace("\n", " ")
        logging.debug(f"HTML preview:\n{preview}")

        # Optional: Save entire response for offline inspection
        fname = f"blocked_{suspect_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(response.text)
        logging.info(f"Saved full HTML to {fname}")
        return {}

    soup = BeautifulSoup(response.content, "html.parser")
    title_tag = soup.find("title")
    if title_tag:
        logging.info(f"Page title: {title_tag.get_text(strip=True)}")
    else:
        logging.warning("No <title> tag found on the page")

    # Continue with your current scraping logic...
    # [REPLACE this comment with the rest of your current result-parsing logic]
    return {}
