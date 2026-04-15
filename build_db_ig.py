"""
Build war_games.db from raw Lahman CSVs + Baseball Reference WAR data.

Loads ALL years (not just 2000+), merges WAR where available (2000-2025),
and creates career aggregate tables with computed rate stats.
"""

import sqlite3
import pandas as pd
import os

DB_PATH = "databases/war_games.db"

# Remove existing database to rebuild from scratch
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON")

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
conn.executescript("""
CREATE TABLE People (
    playerID TEXT PRIMARY KEY,
    birthYear INTEGER,
    birthMonth INTEGER,
    birthDay INTEGER,
    birthCountry TEXT,
    birthState TEXT,
    birthCity TEXT,
    deathYear INTEGER,
    deathMonth INTEGER,
    deathDay INTEGER,
    deathCountry TEXT,
    deathState TEXT,
    deathCity TEXT,
    nameFirst TEXT,
    nameLast TEXT,
    nameGiven TEXT,
    weight INTEGER,
    height INTEGER,
    bats TEXT,
    throws TEXT,
    debut TEXT,
    finalGame TEXT,
    retroID TEXT,
    bbrefID TEXT
);

CREATE TABLE Teams (
    yearID INTEGER,
    lgID TEXT,
    teamID TEXT,
    franchID TEXT,
    divID TEXT,
    Rank INTEGER,
    G INTEGER,
    Ghome INTEGER,
    W INTEGER,
    L INTEGER,
    DivWin TEXT,
    WCWin TEXT,
    LgWin TEXT,
    WSWin TEXT,
    R INTEGER,
    AB INTEGER,
    H INTEGER,
    "2B" INTEGER,
    "3B" INTEGER,
    HR INTEGER,
    BB INTEGER,
    SO INTEGER,
    SB INTEGER,
    CS INTEGER,
    HBP INTEGER,
    SF INTEGER,
    RA INTEGER,
    ER INTEGER,
    ERA REAL,
    CG INTEGER,
    SHO INTEGER,
    SV INTEGER,
    IPouts INTEGER,
    HA INTEGER,
    HRA INTEGER,
    BBA INTEGER,
    SOA INTEGER,
    E INTEGER,
    DP INTEGER,
    FP REAL,
    name TEXT,
    park TEXT,
    attendance INTEGER,
    BPF INTEGER,
    PPF INTEGER,
    teamIDBR TEXT,
    teamIDlahman45 TEXT,
    teamIDretro TEXT,
    PRIMARY KEY (teamID, yearID)
);

CREATE TABLE TeamsFranchises (
    franchID TEXT PRIMARY KEY,
    franchName TEXT,
    active TEXT,
    NAassoc TEXT
);

CREATE TABLE Salaries (
    yearID INTEGER,
    teamID TEXT,
    lgID TEXT,
    playerID TEXT,
    salary REAL,
    PRIMARY KEY (yearID, teamID, playerID),
    FOREIGN KEY (playerID) REFERENCES People(playerID)
);

CREATE TABLE Batting (
    playerID TEXT,
    yearID INTEGER,
    stint INTEGER,
    teamID TEXT,
    lgID TEXT,
    G INTEGER,
    AB INTEGER,
    R INTEGER,
    H INTEGER,
    "2B" INTEGER,
    "3B" INTEGER,
    HR INTEGER,
    RBI INTEGER,
    SB INTEGER,
    CS INTEGER,
    BB INTEGER,
    SO INTEGER,
    IBB INTEGER,
    HBP INTEGER,
    SH INTEGER,
    SF INTEGER,
    GIDP INTEGER,
    WAR REAL,
    PRIMARY KEY (playerID, yearID, stint),
    FOREIGN KEY (playerID) REFERENCES People(playerID)
);

CREATE TABLE Pitching (
    playerID TEXT,
    yearID INTEGER,
    stint INTEGER,
    teamID TEXT,
    lgID TEXT,
    W INTEGER,
    L INTEGER,
    G INTEGER,
    GS INTEGER,
    CG INTEGER,
    SHO INTEGER,
    SV INTEGER,
    IPouts INTEGER,
    H INTEGER,
    ER INTEGER,
    HR INTEGER,
    BB INTEGER,
    SO INTEGER,
    BAOpp REAL,
    ERA REAL,
    IBB INTEGER,
    WP INTEGER,
    HBP INTEGER,
    BK INTEGER,
    BFP INTEGER,
    GF INTEGER,
    R INTEGER,
    SH INTEGER,
    SF INTEGER,
    GIDP INTEGER,
    WAR REAL,
    PRIMARY KEY (playerID, yearID, stint),
    FOREIGN KEY (playerID) REFERENCES People(playerID)
);

CREATE TABLE Appearances (
    yearID INTEGER,
    teamID TEXT,
    lgID TEXT,
    playerID TEXT,
    G_all INTEGER,
    GS INTEGER,
    G_batting INTEGER,
    G_defense INTEGER,
    G_p INTEGER,
    G_c INTEGER,
    G_1b INTEGER,
    G_2b INTEGER,
    G_3b INTEGER,
    G_ss INTEGER,
    G_lf INTEGER,
    G_cf INTEGER,
    G_rf INTEGER,
    G_of INTEGER,
    G_dh INTEGER,
    G_ph INTEGER,
    G_pr INTEGER,
    PRIMARY KEY (yearID, teamID, playerID),
    FOREIGN KEY (playerID) REFERENCES People(playerID)
);

CREATE TABLE AwardsPlayers (
    playerID TEXT,
    awardID TEXT,
    yearID INTEGER,
    lgID TEXT,
    tie TEXT,
    notes TEXT,
    FOREIGN KEY (playerID) REFERENCES People(playerID)
);

CREATE TABLE HallOfFame (
    playerID TEXT,
    yearid INTEGER,
    votedBy TEXT,
    ballots INTEGER,
    needed INTEGER,
    votes INTEGER,
    inducted TEXT,
    category TEXT,
    needed_note TEXT,
    PRIMARY KEY (playerID, yearid, votedBy),
    FOREIGN KEY (playerID) REFERENCES People(playerID)
);

CREATE TABLE AllstarFull (
    playerID TEXT,
    yearID INTEGER,
    gameNum INTEGER,
    gameID TEXT,
    teamID TEXT,
    lgID TEXT,
    GP INTEGER,
    startingPos INTEGER,
    FOREIGN KEY (playerID) REFERENCES People(playerID)
);

CREATE TABLE BattingPost (
    yearID INTEGER,
    round TEXT,
    playerID TEXT,
    teamID TEXT,
    lgID TEXT,
    G INTEGER,
    AB INTEGER,
    R INTEGER,
    H INTEGER,
    "2B" INTEGER,
    "3B" INTEGER,
    HR INTEGER,
    RBI INTEGER,
    SB INTEGER,
    CS INTEGER,
    BB INTEGER,
    SO INTEGER,
    IBB INTEGER,
    HBP INTEGER,
    SH INTEGER,
    SF INTEGER,
    GIDP INTEGER,
    FOREIGN KEY (playerID) REFERENCES People(playerID)
);

CREATE TABLE PitchingPost (
    playerID TEXT,
    yearID INTEGER,
    round TEXT,
    teamID TEXT,
    lgID TEXT,
    W INTEGER,
    L INTEGER,
    G INTEGER,
    GS INTEGER,
    CG INTEGER,
    SHO INTEGER,
    SV INTEGER,
    IPouts INTEGER,
    H INTEGER,
    ER INTEGER,
    HR INTEGER,
    BB INTEGER,
    SO INTEGER,
    BAOpp REAL,
    ERA REAL,
    IBB INTEGER,
    WP INTEGER,
    HBP INTEGER,
    BK INTEGER,
    BFP INTEGER,
    GF INTEGER,
    R INTEGER,
    SH INTEGER,
    SF INTEGER,
    GIDP INTEGER,
    FOREIGN KEY (playerID) REFERENCES People(playerID)
);
""")

