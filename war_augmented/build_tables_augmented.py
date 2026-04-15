"""
Build augmented Batting/Pitching CSVs with WAR merged from Baseball Reference.

Reads raw Lahman CSVs + BBRef WAR CSVs, filters to AL/NL only (AB>0 for batting),
merges WAR, and writes to war_augmented/.

Run from the war_augmented/ directory:
    cd war_augmented && python3 build_tables_augmented.py
"""

import pandas as pd

raw = "../raw_data"
war_dir = "../my_data"

# Load reference tables for joining
people = pd.read_csv(f"{raw}/People.csv", encoding="utf-8-sig",
                      usecols=["playerID", "bbrefID"])
teams = pd.read_csv(f"{raw}/Teams.csv", usecols=["yearID", "teamID", "teamIDBR"])

for stat_type in ["Batting", "Pitching"]:
    # Load raw Lahman stats
    lahman = pd.read_csv(f"{raw}/{stat_type}.csv")

    # Filter to AL/NL only
    lahman = lahman[lahman["lgID"].isin(["AL", "NL"])]

    # For batting, drop rows with no at-bats
    if stat_type == "Batting":
        lahman = lahman[lahman["AB"] > 0]

    # Load BBRef WAR
    war = pd.read_csv(f"{war_dir}/BBRef_{stat_type}_WAR.csv")

    # Drop multi-team summary rows (e.g., "2TM", "3TM")
    war = war[~war["Team"].str.match(r"^\d+TM$", na=False)]

    # Add bbrefID and teamIDBR for joining
    lahman = lahman.merge(people, on="playerID", how="left")
    lahman = lahman.merge(teams, on=["yearID", "teamID"], how="left")

    # Join WAR on (bbrefID, yearID, teamIDBR=Team)
    augmented = lahman.merge(
        war[["bbrefID", "yearID", "Team", "WAR"]],
        left_on=["bbrefID", "yearID", "teamIDBR"],
        right_on=["bbrefID", "yearID", "Team"],
        how="left",
    )

    # Drop helper columns, keep WAR
    augmented.drop(columns=["bbrefID", "teamIDBR", "Team"], inplace=True)

    out_path = f"{stat_type}_with_WAR.csv"
    augmented.to_csv(out_path, index=False)

    total = len(augmented)
    with_war = augmented["WAR"].notna().sum()
    print(f"{stat_type}_with_WAR: {total} rows, {with_war} with WAR ({100*with_war/total:.1f}%)")
