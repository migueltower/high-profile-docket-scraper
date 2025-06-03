import os
import re
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from pyairtable import Api

# Airtable setup
AIRTABLE_API_KEY = os.environ["AIRTABLE_API_KEY"]
BASE_ID = "appwbCU6BAWOA1AQX"
TABLE_ID = "tblb0yIYr91PzghXQ"
api = Api(AIRTABLE_API_KEY)
table = api.table(BASE_ID, TABLE_ID)

TODAY = datetime.today()


def extract_from_docket(url, suspect_name):
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

    # --- Attorney extraction from tblForms2 ---
    atty_section = soup.find(id="tblForms2")
    if atty_section:
        blocks = atty_section.find_all("div", class_="row g-0")
        for block in blocks:
            party = block.find("div", string=re.compile("Party Name", re.I))
            if party and "State Of Arizona" in block.text:
                atty_label = block.find("div", string=re.compile("Attorney", re.I))
                if atty_label:
                    atty_val = atty_label.find_next_sibling("div")
                    if atty_val:
                        result["Attorney"] = atty_val.text.strip()
                        break

    # --- Disposition info from tblDocket12 ---
    charge_section = soup.find(id="tblDocket12")
    murder_found = False
    if charge_section:
        rows = charge_section.find_all("div", class_="row g-0")
        for row in rows:
            party_name_div = row.find("div", class_=re.compile("col.*"))
            if party_name_div and suspect_name.lower() in party_name_div.text.strip().lower():
                description_label = row.find(string=re.compile("Description", re.I))
                disposition_label = row.find(string=re.compile("Disposition", re.I))

                description = ""
                disposition = ""

                if description_label:
                    desc_val_div = description_label.find_next("div")
                    if desc_val_div:
                        description = desc_val_div.text.strip()

                if disposition_label:
                    disp_val_div = disposition_label.find_next("div")
                    if disp_val_div:
                        disposition = disp_val_div.text.strip()

                if "MURDER" in description.upper():
                    result["Crime"] = description
                    result["Status"] = disposition
                    murder_found = True
                    break
                elif not result["Crime"]:
                    result["Crime"] = description
                    result["Status"] = disposition

    # --- Calendar info from tblForms4 ---
    calendar = soup.find(id="tblForms4")
    future_dates = []
    if calendar:
        rows = calendar.find_all("div", class_="row g-0")
        for row in rows:
            date_div = row.find("div", class_="col-6 col-lg-2")
            event_div = row.find("div", class_="col-6 col-lg-8")
            if date_div and event_div:
                try:
                    date_obj = datetime.strptime(date_div.text.strip(), "%m/%d/%Y")
                    if date_obj >= TODAY:
                        event_text = event_div.text.strip()
                        future_dates.append((date_obj, event_text))
                except:
                    continue

        if future_dates:
            future_dates.sort()
            soonest_date, soonest_event = future_dates[0]
            result["Next Hearing Date"] = soonest_date.strftime("%Y-%m-%d")
            result["Next Hearing"] = soonest_event

            for dt, ev in future_dates:
                if "TRIAL" in ev.upper() and not result["Trial"]:
                    result["Trial"] = dt.strftime("%Y-%m-%d")
                if "SENTENCING" in ev.upper() and not result["Sentencing"]:
                    result["Sentencing"] = dt.strftime("%Y-%m-%d")

    return result


# --- Main Run ---
records = table.all(fields=["Suspect Name", "Court Docket"])

for record in records:
    fields = record.get("fields", {})
    docket_url = fields.get("Court Docket")
    suspect = fields.get("Suspect Name")

    if docket_url and suspect:
        print(f"Processing: {suspect}")
        try:
            result = extract_from_docket(docket_url, suspect)
            table.update(record["id"], result)
            print(f"✔️ Updated {suspect}")
        except Exception as e:
            print(f"❌ Failed for {suspect}: {e}")
