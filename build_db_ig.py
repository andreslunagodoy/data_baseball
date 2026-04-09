import sqlite3
import pandas as pd
import os

DB_PATH = "databases/war_games.db"

# Remove existing database to rebuild from scratch
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON")

# --- Schema definitions ---

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

CREATE TABLE Salaries (
    yearID INTEGER,
    teamID TEXT,
    lgID TEXT,
    playerID TEXT,
    salary REAL,
    PRIMARY KEY (yearID, teamID, playerID),
    FOREIGN KEY (playerID) REFERENCES People(playerID),
    FOREIGN KEY (teamID, yearID) REFERENCES Teams(teamID, yearID)
);

CREATE TABLE Batting_with_WAR (
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
    FOREIGN KEY (playerID) REFERENCES People(playerID),
    FOREIGN KEY (teamID, yearID) REFERENCES Teams(teamID, yearID)
);

CREATE TABLE Pitching_with_WAR (
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
    FOREIGN KEY (playerID) REFERENCES People(playerID),
    FOREIGN KEY (teamID, yearID) REFERENCES Teams(teamID, yearID)
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
    FOREIGN KEY (playerID) REFERENCES People(playerID),
    FOREIGN KEY (teamID, yearID) REFERENCES Teams(teamID, yearID)
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
""")

print("Schema created.")

# --- Load data (parents first, then children) ---

tables = [
    ("People", "my_data/People.csv"),
    ("Teams", "my_data/Teams.csv"),
    ("Salaries", "my_data/Salaries.csv"),
    ("Batting_with_WAR", "my_data/Batting_with_WAR.csv"),
    ("Pitching_with_WAR", "my_data/Pitching_with_WAR.csv"),
    ("Appearances", "my_data/Appearances.csv"),
    ("AwardsPlayers", "my_data/AwardsPlayers.csv"),
    ("HallOfFame", "my_data/HallOfFame.csv"),
]

for table_name, csv_path in tables:
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    # People CSV has an extra ID column from Lahman source
    if "ID" in df.columns:
        df = df.drop(columns=["ID"])
    df.to_sql(table_name, conn, if_exists="append", index=False)
    print(f"{table_name}: {len(df)} rows loaded")

conn.close()
print(f"\nDatabase built: {DB_PATH}")
