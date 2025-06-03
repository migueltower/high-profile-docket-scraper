import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pyairtable import Api

# Airtable Setup
AIRTABLE_API_KEY = os.environ["AIRTABLE_API_KEY"]
BASE_ID = "appwbCU6BAWOA1AQX"
TABLE_ID = "tblb0yIYr91PzghXQ"
api = Api(AIRTABLE_API_KEY)
table = api.table(BASE_ID, TABLE_ID)

TODAY = datetime.today()

def extract_from_docket(url, suspect_name):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    
    # --- Extract Attorney ---
    atty_name = None
    tbl2 = soup.find(id="tblDocket2")
    if tbl2:
        rows = tbl2.find_all("tr")
        for row in rows:
            if "State Of Arizona" in row.text:
                cells = row.find_all("td")
                if len(cells) > 3:
                    atty_name = cells[3].get_text(strip=True)
                    break
    
    # --- Extract Disposition Info ---
    crime, status = None, None
    charges = soup.find(id="tblDocket12")
    if charges:
        rows = charges.find_all("tr")
        for row in rows[1:]:  # Skip header
            cells = row.find_all("td")
            if len(cells) < 5:
                continue
            party, description, disposition = cells[0].text, cells[1].text, cells[4].text
            if suspect_name.lower() in party.lower():
                if "MURDER" in description.upper():
                    crime = description
                    status = disposition
                    break
                elif not crime:
                    crime = description
                    status = disposition
    
    # --- Extract Calendar Info ---
    calendar = soup.find(id="tblForms4")
    next_hearing_date, next_hearing = None, None
    trial, sentencing = None, None
    if calendar:
        rows = calendar.find_all("div", class_="row g-0")
        future_dates = []
        for row in rows:
            date_div = row.find("div", class_="col-6 col-lg-2")
            event_div = row.find("div", class_="col-6 col-lg-8")
            if date_div and event_div:
                date_str = date_div.text.strip()
                event_str = event_div.text.strip()
                try:
                    date_obj = datetime.strptime(date_str, "%m/%d/%Y")
                    if date_obj >= TODAY:
                        future_dates.append((date_obj, event_str))
                except:
                    continue
        
        if future_dates:
            future_dates.sort()
            next_hearing_date, next_hearing = future_dates[0]
            for dt, ev in future_dates:
                if "TRIAL" in ev.upper() and not trial:
                    trial = dt
                if "SENTENCING" in ev.upper() and not sentencing:
                    sentencing = dt

    return {
        "Attorney": atty_name,
        "Crime": crime,
        "Status": status,
        "Next Hearing": next_hearing,
        "Next Hearing Date": next_hearing_date.strftime("%Y-%m-%d") if next_hearing_date else None,
        "Trial": trial.strftime("%Y-%m-%d") if trial else None,
        "Sentencing": sentencing.strftime("%Y-%m-%d") if sentencing else None
    }

# Main run
records = table.all(fields=["Suspect Name", "Court Docket"])
for record in records:
    fields = record["fields"]
    docket_url = fields.get("Court Docket")
    suspect = fields.get("Suspect Name")
    if docket_url and suspect:
        result = extract_from_docket(docket_url, suspect)
        table.update(record["id"], result)
        print(f"Updated: {suspect}")
