import pandas as pd
import time

start_year = 2024
end_year = 2025

batting_all = []
pitching_all = []

for year in range(start_year, end_year + 1):
    print(f"Processing {year}...")

    # Batting
    try:
        bat_url = f"https://www.baseball-reference.com/leagues/majors/{year}-standard-batting.shtml"
        bat_tables = pd.read_html(bat_url)
        batting = bat_tables[1]
        batting['yearID'] = year  # add year column
        batting_all.append(batting)
        print(f"  Batting {year} done")
    except Exception as e:
        print(f"  Batting {year} failed:", e)

    # Pitching
    try:
        pit_url = f"https://www.baseball-reference.com/leagues/majors/{year}-standard-pitching.shtml"
        pit_tables = pd.read_html(pit_url)
        pitching = pit_tables[1]
        pitching['yearID'] = year
        pitching_all.append(pitching)
        print(f"  Pitching {year} done")
    except Exception as e:
        print(f"  Pitching {year} failed:", e)

    # Be polite to the server
    time.sleep(1.5)

# Combine all years into one CSV per category
batting_final = pd.concat(batting_all, ignore_index=True)
batting_final.to_csv("BBRef_Batting_1900_2025.csv", index=False)

pitching_final = pd.concat(pitching_all, ignore_index=True)
pitching_final.to_csv("BBRef_Pitching_1900_2025.csv", index=False)

print("All done! Two CSVs created: BBRef_Batting_1900_2025.csv and BBRef_Pitching_1900_2025.csv")