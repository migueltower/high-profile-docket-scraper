import os
import requests
import time
import random
import logging
from datetime import datetime
from bs4 import BeautifulSoup
from pyairtable import Api

# ─────────────────────────────
# Logger Configuration
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console = logging.StreamHandler()
console.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
logger.addHandler(console)

# Airtable & Court Site Setup
AIRTABLE_API_KEY = os.environ["AIRTABLE_API_KEY"]
BASE_ID = "appwbCU6BAWOA1AQX"
TABLE_ID = "tblb0yIYr91PzghXQ"
BASE_URL = "https://www.superiorcourt.maricopa.gov/docket/CriminalCourtCases/caseInfo.asp?caseNumber="
TODAY = datetime.today()

HEADER_POOL = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:110.0) Gecko/20100101 Firefox/110.0",
        "Referer": "https://www.superiorcourt.maricopa.gov/"
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Referer": "https://www.superiorcourt.maricopa.gov/"
    },
    {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
        "Referer": "https://www.superiorcourt.maricopa.gov/"
    }
]

def extract_docket_data(url, suspect_name):
    headers = random.choice(HEADER_POOL)
    session = requests.Session()

    try:
        # Seed with homepage cookies and delay
        session.get("https://www.superiorcourt.maricopa.gov/", headers=headers, timeout=10)
        time.sleep(random.uniform(4, 7))

        response = session.get(url, headers=headers, timeout=15)
        if "server is busy" in response.text.lower():
            logger.warning("⚠️ Server busy message detected.")
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

        # Attorney
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

        # Charges
        charges = []
        disposition_section = soup.find("div", id="tblDocket12")
        if disposition_section:
            rows = disposition_section.find_all("div", class_="row g-0")
            for row in rows:
                divs = row.find_all("div")
                party = description = disposition = disp_text = None
                for i in range(len(divs)):
                    txt = divs[i].get_text(strip=True)
                    if txt == "Party Name" and i+1 < len(divs):
                        party = divs[i+1].get_text(strip=True)
                    elif txt == "Description" and i+1 < len(divs):
                        description = divs[i+1].get_text(strip=True)
                    elif txt == "Disposition" and i+1 < len(divs):
                        disposition = divs[i+1].get_text(strip=True)
                    elif "Disposition" in txt and i+1 < len(divs):
                        disp_text = divs[i+1].get_text(strip=True)
                if party and suspect_name.lower() in party.lower() and description:
                    charges.append({
                        "description": description,
                        "disposition": disposition,
                        "disposition_text": disp_text,
                        "has_murder": "MURDER" in description.upper(),
                        "is_guilty": "GUILTY" in disp_text.upper(),
                        "is_empty": disp_text.strip() == ""
                    })

        def pick_best(charges):
            for c in charges:
                if c["is_empty"]: return c
            for c in charges:
                if c["is_guilty"]: return c
            for c in charges:
                if c["has_murder"]: return c
            return charges[0] if charges else None

        selected = pick_best(charges)
        if selected:
            result["Crime"] = selected["description"]
            result["Status"] = selected["disposition"]

        # Calendar dates
        calendar = soup.find(id="tblForms4")
        if calendar:
            rows = calendar.find_all("div", class_="row g-0")
            future = []
            for row in rows:
                date_div = row.find("div", class_="col-6 col-lg-2")
                event_div = row.find("div", class_="col-6 col-lg-8")
                if date_div and event_div:
                    try:
                        date = datetime.strptime(date_div.text.strip(), "%m/%d/%Y")
                        event = event_div.text.strip()
                        if date >= TODAY:
                            future.append((date, event))
                    except:
                        continue
            if future:
                future.sort()
                next_date, next_event = future[0]
                result["Next Hearing Date"] = next_date.strftime("%Y-%m-%d")
                result["Next Hearing"] = next_event
                for dt, ev in future:
                    if "TRIAL" in ev.upper() and not result["Trial"]:
                        result["Trial"] = dt.strftime("%Y-%m-%d")
                    if "SENTENCING" in ev.upper() and not result["Sentencing"]:
                        result["Sentencing"] = dt.strftime("%Y-%m-%d")

        # Last filing
        filings = soup.find("div", id="tblForms3")
        latest_date = None
        latest_desc = None
        if filings:
            for row in filings.find_all("div", class_="row g-0"):
                divs = row.find_all("div")
                date, desc = None, None
                for i in range(len(divs)):
                    if "Filing Date" in divs[i].text and i+1 < len(divs):
                        try: date = datetime.strptime(divs[i+1].text.strip(), "%m/%d/%Y")
                        except: pass
                    if "Description" in divs[i].text and i+1 < len(divs):
                        desc = divs[i+1].text.strip()
                if date and desc and (not latest_date or date > latest_date):
                    latest_date = date
                    latest_desc = desc
        if latest_desc:
            result["fldX72Wdvk52dP8NG"] = latest_desc

        return result

    except requests.exceptions.RequestException as e:
        logger.exception(f"❌ Failed to fetch {url}")
        return {}

def main():
    api = Api(AIRTABLE_API_KEY)
    table = api.table(BASE_ID, TABLE_ID)
    logger.info("🔍 Pulling Airtable records...")

    records = table.all(fields=["Suspect Name", "Court Docket"])
    for record in records:
        fields = record.get("fields", {})
        name = fields.get("Suspect Name")
        url = fields.get("Court Docket")
        if not name or not url:
            continue
        logger.info(f"🎯 Scraping {name}")
        try:
            data = extract_docket_data(url, name)
            logger.info(f"✏️ Updating: {data}")
            table.update(record["id"], data)
        except Exception as e:
            logger.error(f"❌ Error processing {name}: {e}")

if __name__ == "__main__":
    main()
