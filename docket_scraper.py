import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pyairtable import Api

AIRTABLE_API_KEY = os.environ["AIRTABLE_API_KEY"]
BASE_ID = "appwbCU6BAWOA1AQX"
TABLE_ID = "tblb0yIYr91PzghXQ"

api = Api(AIRTABLE_API_KEY)
table = api.table(BASE_ID, TABLE_ID)

TODAY = datetime.today()

def extract_docket_data(url, suspect_name):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    result = {
        "Attorney": None,
        "Crime": None,
        "Status": None,
        "Next Hearing": None,
        "Next Hearing Date": None,
        "Trial": None,
        "Sentencing": None
    }

    # --- ATTORNEY Extraction ---
    party_sections = soup.find_all("div", id="tblForms2")
    for section in party_sections:
        labels = section.find_all("div", class_="col-4 m-visibility bold-font")
        values = section.find_all("div", class_="col-8 col-lg-3")
        name = None
        for i, label in enumerate(labels):
            if label.text.strip() == "Party Name" and i < len(values):
                name = values[i].get_text(strip=True)
                if "State Of Arizona" in name:
                    for j, lbl in enumerate(labels):
                        if lbl.text.strip() == "Attorney" and j < len(values):
                            result["Attorney"] = values[j].get_text(strip=True)
                    break

    # --- CRIME + STATUS Extraction ---
    disposition_section = soup.find("div", id="tblDocket12")
    best_crime, best_status = None, None

    if disposition_section:
        rows = disposition_section.find_all("div", class_="row g-0")
        first_found = False
        for row in rows:
            cols = row.find_all("div")
            party, description, disposition = None, None, None
            for idx, col in enumerate(cols):
                text = col.get_text(strip=True)
                if "Party Name" in text and idx + 1 < len(cols):
                    party = cols[idx + 1].get_text(strip=True)
                elif "Description" in text and idx + 1 < len(cols):
                    description = cols[idx + 1].get_text(strip=True)
                elif "Disposition" in text and idx + 1 < len(cols):
                    disposition = cols[idx + 1].get_text(strip=True)

            if party and suspect_name.lower() in party.lower():
                if description and "MURDER" in description.upper():
                    best_crime = description
                    best_status = disposition
                    break
                elif not first_found and description:
                    best_crime = description
                    best_status = disposition
                    first_found = True

    if best_crime:
        result["Crime"] = best_crime
        result["Status"] = best_status

    # --- CALENDAR INFO ---
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

    return result


# --- MAIN EXECUTION ---
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
        print(f"Updating: {data}")
        table.update(record["id"], data)
    except Exception as e:
        print(f"Error processing {suspect}: {e}")
