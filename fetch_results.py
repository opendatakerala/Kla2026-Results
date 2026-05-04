from curl_cffi import requests
from bs4 import BeautifulSoup
import csv
import json
from datetime import datetime
from zoneinfo import ZoneInfo

# -----------------------------
# CONFIG
# -----------------------------
BASE_URL = "https://results.eci.gov.in/ResultAcGenMay2026/statewiseS{}.htm"
STATE_RANGE = range(111, 118)

CSV_FILE = "KLAdetails.csv"

OUTPUT_JSON = "results.json"
OUTPUT_CSV = "results.csv"

# -----------------------------
# TIME (IST)
# -----------------------------
def get_ist_time():
    return datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")


# -----------------------------
# LOAD CONST DATA (CSV)
# -----------------------------
def load_lookup():
    lookup = {}

    with open(CSV_FILE, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        # normalize headers once
        reader.fieldnames = [h.strip() for h in reader.fieldnames]

        for row in reader:
            # strip ALL keys safely
            row = {k.strip(): v.strip() if isinstance(v, str) else v for k, v in row.items()}

            no_raw = row.get("constituency_Number", "").strip()

            if not no_raw.isdigit():
                continue

            no = int(no_raw)

            lookup[no] = {
                "name": row.get("constituency_Name", ""),
                "name_ml": row.get("constituency_Name_ (Malayalam)", ""),
                "district": row.get("district", ""),
                "region": row.get("region", ""),
                "wikidata": row.get("constituency_Wikidata", "")
            }

    return lookup

# -----------------------------
# SCRAPE HTML
# -----------------------------
def scrape_state(state_code):
    url = BASE_URL.format(state_code)
    print(f"Fetching {url}")

    res = requests.get(url, impersonate="chrome110")

    if res.status_code != 200 or "custom-table" not in res.text:
        print(f"Blocked or invalid: S{state_code}")
        return []

    soup = BeautifulSoup(res.text, "html.parser")

    rows = soup.select("div.custom-table table tbody tr")

    data = []

    for row in rows:
        cols = row.find_all("td", recursive=False)
        if len(cols) < 6:
            continue

        constituency_name = cols[0].get_text(strip=True)
        constituency_no = cols[1].get_text(strip=True)

        leading_candidate = cols[2].get_text(strip=True)
        leading_party = cols[3].get_text(strip=True).split("iParty")[0]

        if "iParty" in leading_party:
            leading_party = leading_party.split("iParty")[0].strip()
        elif "Party" in leading_party:
            leading_party = leading_party.split("Party")[0].strip()

        trailing_candidate = cols[4].get_text(strip=True)
        trailing_party = cols[5].get_text(strip=True)

        if "iParty" in trailing_party:
            trailing_party = trailing_party.split("iParty")[0].strip()
        elif "Party" in trailing_party:
            trailing_party = trailing_party.split("Party")[0].strip()

        margin = cols[6].get_text(strip=True) if len(cols) > 6 else None
        round_val = cols[7].get_text(strip=True) if len(cols) > 7 else None
        status = cols[8].get_text(strip=True) if len(cols) > 8 else None

        if not constituency_no.isdigit():
            continue

        data.append({
            "constituency_no": int(constituency_no),
            "scraped_name": constituency_name,
            "leading_candidate": leading_candidate,
            "leading_party": leading_party,
            "trailing_candidate": trailing_candidate,
            "trailing_party": trailing_party,
            "margin": margin,
            "round": round_val,
            "status": status,
            "state_code": f"S{state_code}"
        })

    return data


# -----------------------------
# MAIN PROCESS
# -----------------------------
def main():
    lookup = load_lookup()
    all_results = []
    update_time = get_ist_time()

    for state in STATE_RANGE:
        scraped = scrape_state(state)

        for item in scraped:
            meta = lookup.get(item["constituency_no"], {})

            all_results.append({
                "state_code": item["state_code"],
                "constituency_no": item["constituency_no"],

                "constituency_name": meta.get("name", item["scraped_name"]),
                "constituency_name_ml": meta.get("name_ml", ""),
                "district": meta.get("district", ""),
                "region": meta.get("region", ""),
                "wikidata": meta.get("wikidata", ""),

                "leading_candidate": item["leading_candidate"],
                "leading_party": item["leading_party"],
                "trailing_candidate": item["trailing_candidate"],
                "trailing_party": item["trailing_party"],

                "margin": item["margin"],
                "round": item["round"],
                "status": item["status"],

                "update_time": update_time
            })

    # -----------------------------
    # SAVE JSON
    # -----------------------------
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    # -----------------------------
    # SAVE CSV
    # -----------------------------
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "state_code",
                "constituency_no",
                "constituency_name",
                "constituency_name_ml",
                "district",
                "region",
                "wikidata",
                "leading_candidate",
                "leading_party",
                "trailing_candidate",
                "trailing_party",
                "margin",
                "round",
                "status",
                "update_time"
            ]
        )
        writer.writeheader()
        writer.writerows(all_results)

    print(f"Done. Total records: {len(all_results)}")


if __name__ == "__main__":
    main()
