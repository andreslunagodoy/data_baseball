import pandas as pd
import shutil

YEAR_MIN = 2000

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

# Filter Appearances to 2000+, only keep players in Batting or Pitching
batting = pd.read_csv("data/Batting.csv", usecols=["playerID", "yearID", "teamID"])
pitching = pd.read_csv("data/Pitching.csv", usecols=["playerID", "yearID", "teamID"])
valid_keys = pd.concat([batting, pitching]).drop_duplicates()
df = pd.read_csv("../data/Appearances.csv")
df = df[df["yearID"] >= YEAR_MIN]
df = df.merge(valid_keys, on=["playerID", "yearID", "teamID"])
df.to_csv("data/Appearances.csv", index=False)
print(f"Appearances: {len(df)} rows (yearID >= {YEAR_MIN}, matched to Batting/Pitching)")

# Filter AwardsPlayers to 2000+ and selected awards
AWARDS = [
    "Cy Young Award", "Gold Glove", "Most Valuable Player",
    "Silver Slugger", "ALCS MVP", "NLCS MVP", "World Series MVP",
]
df = pd.read_csv("../data/AwardsPlayers.csv")
df = df[df["awardID"].isin(AWARDS)]
df.to_csv("data/AwardsPlayers.csv", index=False)
print(f"AwardsPlayers: {len(df)} rows (selected awards)")

# HallOfFame: only inducted players
df = pd.read_csv("../data/HallOfFame.csv")
df = df[(df["inducted"] == "Y") & (df["category"] == "Player")]
df.to_csv("data/HallOfFame.csv", index=False)
print(f"HallOfFame: {len(df)} rows (inducted players only)")

# Copy People, Teams, Salaries as-is
for name in ["People", "Teams", "Salaries"]:
    shutil.copy(f"../data/{name}.csv", f"data/{name}.csv")
    print(f"{name}: copied to data/")