print("Schema created.")

# ---------------------------------------------------------------------------
# Load raw tables (all years)
# ---------------------------------------------------------------------------
raw = "raw_data"

simple_tables = [
    ("People",           f"{raw}/People.csv"),
    ("Teams",            f"{raw}/Teams.csv"),
    ("TeamsFranchises",  f"{raw}/TeamsFranchises.csv"),
    ("Salaries",         f"{raw}/Salaries.csv"),
    ("Appearances",      f"{raw}/Appearances.csv"),
    ("AwardsPlayers",    f"{raw}/AwardsPlayers.csv"),
    ("HallOfFame",       f"{raw}/HallOfFame.csv"),
    ("AllstarFull",      f"{raw}/AllstarFull.csv"),
    ("BattingPost",      f"{raw}/BattingPost.csv"),
    ("PitchingPost",     f"{raw}/PitchingPost.csv"),
]

AL_NL_TABLES = {"Teams", "Appearances", "AllstarFull", "BattingPost", "PitchingPost", "Salaries"}

for table_name, csv_path in simple_tables:
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    if "ID" in df.columns:
        df = df.drop(columns=["ID"])
    if table_name in AL_NL_TABLES and "lgID" in df.columns:
        df = df[df["lgID"].isin(["AL", "NL"])]
    df.to_sql(table_name, conn, if_exists="append", index=False)
    print(f"  {table_name}: {len(df)} rows")

