import os
import requests
import time
import logging
from bs4 import BeautifulSoup
from datetime import datetime
from pyairtable import Api
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

AIRTABLE_API_KEY = os.environ["AIRTABLE_API_KEY"]
BASE_ID = "appwbCU6BAWOA1AQX"
TABLE_ID = "tblb0yIYr91PzghXQ"

api = Api(AIRTABLE_API_KEY)
table = api.table(BASE_ID, TABLE_ID)

TODAY = datetime.today()

# --- Static session headers with real User-Agent and Cookie ---
session = requests.Session()
retries = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504], raise_on_status=False)
session.mount("https://", HTTPAdapter(max_retries=retries))
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "Cookie": "cookiesEnabled=1; _ga=GA1.1.999643802.1729287917; _ga_Y8Q8DRN6NX=deleted; _ga_Y8Q8DRN6NX=deleted; _ga_Y8Q8DRN6NX=deleted; _gcl_au=1.1.355616172.1752169833; _ga_Q0RZTDZCMF=GS2.1.s1752169833$o3$g0$t1752169841$j52$l0$h0; _ga_W7L0KQ6EGZ=GS2.1.s1752169833$o3$g0$t1752169841$j52$l0$h0; ASPSESSIONIDSWDQTDSB=LKGDODJAIFFDHBKJODFEHOGD; _ga_Y8Q8DRN6NX=GS2.1.s1752777277$o298$g1$t1752777362$j44$l0$h0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.superiorcourt.maricopa.gov/",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "DNT": "1",
    "TE": "trailers"
})

def extract_docket_data(url, suspect_name):
    time.sleep(4)  # fixed delay to avoid throttling
    logging.info(f"Hitting {url}")

    response = session.get(url)
    logging.info(f"Received {response.status_code} from {url}")

    # Check for "server busy" or similar issues
    page_text = response.text.lower()
    known_fail_phrases = [
        "server is busy", "try again later", "temporarily unavailable",
        "an error has occurred", "could not be found", "unavailable"
    ]
    if any(phrase in page_text for phrase in known_fail_phrases):
        logging.warning(f"⚠️ Blocking message detected at {url}")
        logging.debug(response.text[:1000])
        return {}  # skip this case

    soup = BeautifulSoup(response.content, "html.parser")

    # Log the page title
    title_tag = soup.find("title")
    if title_tag:
        logging.info(f"Page title: {title_tag.get_text(strip=True)}")
    else:
        logging.warning("No <title> tag found on the page")

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

    party_sections = soup.find_all("div", id="tblForms2")
    for section in party_sections:
        labels = section.find_all("div", class_="col-4 m-visibility bold-font")
        values = section.find_all("div", class_="col-8 col-lg-3")
        for i, label in enumerate(labels):
            if label.text.strip() == "Party Name" and i < len(values):
                name = values[i].get_text(strip=True)
                if "State Of Arizona" in name:
                    for j, lbl in enumerate(labels):
                        if lbl.text.strip() == "Attorney" and j < len(values):
                            result["Attorney"] = values[j].get_text(strip=True)
                    break

    disposition_section = soup.find("div", id="tblDocket12")
    charges = []
    if disposition_section:
        rows = disposition_section.find_all("div", class_="row g-0")
        for row in rows:
            cols = row.find_all("div")
            party, description, disposition, disp_text = None, None, None, ""

            for i in range(len(cols)):
                label = cols[i].get_text(strip=True)
                if "Party Name" == label and i + 1 < len(cols):
                    party = cols[i + 1].get_text(strip=True)
                elif "Description" == label and i + 1 < len(cols):
                    description = cols[i + 1].get_text(strip=True)
                elif "Disposition" == label and i + 1 < len(cols):
                    disposition = cols[i + 1].get_text(strip=True)
                elif "Disposition" in label and i + 1 < len(cols):
                    disp_text = cols[i + 1].get_text(strip=True)

            if party and suspect_name.lower() in party.lower() and description:
                charges.append({
                    "description": description,
                    "disposition": disposition,
                    "disposition_text": disp_text,
                    "has_murder": "MURDER" in description.upper(),
                    "is_guilty": "GUILTY" in disp_text.upper(),
                    "is_empty": disp_text.strip() == ""
                })

    def pick_best_charge(charges):
        for c in charges:
            if c["is_empty"]:
                return c
        for c in charges:
            if c["is_guilty"]:
                return c
        for c in charges:
            if c["has_murder"]:
                return c
        return charges[0] if charges else None

    selected = pick_best_charge(charges)
    if selected:
        result["Crime"] = selected["description"]
        result["Status"] = selected["disposition"]

    calendar = soup.find(id="tblForms4")
    if calendar:
        rows = calendar.find_all("div", class_="row g-0")
        future_dates = []
        for row in rows:
            date_div = row.find("div", class_="col-6 col-lg-2")
            event_div = row.find("div", class_="col-6 col-lg-8")
            if date_div and event_div:
                try:
                    date_obj = datetime.strptime(date_div.text.strip(), "%m/%d/%Y")
                    event_str = event_div.text.strip()
                    if date_obj >= TODAY:
                        future_dates.append((date_obj, event_str))
                except:
                    continue

        if future_dates:
            future_dates.sort()
            next_hearing_date, next_hearing = future_dates[0]
            result["Next Hearing Date"] = next_hearing_date.strftime("%Y-%m-%d")
            result["Next Hearing"] = next_hearing

            for dt, ev in future_dates:
                if "TRIAL" in ev.upper() and not result["Trial"]:
                    result["Trial"] = dt.strftime("%Y-%m-%d")
                if "SENTENCING" in ev.upper() and not result["Sentencing"]:
                    result["Sentencing"] = dt.strftime("%Y-%m-%d")

    filings = soup.find("div", id="tblForms3")
    latest_date = None
    latest_description = None
    if filings:
        rows = filings.find_all("div", class_="row g-0")
        for row in rows:
            divs = row.find_all("div")
            date_found = None
            description = None
            for i in range(len(divs)):
                if "Filing Date" in divs[i].text and i + 1 < len(divs):
                    try:
                        date_found = datetime.strptime(divs[i + 1].text.strip(), "%m/%d/%Y")
                    except:
                        pass
                if "Description" in divs[i].text and i + 1 < len(divs):
                    description = divs[i + 1].text.strip()
            if date_found and description:
                if not latest_date or date_found > latest_date:
                    latest_date = date_found
                    latest_description = description

    if latest_description:
        result["fldX72Wdvk52dP8NG"] = latest_description

    return result

# --- MAIN LOOP ---
records = table.all(fields=["Suspect Name", "Court Docket"])
for record in records:
    fields = record.get("fields", {})
    suspect = fields.get("Suspect Name")
    docket_url = fields.get("Court Docket")

    if not suspect or not docket_url:
        continue

    try:
        print(f"Processing {suspect}")
        data = extract_docket_data(docket_url, suspect)
        if data:
            print(f"Updating: {data}")
            table.update(record["id"], data)
        else:
            print(f"Skipped update for {suspect} due to error page")
    except Exception as e:
        logging.error(f"Error processing {suspect}: {e}")
