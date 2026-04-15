"""
Scrape WAR data from Baseball Reference for all MLB years.

Supports resuming: reads existing CSVs and skips years already scraped.
Saves progress every 10 years.

Usage: python3 scraper_bbref.py [start_year] [end_year]
Default: 1871 to 2025
"""

import pandas as pd
import time
import sys
import os
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup

start_year = int(sys.argv[1]) if len(sys.argv) > 1 else 1871
end_year = int(sys.argv[2]) if len(sys.argv) > 2 else 2025

_DIR = os.path.dirname(os.path.abspath(__file__))
BATTING_CSV = os.path.join(_DIR, "..", "my_data", "BBRef_Batting_WAR.csv")
PITCHING_CSV = os.path.join(_DIR, "..", "my_data", "BBRef_Pitching_WAR.csv")

headers = {"User-Agent": "BaseballDataProject/1.0"}

# Load existing data for resume support
if os.path.exists(BATTING_CSV):
    existing_bat = pd.read_csv(BATTING_CSV)
    existing_bat_years = set(existing_bat["yearID"].unique())
else:
    existing_bat = pd.DataFrame(columns=["yearID", "bbrefID", "Player", "Team", "WAR"])
    existing_bat_years = set()

if os.path.exists(PITCHING_CSV):
    existing_pit = pd.read_csv(PITCHING_CSV)
    existing_pit_years = set(existing_pit["yearID"].unique())
else:
    existing_pit = pd.DataFrame(columns=["yearID", "bbrefID", "Player", "Team", "WAR"])
    existing_pit_years = set()

print(f"Existing data: {len(existing_bat)} batting rows ({len(existing_bat_years)} years), "
      f"{len(existing_pit)} pitching rows ({len(existing_pit_years)} years)")

def fetch_url(url):
    """Fetch URL with retry on 429."""
    for attempt in range(4):
        try:
            req = Request(url, headers=headers)
            return urlopen(req).read().decode("utf-8")
        except Exception as e:
            if "429" in str(e) and attempt < 3:
                wait = 30 * (attempt + 1)
                print(f"    Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                raise

batting_rows = []
pitching_rows = []
years_processed = 0

for year in range(start_year, end_year + 1):
    need_batting = year not in existing_bat_years
    need_pitching = year not in existing_pit_years

    if not need_batting and not need_pitching:
        continue

    print(f"Processing {year}...")

    # Batting
    if need_batting:
        try:
            bat_url = f"https://www.baseball-reference.com/leagues/majors/{year}-standard-batting.shtml"
            html = fetch_url(bat_url)
            soup = BeautifulSoup(html, "html.parser")
            table = soup.find("table", id="players_standard_batting")
            if table:
                tbody = table.find("tbody")
                count = 0
                for row in tbody.find_all("tr"):
                    if "thead" in row.get("class", []):
                        continue
                    td = row.find("td", {"data-stat": "name_display"})
                    if not td:
                        continue
                    a = td.find("a")
                    if not a:
                        continue

                    bbref_id = a["href"].split("/")[-1].replace(".shtml", "")
                    name = a.text.rstrip("*#")
                    team_td = row.find("td", {"data-stat": "team_name_abbr"})
                    team = team_td.text if team_td else ""
                    war_td = row.find("td", {"data-stat": "b_war"})
                    war = war_td.text if war_td else ""

                    batting_rows.append({
                        "yearID": year,
                        "bbrefID": bbref_id,
                        "Player": name,
                        "Team": team,
                        "WAR": float(war) if war else None,
                    })
                    count += 1
                print(f"  Batting {year}: {count} players")
            else:
                print(f"  Batting {year}: no table found")
        except Exception as e:
            print(f"  Batting {year} failed: {e}")

    # Pitching
    if need_pitching:
        try:
            pit_url = f"https://www.baseball-reference.com/leagues/majors/{year}-standard-pitching.shtml"
            html = fetch_url(pit_url)
            soup = BeautifulSoup(html, "html.parser")
            table = soup.find("table", id="players_standard_pitching")
            if table:
                tbody = table.find("tbody")
                count = 0
                for row in tbody.find_all("tr"):
                    if "thead" in row.get("class", []):
                        continue
                    td = row.find("td", {"data-stat": "name_display"})
                    if not td:
                        continue
                    a = td.find("a")
                    if not a:
                        continue

                    bbref_id = a["href"].split("/")[-1].replace(".shtml", "")
                    name = a.text.rstrip("*#")
                    team_td = row.find("td", {"data-stat": "team_name_abbr"})
                    team = team_td.text if team_td else ""
                    war_td = row.find("td", {"data-stat": "p_war"})
                    war = war_td.text if war_td else ""

                    pitching_rows.append({
                        "yearID": year,
                        "bbrefID": bbref_id,
                        "Player": name,
                        "Team": team,
                        "WAR": float(war) if war else None,
                    })
                    count += 1
                print(f"  Pitching {year}: {count} players")
            else:
                print(f"  Pitching {year}: no table found")
        except Exception as e:
            print(f"  Pitching {year} failed: {e}")

    time.sleep(6)
    years_processed += 1

    # Save progress every 10 years
    if years_processed % 10 == 0 and (batting_rows or pitching_rows):
        if batting_rows:
            new_bat = pd.DataFrame(batting_rows)
            existing_bat = pd.concat([existing_bat, new_bat], ignore_index=True)
            existing_bat.to_csv(BATTING_CSV, index=False)
            batting_rows = []
            print(f"  [checkpoint] Batting: {len(existing_bat)} total rows")

        if pitching_rows:
            new_pit = pd.DataFrame(pitching_rows)
            existing_pit = pd.concat([existing_pit, new_pit], ignore_index=True)
            existing_pit.to_csv(PITCHING_CSV, index=False)
            pitching_rows = []
            print(f"  [checkpoint] Pitching: {len(existing_pit)} total rows")

# Final save
if batting_rows:
    new_bat = pd.DataFrame(batting_rows)
    existing_bat = pd.concat([existing_bat, new_bat], ignore_index=True)
    existing_bat.to_csv(BATTING_CSV, index=False)

if pitching_rows:
    new_pit = pd.DataFrame(pitching_rows)
    existing_pit = pd.concat([existing_pit, new_pit], ignore_index=True)
    existing_pit.to_csv(PITCHING_CSV, index=False)

print(f"\nDone! Batting: {len(existing_bat)} rows, Pitching: {len(existing_pit)} rows")