# ---------------------------------------------------------------------------
# Batting + WAR merge (all years, WAR available for 2000-2025)
# ---------------------------------------------------------------------------
print("\nMerging WAR into Batting...")
people = pd.read_csv(f"{raw}/People.csv", encoding="utf-8-sig",
                      usecols=["playerID", "bbrefID"])
teams = pd.read_csv(f"{raw}/Teams.csv", usecols=["yearID", "teamID", "teamIDBR"])

for stat_type, table_name in [("Batting", "Batting"), ("Pitching", "Pitching")]:
    lahman = pd.read_csv(f"{raw}/{stat_type}.csv")

    # Keep only AL/NL leagues
    lahman = lahman[lahman["lgID"].isin(["AL", "NL"])]

    # For batting, drop rows with no at-bats
    if stat_type == "Batting":
        lahman = lahman[lahman["AB"] > 0]

    war = pd.read_csv(f"my_data/BBRef_{stat_type}_WAR.csv")

    # Drop multi-team summary rows
    war = war[~war["Team"].str.match(r"^\d+TM$", na=False)]

    # Add bbrefID and teamIDBR for joining
    lahman = lahman.merge(people, on="playerID", how="left")
    lahman = lahman.merge(teams, on=["yearID", "teamID"], how="left")

    # Join WAR
    augmented = lahman.merge(
        war[["bbrefID", "yearID", "Team", "WAR"]],
        left_on=["bbrefID", "yearID", "teamIDBR"],
        right_on=["bbrefID", "yearID", "Team"],
        how="left",
    )
    augmented.drop(columns=["bbrefID", "teamIDBR", "Team"], inplace=True)

    augmented.to_sql(table_name, conn, if_exists="append", index=False)
    total = len(augmented)
    with_war = augmented["WAR"].notna().sum()
    print(f"  {table_name}: {total} rows, {with_war} with WAR ({100*with_war/total:.1f}%)")

# ---------------------------------------------------------------------------
# Career aggregate tables
# ---------------------------------------------------------------------------
print("\nCreating career aggregate tables...")

