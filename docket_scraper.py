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

    result = {
        "Attorney": None,
        "Crime": None,
        "Status": None,
        "Next Hearing": None,
        "Next Hearing Date": None,
        "Trial": None,
        "Sentencing": None
    }

    # -- ATTORNEY extraction --
    tbl2 = soup.find(id="tblDocket2")
    if tbl2:
        party_blocks = tbl2.find_all(id="tblForms2")
        for block in party_blocks:
            labels = block.find_all("div", class_="col-4 m-visibility bold-font")
            for i, label in enumerate(labels):
                if label.get_text(strip=True) == "Party Name":
                    name_div = labels[i].find_next_sibling("div")
                    if name_div and "State Of Arizona" in name_div.get_text():
                        for j, lbl in enumerate(labels):
                            if lbl.get_text(strip=True) == "Attorney":
                                attorney_div = lbl.find_next_sibling("div")
                                if attorney_div:
                                    result["Attorney"] = attorney_div.get_text(strip=True)
                        break

    # -- CRIME + STATUS extraction --
    disposition_section = soup.find(id="tblDocket12")
    crime_found = False
    if disposition_section:
        blocks = disposition_section.find_all("div", class_="row g-0")
        for block in blocks:
            party_name = None
            description = None
            disposition = None

            for label in block.find_all("div", class_="col-6"):
                label_text = label.get_text(strip=True)
                next_div = label.find_next_sibling("div")
                if not next_div:
                    continue

                if label_text == "Party Name":
                    party_name = next_div.get_text(strip=True)
                elif label_text == "Description":
                    description = next_div.get_text(strip=True)
                elif label_text == "Disposition":
                    disposition = next_div.get_text(strip=True)

            if not party_name or not suspect_name.lower() in party_name.lower():
                continue

            if description and "MURDER" in description.upper():
                result["Crime"] = description
