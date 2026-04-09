import pandas as pd

# Load reference tables
people = pd.read_csv("my_data/People.csv", usecols=["playerID", "bbrefID"])
teams = pd.read_csv("my_data/Teams.csv", usecols=["yearID", "teamID", "teamIDBR"])

for stat_type in ["Batting", "Pitching"]:
    # Load Lahman stats and WAR
    lahman = pd.read_csv(f"my_data/{stat_type}.csv")
    war = pd.read_csv(f"my_data/BBRef_{stat_type}_WAR.csv")

    # Drop nTM rows (players with 2TM, 3TM, etc.)
    war = war[~war["Team"].str.match(r"^\d+TM$", na=False)]

    # Add bbrefID to Lahman via People
    lahman = lahman.merge(people, on="playerID", how="left")

    # Add teamIDBR to Lahman via Teams
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

    augmented.to_csv(f"my_data/{stat_type}_with_WAR.csv", index=False)

    total = len(augmented)
    with_war = augmented["WAR"].notna().sum()
    print(f"{stat_type}_with_WAR: {total} rows, {with_war} with WAR ({100*with_war/total:.1f}%)")
