import pandas as pd
import time
from urllib.request import urlopen
from bs4 import BeautifulSoup

start_year = 2020
end_year = 2025

batting_rows = []
pitching_rows = []

for year in range(start_year, end_year + 1):
    print(f"Processing {year}...")

    # Batting
    try:
        bat_url = f"https://www.baseball-reference.com/leagues/majors/{year}-standard-batting.shtml"
        html = urlopen(bat_url).read().decode("utf-8")
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", id="players_standard_batting")
        tbody = table.find("tbody")

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
            name = a.text.rstrip("*#")  # remove HOF/active markers
            team = row.find("td", {"data-stat": "team_name_abbr"}).text
            war = row.find("td", {"data-stat": "b_war"}).text

            batting_rows.append({
                "yearID": year,
                "bbrefID": bbref_id,
                "Player": name,
                "Team": team,
                "WAR": float(war) if war else None,
            })

        print(f"  Batting {year}: {sum(1 for r in batting_rows if r['yearID'] == year)} players")
    except Exception as e:
        print(f"  Batting {year} failed: {e}")

    # Pitching
    try:
        pit_url = f"https://www.baseball-reference.com/leagues/majors/{year}-standard-pitching.shtml"
        html = urlopen(pit_url).read().decode("utf-8")
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", id="players_standard_pitching")
        tbody = table.find("tbody")

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
            team = row.find("td", {"data-stat": "team_name_abbr"}).text
            war = row.find("td", {"data-stat": "p_war"}).text

            pitching_rows.append({
                "yearID": year,
                "bbrefID": bbref_id,
                "Player": name,
                "Team": team,
                "WAR": float(war) if war else None,
            })

        print(f"  Pitching {year}: {sum(1 for r in pitching_rows if r['yearID'] == year)} players")
    except Exception as e:
        print(f"  Pitching {year} failed: {e}")

    time.sleep(1.5)

# Save
batting_df = pd.DataFrame(batting_rows)
batting_df.to_csv("data/BBRef_Batting_WAR.csv", index=False)

pitching_df = pd.DataFrame(pitching_rows)
pitching_df.to_csv("data/BBRef_Pitching_WAR.csv", index=False)

print(f"\nDone! Batting: {len(batting_df)} rows, Pitching: {len(pitching_df)} rows")
print("Files: data/BBRef_Batting_WAR.csv, data/BBRef_Pitching_WAR.csv")
