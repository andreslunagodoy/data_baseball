import streamlit as st
import pandas as pd
import sqlite3
from itertools import product

st.set_page_config(page_title="Immaculate Grid Solver", layout="wide")
st.title("Immaculate Grid Solver")

# ── DB connection ─────────────────────────────────────────────
@st.cache_resource
def get_connection():
    conn = sqlite3.connect("databases/war_games.db", check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

conn = get_connection()

def q(query):
    return pd.read_sql_query(query, conn)

# ── Load franchise list ───────────────────────────────────────
@st.cache_data
def get_franchises():
    df = q("""
        SELECT DISTINCT t.franchID, MAX(t.name) AS name
        FROM Teams t
        WHERE t.yearID >= 2000
        GROUP BY t.franchID
        ORDER BY t.franchID
    """)
    return dict(zip(df["franchID"], df["name"]))

franchises = get_franchises()
franchise_ids = list(franchises.keys())
franchise_labels = {fid: f"{fid} — {name}" for fid, name in franchises.items()}

# ── Dropdowns ─────────────────────────────────────────────────
st.markdown("### Select 3 row teams and 3 column teams")

col_left, col_right = st.columns(2)

with col_left:
    st.markdown("**Row teams (left side)**")
    row1 = st.selectbox("Row 1", franchise_ids, index=franchise_ids.index("NYY"), format_func=lambda x: franchise_labels[x], key="r1")
    row2 = st.selectbox("Row 2", franchise_ids, index=franchise_ids.index("BOS"), format_func=lambda x: franchise_labels[x], key="r2")
    row3 = st.selectbox("Row 3", franchise_ids, index=franchise_ids.index("LAD"), format_func=lambda x: franchise_labels[x], key="r3")

with col_right:
    st.markdown("**Column teams (top)**")
    col1 = st.selectbox("Col 1", franchise_ids, index=franchise_ids.index("CHC"), format_func=lambda x: franchise_labels[x], key="c1")
    col2 = st.selectbox("Col 2", franchise_ids, index=franchise_ids.index("ATL"), format_func=lambda x: franchise_labels[x], key="c2")
    col3 = st.selectbox("Col 3", franchise_ids, index=franchise_ids.index("HOU"), format_func=lambda x: franchise_labels[x], key="c3")

rows = [row1, row2, row3]
cols = [col1, col2, col3]

# ── Resolver: players who played for a franchise ──────────────
@st.cache_data
def resolve_franchise(fid):
    df = q(f"""
        SELECT DISTINCT b.playerID FROM Batting_with_WAR b
        JOIN Teams t ON b.teamID = t.teamID AND b.yearID = t.yearID
        WHERE t.franchID = '{fid}'
        UNION
        SELECT DISTINCT p.playerID FROM Pitching_with_WAR p
        JOIN Teams t ON p.teamID = t.teamID AND p.yearID = t.yearID
        WHERE t.franchID = '{fid}'
    """)
    return set(df["playerID"])

# ── WAR lookup (batting + pitching) ──────────────────────────
@st.cache_data
def get_war_lookup(player_ids_tuple):
    player_ids = list(player_ids_tuple)
    if not player_ids:
        return {}
    placeholders = ",".join(f"'{pid}'" for pid in player_ids)
    df = q(f"""
        SELECT playerID, name, SUM(war) AS career_WAR FROM (
            SELECT b.playerID,
                   p.nameFirst || ' ' || p.nameLast AS name,
                   COALESCE(b.WAR, 0) AS war
            FROM Batting_with_WAR b
            JOIN People p ON b.playerID = p.playerID
            WHERE b.playerID IN ({placeholders})
            UNION ALL
            SELECT pt.playerID,
                   p.nameFirst || ' ' || p.nameLast AS name,
                   COALESCE(pt.WAR, 0) AS war
            FROM Pitching_with_WAR pt
            JOIN People p ON pt.playerID = p.playerID
            WHERE pt.playerID IN ({placeholders})
        )
        GROUP BY playerID
    """)
    return {row["playerID"]: (row["name"], row["career_WAR"]) for _, row in df.iterrows()}

# ── Solver ────────────────────────────────────────────────────
def solve_grid(rows, cols):
    resolved = {}
    for label in set(rows + cols):
        resolved[label] = resolve_franchise(label)

    cells = list(product(rows, cols))
    all_candidates = set()
    candidates = {}
    for r, c in cells:
        both = resolved[r] & resolved[c]
        candidates[(r, c)] = both
        all_candidates |= both

    lookup = get_war_lookup(tuple(sorted(all_candidates)))

    for cell in candidates:
        candidates[cell] = sorted(
            [pid for pid in candidates[cell] if pid in lookup],
            key=lambda pid: lookup[pid][1],
            reverse=True,
        )

    cell_order = sorted(cells, key=lambda cell: len(candidates[cell]))
    used = set()
    grid = {}

    def backtrack(idx):
        if idx == len(cell_order):
            return True
        cell = cell_order[idx]
        for pid in candidates[cell]:
            if pid not in used:
                used.add(pid)
                grid[cell] = pid
                if backtrack(idx + 1):
                    return True
                used.remove(pid)
                del grid[cell]
        return False

    if not backtrack(0):
        return None, None, None

    return grid, lookup, candidates

# ── Run ───────────────────────────────────────────────────────
if st.button("Solve Grid", type="primary"):
    with st.spinner("Solving..."):
        grid, lookup, candidates = solve_grid(rows, cols)

    if grid is None:
        st.error("No valid grid found for these teams.")
    else:
        st.markdown("### Solution")

        header = [""] + [franchise_labels[c] for c in cols]
        table_rows = []
        for r in rows:
            row_data = [franchise_labels[r]]
            for c in cols:
                pid = grid[(r, c)]
                name, war = lookup[pid]
                row_data.append(f"{name} ({war:.1f} WAR)")
            table_rows.append(row_data)

        result_df = pd.DataFrame(table_rows, columns=header)
        st.table(result_df)

        st.markdown("### Candidates per cell")
        for r in rows:
            for c in cols:
                n = len(candidates[(r, c)])
                st.write(f"**{franchises[r]}** x **{franchises[c]}**: {n} eligible players")