conn.executescript("""
CREATE TABLE Career_Batting AS
SELECT
    playerID,
    COUNT(DISTINCT yearID) AS seasons,
    SUM(G) AS G,
    SUM(AB) AS AB,
    SUM(R) AS R,
    SUM(H) AS H,
    SUM("2B") AS "2B",
    SUM("3B") AS "3B",
    SUM(HR) AS HR,
    SUM(RBI) AS RBI,
    SUM(SB) AS SB,
    SUM(CS) AS CS,
    SUM(BB) AS BB,
    SUM(SO) AS SO,
    SUM(IBB) AS IBB,
    SUM(HBP) AS HBP,
    SUM(SH) AS SH,
    SUM(SF) AS SF,
    SUM(GIDP) AS GIDP,
    SUM(WAR) AS WAR,
    -- Computed rate stats
    CASE WHEN SUM(AB) > 0
         THEN ROUND(1.0 * SUM(H) / SUM(AB), 3) END AS AVG,
    CASE WHEN (SUM(AB) + SUM(COALESCE(BB,0)) + SUM(COALESCE(HBP,0)) + SUM(COALESCE(SF,0))) > 0
         THEN ROUND(1.0 * (SUM(H) + SUM(COALESCE(BB,0)) + SUM(COALESCE(HBP,0)))
              / (SUM(AB) + SUM(COALESCE(BB,0)) + SUM(COALESCE(HBP,0)) + SUM(COALESCE(SF,0))), 3) END AS OBP,
    CASE WHEN SUM(AB) > 0
         THEN ROUND(1.0 * (SUM(H) - SUM("2B") - SUM("3B") - SUM(HR)
              + 2 * SUM("2B") + 3 * SUM("3B") + 4 * SUM(HR)) / SUM(AB), 3) END AS SLG,
    CASE WHEN SUM(AB) > 0
         THEN ROUND(
              CASE WHEN (SUM(AB) + SUM(COALESCE(BB,0)) + SUM(COALESCE(HBP,0)) + SUM(COALESCE(SF,0))) > 0
                   THEN 1.0 * (SUM(H) + SUM(COALESCE(BB,0)) + SUM(COALESCE(HBP,0)))
                        / (SUM(AB) + SUM(COALESCE(BB,0)) + SUM(COALESCE(HBP,0)) + SUM(COALESCE(SF,0)))
                   ELSE 0 END
              + 1.0 * (SUM(H) - SUM("2B") - SUM("3B") - SUM(HR)
                + 2 * SUM("2B") + 3 * SUM("3B") + 4 * SUM(HR)) / SUM(AB)
         , 3) END AS OPS
FROM Batting
GROUP BY playerID;

CREATE TABLE Career_Pitching AS
SELECT
    playerID,
    COUNT(DISTINCT yearID) AS seasons,
    SUM(W) AS W,
    SUM(L) AS L,
    SUM(G) AS G,
    SUM(GS) AS GS,
    SUM(CG) AS CG,
    SUM(SHO) AS SHO,
    SUM(SV) AS SV,
    SUM(IPouts) AS IPouts,
    SUM(H) AS H,
    SUM(ER) AS ER,
    SUM(HR) AS HR,
    SUM(BB) AS BB,
    SUM(SO) AS SO,
    SUM(WAR) AS WAR,
    -- Computed rate stats
    CASE WHEN SUM(IPouts) > 0
         THEN ROUND(9.0 * SUM(ER) / (SUM(IPouts) / 3.0), 2) END AS ERA,
    CASE WHEN SUM(IPouts) > 0
         THEN ROUND((SUM(BB) + SUM(H)) / (SUM(IPouts) / 3.0), 3) END AS WHIP
FROM Pitching
GROUP BY playerID;
""")

bat_count = conn.execute("SELECT COUNT(*) FROM Career_Batting").fetchone()[0]
pit_count = conn.execute("SELECT COUNT(*) FROM Career_Pitching").fetchone()[0]
print(f"  Career_Batting: {bat_count} players")
print(f"  Career_Pitching: {pit_count} players")

# ---------------------------------------------------------------------------
# Indexes for common queries
# ---------------------------------------------------------------------------
print("\nCreating indexes...")
conn.executescript("""
CREATE INDEX idx_batting_player ON Batting(playerID);
CREATE INDEX idx_batting_team_year ON Batting(teamID, yearID);
CREATE INDEX idx_pitching_player ON Pitching(playerID);
CREATE INDEX idx_pitching_team_year ON Pitching(teamID, yearID);
CREATE INDEX idx_appearances_player ON Appearances(playerID);
CREATE INDEX idx_teams_franch ON Teams(franchID);
CREATE INDEX idx_awards_player ON AwardsPlayers(playerID);
CREATE INDEX idx_awards_id ON AwardsPlayers(awardID);
CREATE INDEX idx_hof_player ON HallOfFame(playerID);
CREATE INDEX idx_allstar_player ON AllstarFull(playerID);
CREATE INDEX idx_battingpost_player ON BattingPost(playerID);
CREATE INDEX idx_battingpost_team_year ON BattingPost(teamID, yearID);
CREATE INDEX idx_pitchingpost_player ON PitchingPost(playerID);
CREATE INDEX idx_pitchingpost_team_year ON PitchingPost(teamID, yearID);
CREATE INDEX idx_career_batting_player ON Career_Batting(playerID);
CREATE INDEX idx_career_pitching_player ON Career_Pitching(playerID);
""")

conn.close()
print(f"\nDatabase built: {DB_PATH}")
