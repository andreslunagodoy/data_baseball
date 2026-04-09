"""
build_db_lahman.py
Reads Lahman CSV files from raw_data/ and creates databases/lahman.db (SQLite).
"""

import os
import sqlite3
import pandas as pd

DATA_DIR = "raw_data"
DB_FILE = "databases/lahman.db"

# ── Load CSVs ────────────────────────────────────────────────
people = pd.read_csv(os.path.join(DATA_DIR, "People.csv"))
batting = pd.read_csv(os.path.join(DATA_DIR, "Batting.csv"))
pitching = pd.read_csv(os.path.join(DATA_DIR, "Pitching.csv"))
teams = pd.read_csv(os.path.join(DATA_DIR, "Teams.csv"))
salaries = pd.read_csv(os.path.join(DATA_DIR, "Salaries.csv"))

my_tables = [people, batting, pitching, teams, salaries]
table_names = ["People", "Batting", "Pitching", "Teams", "Salaries"]

# Sanity check: print columns
for name, df in zip(table_names, my_tables):
    print(f"{name}: {list(df.columns)}")

# ── Create SQLite database ───────────────────────────────────
conn = sqlite3.connect(DB_FILE)
conn.execute("PRAGMA foreign_keys = ON;")
cursor = conn.cursor()

pk_map = {
    "People": ["playerID"],
    "Batting": ["playerID", "yearID", "stint"],
    "Pitching": ["playerID", "yearID", "stint"],
    "Teams": ["teamID", "yearID"],
    "Salaries": ["yearID", "teamID", "playerID"]
}

fk_map = {
    "Batting": [("playerID", "People", "playerID"), ("teamID,yearID", "Teams", "teamID,yearID")],
    "Pitching": [("playerID", "People", "playerID"), ("teamID,yearID", "Teams", "teamID,yearID")],
    "Salaries": [("playerID", "People", "playerID"), ("teamID,yearID", "Teams", "teamID,yearID")]
}

dtype_map = {
    "str": "TEXT",
    "int64": "INTEGER",
    "float64": "REAL"
}

for name, df in zip(table_names, my_tables):
    cursor.execute(f"DROP TABLE IF EXISTS {name};")

    cols = []
    for col, dtype in zip(df.columns, df.dtypes):
        sql_type = dtype_map.get(str(dtype), "TEXT")
        col_quoted = f'"{col}"'
        if col in pk_map[name] and len(pk_map[name]) == 1:
            cols.append(f"{col_quoted} {sql_type} PRIMARY KEY")
        else:
            cols.append(f"{col_quoted} {sql_type}")

    create_sql = f"CREATE TABLE {name} ({', '.join(cols)}"

    if len(pk_map[name]) > 1:
        pk_cols = ', '.join(f'"{c}"' for c in pk_map[name])
        create_sql += f", PRIMARY KEY ({pk_cols})"

    if name in fk_map:
        for fk_cols, ref_table, ref_cols in fk_map[name]:
            fk_cols_list = ', '.join(f'"{c.strip()}"' for c in fk_cols.split(','))
            ref_cols_list = ', '.join(f'"{c.strip()}"' for c in ref_cols.split(','))
            create_sql += f", FOREIGN KEY ({fk_cols_list}) REFERENCES {ref_table}({ref_cols_list})"

    create_sql += ");"
    cursor.execute(create_sql)
    print(f"Created table {name}")

conn.commit()

# ── Load data (parents first) ────────────────────────────────
people.to_sql("People", conn, if_exists="append", index=False)
teams.to_sql("Teams", conn, if_exists="append", index=False)
print("Loaded People and Teams")

batting.to_sql("Batting", conn, if_exists="append", index=False)
pitching.to_sql("Pitching", conn, if_exists="append", index=False)
salaries.to_sql("Salaries", conn, if_exists="append", index=False)
print("Loaded Batting, Pitching, Salaries")

# ── Verify row counts ────────────────────────────────────────
for name, df in zip(table_names, my_tables):
    cursor.execute(f"SELECT COUNT(*) FROM {name};")
    count = cursor.fetchone()[0]
    match = "✓" if count == len(df) else "✗"
    print(f"{match} {name}: SQLite={count}, DataFrame={len(df)}")

conn.close()
print(f"\nDone. Database written to {DB_FILE}")
