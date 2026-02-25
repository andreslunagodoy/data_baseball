import pandas as pd
import requests
import time
from io import StringIO

start_year = 2024
end_year = 2025

headers = {
    "User-Agent": "Mozilla/5.0"
}

batting_all = []
pitching_all = []

for year in range(start_year, end_year + 1):
    print(f"Processing {year}...")

    # Batting CSV
    try:
        bat_url = f"https://www.baseball-reference.com/leagues/MLB/{year}-standard-batting.csv"
        r = requests.get(bat_url, headers=headers)
        r.raise_for_status()

        batting = pd.read_csv(StringIO(r.text))
        batting['yearID'] = year
        batting_all.append(batting)

        print(f"  Batting {year} done")
    except Exception as e:
        print(f"  Batting {year} failed:", e)

    # Pitching CSV
    try:
        pit_url = f"https://www.baseball-reference.com/leagues/MLB/{year}-standard-pitching.csv"
        r = requests.get(pit_url, headers=headers)
        r.raise_for_status()

        pitching = pd.read_csv(StringIO(r.text))
        pitching['yearID'] = year
        pitching_all.append(pitching)

        print(f"  Pitching {year} done")
    except Exception as e:
        print(f"  Pitching {year} failed:", e)

    time.sleep(1.5)

# Combine
batting_final = pd.concat(batting_all, ignore_index=True)
pitching_final = pd.concat(pitching_all, ignore_index=True)

batting_final.to_csv("BBRef_Batting.csv", index=False)
pitching_final.to_csv("BBRef_Pitching.csv", index=False)

print("Done!")