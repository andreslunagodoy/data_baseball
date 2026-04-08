import pandas as pd
import shutil

YEAR_MIN = 2020

# Filter Batting to 2020+ and AB > 0
df = pd.read_csv("../data/Batting.csv")
df = df[(df["yearID"] >= YEAR_MIN) & (df["AB"] > 0)]
df.to_csv("data/Batting.csv", index=False)
print(f"Batting: {len(df)} rows (yearID >= {YEAR_MIN}, AB > 0)")

# Filter Pitching to 2020+
df = pd.read_csv("../data/Pitching.csv")
df = df[df["yearID"] >= YEAR_MIN]
df.to_csv("data/Pitching.csv", index=False)
print(f"Pitching: {len(df)} rows (yearID >= {YEAR_MIN})")

# Copy People, Teams, Salaries as-is
for name in ["People", "Teams", "Salaries"]:
    shutil.copy(f"../data/{name}.csv", f"data/{name}.csv")
    print(f"{name}: copied to data/")
