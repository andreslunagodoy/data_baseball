import streamlit as st
import pandas as pd
import sqlite3
import csv
import math
from itertools import product
from grid_resolver import (
    resolve_condition,
    resolve_cell,
    get_career_war,
    get_all_stat_labels,
    is_unsupported,
    _normalize,
    resolve_stat,
    resolve_stat_for_team,
    resolve_team,
)

st.set_page_config(page_title="Baseball Explorer", layout="wide")

# ── DB connection ─────────────────────────────────────────────
@st.cache_resource
def get_connection():
    conn = sqlite3.connect("databases/war_games.db", check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

conn = get_connection()

def q(query, params=None):
    return pd.read_sql_query(query, conn, params=params)


# ── Shared data loaders ──────────────────────────────────────
@st.cache_data
def get_franchises():
    df = q("""
        SELECT DISTINCT tf.franchID, tf.franchName
        FROM TeamsFranchises tf
        WHERE tf.active = 'Y'
        ORDER BY tf.franchName
    """)
    return dict(zip(df["franchID"], df["franchName"]))

@st.cache_data
def get_all_players():
    return q("""
        SELECT playerID, nameFirst, nameLast,
               nameFirst || ' ' || nameLast AS fullName,
               debut, finalGame
        FROM People
        WHERE playerID IN (SELECT DISTINCT playerID FROM Batting)
           OR playerID IN (SELECT DISTINCT playerID FROM Pitching)
        ORDER BY nameLast, nameFirst
    """)

@st.cache_data
def load_grids():
    rows = []
    with open("scraper_ig/immaculate_grids.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows

@st.cache_data
def get_grid_condition_options():
    """All possible conditions for the 'make your own grid' mode."""
    franchises = get_franchises()
    options = []
    for fid, fname in sorted(franchises.items(), key=lambda x: x[1]):
        options.append(("team", fid, fname))
    for label in get_all_stat_labels():
        options.append(("stat", None, label))
    return options


# ── Tab definitions ───────────────────────────────────────────
tab_home, tab_player, tab_conditions, tab_grid = st.tabs([
    "Home", "Player Lookup", "Condition Explorer", "Immaculate Grid"
])


# ══════════════════════════════════════════════════════════════
# TAB 1: HOME
# ══════════════════════════════════════════════════════════════
with tab_home:
    st.title("Baseball Explorer")
    st.markdown("""
    A tool for exploring MLB stats and solving
    [Immaculate Grid](https://www.immaculategrid.com/) puzzles.

    **Player Lookup** — Pick a player, see their stats season by season.

    **Condition Explorer** — Combine conditions (teams, awards, stat milestones)
    and find which players match all of them. Great for answering questions like
    *"Who played for the Yankees AND won an MVP while there?"*

    **Immaculate Grid** — Solve any of the 1,102 grids scraped from the website,
    or build your own by picking 6 conditions.

    ---
    *Data: [Lahman Database](https://www.seanlahman.com/) (1871–present) +
    [Baseball Reference](https://www.baseball-reference.com/) WAR.*
    """)


# ══════════════════════════════════════════════════════════════
# TAB 2: PLAYER LOOKUP
# ══════════════════════════════════════════════════════════════
with tab_player:
    st.header("Player Lookup")
    st.markdown("Search for a player to see their batting and pitching stats, year by year. Use the year filter to narrow the range.")

    players_df = get_all_players()
    # Build "Name (playerID)" labels for selectbox
    player_labels = (players_df["fullName"] + "  (" + players_df["playerID"] + ")").tolist()
    player_ids = players_df["playerID"].tolist()

    selected_idx = st.selectbox(
        "Search for a player",
        options=player_labels,
        key="player_select",
    )

    pid = player_ids[player_labels.index(selected_idx)]

    # Year range filter
    col_a, col_b = st.columns(2)
    with col_a:
        year_min = st.number_input("From year", value=1871, min_value=1871, max_value=2025, key="yr_min")
    with col_b:
        year_max = st.number_input("To year", value=2025, min_value=1871, max_value=2025, key="yr_max")

    # Player bio
    bio = q("SELECT * FROM People WHERE playerID = ?", [pid])
    if not bio.empty:
        p = bio.iloc[0]
        st.subheader(f"{p['nameFirst']} {p['nameLast']}")
        bio_parts = []
        if pd.notna(p.get("birthYear")):
            bio_parts.append(f"Born: {int(p['birthYear'])}")
        if pd.notna(p.get("birthCountry")) and pd.notna(p.get("birthCity")):
            bio_parts.append(f"{p['birthCity']}, {p.get('birthState', '')}, {p['birthCountry']}")
        if pd.notna(p.get("debut")):
            bio_parts.append(f"Debut: {p['debut']}")
        if pd.notna(p.get("finalGame")):
            bio_parts.append(f"Final game: {p['finalGame']}")
        if pd.notna(p.get("bats")):
            bio_parts.append(f"Bats: {p['bats']} / Throws: {p.get('throws', '?')}")
        st.markdown(" | ".join(bio_parts))

    # Batting stats
    batting = q("""
        SELECT b.yearID, b.teamID, b.stint, b.G, b.AB, b.R, b.H,
               b."2B", b."3B", b.HR, b.RBI, b.SB, b.CS, b.BB, b.SO,
               b.HBP, b.SF, b.WAR,
               CASE WHEN b.AB > 0 THEN ROUND(1.0 * b.H / b.AB, 3) END AS AVG,
               CASE WHEN (b.AB + COALESCE(b.BB,0) + COALESCE(b.HBP,0) + COALESCE(b.SF,0)) > 0
                    THEN ROUND(1.0 * (b.H + COALESCE(b.BB,0) + COALESCE(b.HBP,0))
                         / (b.AB + COALESCE(b.BB,0) + COALESCE(b.HBP,0) + COALESCE(b.SF,0)), 3) END AS OBP,
               CASE WHEN b.AB > 0
                    THEN ROUND(1.0 * (b.H - b."2B" - b."3B" - b.HR
                         + 2*b."2B" + 3*b."3B" + 4*b.HR) / b.AB, 3) END AS SLG
        FROM Batting b
        WHERE b.playerID = ? AND b.yearID BETWEEN ? AND ?
        ORDER BY b.yearID, b.stint
    """, [pid, year_min, year_max])

    if not batting.empty:
        batting["OPS"] = batting["OBP"].add(batting["SLG"])
        batting["OPS"] = batting["OPS"].round(3)
        st.subheader("Batting")
        st.dataframe(batting, width="stretch", hide_index=True)

        # Career totals
        career_bat = q("SELECT * FROM Career_Batting WHERE playerID = ?", [pid])
        if not career_bat.empty:
            st.markdown("**Career Totals**")
            st.dataframe(career_bat, width="stretch", hide_index=True)

    # Pitching stats
    pitching = q("""
        SELECT p.yearID, p.teamID, p.stint, p.W, p.L, p.G, p.GS, p.CG, p.SHO,
               p.SV, p.IPouts, p.H, p.ER, p.HR, p.BB, p.SO, p.WAR,
               p.ERA,
               CASE WHEN p.IPouts > 0
                    THEN ROUND((p.BB + p.H) / (p.IPouts / 3.0), 3) END AS WHIP
        FROM Pitching p
        WHERE p.playerID = ? AND p.yearID BETWEEN ? AND ?
        ORDER BY p.yearID, p.stint
    """, [pid, year_min, year_max])

    if not pitching.empty:
        # Convert IPouts to IP for display
        pitching.insert(
            pitching.columns.get_loc("IPouts") + 1,
            "IP",
            pitching["IPouts"].apply(lambda x: f"{x // 3}.{x % 3}" if pd.notna(x) else None),
        )
        st.subheader("Pitching")
        st.dataframe(pitching, width="stretch", hide_index=True)

        career_pit = q("SELECT * FROM Career_Pitching WHERE playerID = ?", [pid])
        if not career_pit.empty:
            st.markdown("**Career Totals**")
            st.dataframe(career_pit, width="stretch", hide_index=True)

    if batting.empty and pitching.empty:
        st.info("No batting or pitching stats found for this player in the selected year range.")


# ══════════════════════════════════════════════════════════════
# TAB 3: CONDITION EXPLORER
# ══════════════════════════════════════════════════════════════
with tab_conditions:
    st.header("Condition Explorer")
    st.markdown("Pick up to 5 conditions — teams, awards, stat thresholds, positions — and see which players satisfy **all** of them. By default, season-level stats must have been achieved while on the selected team (like in Immaculate Grid).")

    # Build unified options list: teams + stats
    stat_labels = get_all_stat_labels()
    franchises = get_franchises()

    cond_options = ["(none)"]
    cond_data = [None]  # parallel list: (type, code, label) or None
    for fid, fname in sorted(franchises.items(), key=lambda x: x[1]):
        cond_options.append(f"Team: {fname}")
        cond_data.append(("team", fid, fname))
    for label in stat_labels:
        cond_options.append(f"Stat: {label}")
        cond_data.append(("stat", None, label))

    selected = []
    cols = st.columns(5)
    for i in range(5):
        with cols[i]:
            idx = st.selectbox(
                f"Condition {i+1}",
                cond_options,
                key=f"cond_{i}",
            )
            if idx != "(none)":
                selected.append(cond_data[cond_options.index(idx)])

    col_mode, col_constraint = st.columns(2)
    with col_mode:
        mode = st.radio("Display mode", ["Highest career WAR", "Lowest career WAR", "Random"], horizontal=True)
    with col_constraint:
        constraint_mode = st.radio(
            "Resolution mode",
            ["Team-constrained (Immaculate Grid rules)", "Standalone (independent intersection)"],
            horizontal=True,
            help="Team-constrained: year-bound stats (season, awards, positions) must be achieved while on the selected team(s). Standalone: conditions are resolved independently and intersected.",
        )
    use_team_constraint = constraint_mode.startswith("Team")

    if st.button("Show players", key="cond_show"):
        if not selected:
            st.warning("Select at least one condition.")
        else:
            unsupported_labels = [c[2] for c in selected if c[0] == "stat" and is_unsupported(c[2])]
            if unsupported_labels:
                st.warning(f"Unsupported categories (requires external data): {', '.join(unsupported_labels)}")
            else:
                teams = [c for c in selected if c[0] == "team"]
                stats = [c for c in selected if c[0] == "stat"]

                if use_team_constraint and teams and stats:
                    # Team-constrained: for each stat, resolve against each team,
                    # then intersect all results
                    player_set = None
                    for cond_type, code, label in selected:
                        if cond_type == "team":
                            pids = resolve_team(conn, code)
                        else:
                            # Intersect this stat constrained to each team
                            stat_set = None
                            for _, fid, _ in teams:
                                team_pids = resolve_stat_for_team(conn, label, fid)
                                if stat_set is None:
                                    stat_set = team_pids
                                else:
                                    stat_set = stat_set & team_pids
                            pids = stat_set or set()
                        if player_set is None:
                            player_set = pids
                        else:
                            player_set = player_set & pids
                else:
                    # Standalone: resolve each independently and intersect
                    player_set = None
                    for cond_type, code, label in selected:
                        if cond_type == "team":
                            pids = resolve_team(conn, code)
                        else:
                            pids = resolve_stat(conn, label)
                        if player_set is None:
                            player_set = pids
                        else:
                            player_set = player_set & pids

                if not player_set:
                    st.info("No players satisfy all selected conditions.")
                else:
                    war_lookup = get_career_war(conn, player_set)
                    rows = [(pid, name, war) for pid, (name, war) in war_lookup.items()]

                    if mode == "Highest career WAR":
                        rows.sort(key=lambda x: x[2], reverse=True)
                        rows = rows[:10]
                    elif mode == "Lowest career WAR":
                        rows.sort(key=lambda x: x[2])
                        rows = rows[:10]
                    else:
                        import random
                        rows = random.sample(rows, min(10, len(rows)))

                    result_df = pd.DataFrame(rows, columns=["playerID", "Name", "Career WAR"])
                    result_df["Career WAR"] = result_df["Career WAR"].round(1)
                    result_df.index = range(1, len(result_df) + 1)
                    cond_desc = " + ".join(c[2] for c in selected)
                    st.markdown(f"**{len(player_set)}** players satisfy all conditions ({cond_desc}). Showing {len(result_df)}:")
                    st.dataframe(result_df[["Name", "Career WAR"]], width="stretch")


# ══════════════════════════════════════════════════════════════
# TAB 4: IMMACULATE GRID
# ══════════════════════════════════════════════════════════════
with tab_grid:
    st.header("Immaculate Grid")
    st.markdown("Fill a 3x3 grid where each cell needs a player who matches both its row and column condition. The solver finds a solution using 9 different players, preferring those with the highest career WAR.")

    grid_mode = st.radio("Mode", ["Solve a scraped grid", "Make your own grid"], horizontal=True)

    # ── Shared solver ─────────────────────────────────────────
    def solve_grid(row_conds, col_conds):
        """
        row_conds, col_conds: list of 3 tuples (type, code, label).
        Returns (grid, war_lookup, candidates, unsupported_cells) or (None, ...).

        Uses resolve_cell() to enforce same-season constraints when a team
        is paired with a year-bound stat (season stats, positions, awards, all-star).
        """
        cells = list(product(range(3), range(3)))
        all_candidates = set()
        candidates = {}
        unsupported_cells = set()

        for ri, ci in cells:
            cell_set, has_unsup = resolve_cell(conn, row_conds[ri], col_conds[ci])
            if has_unsup:
                unsupported_cells.add((ri, ci))
                candidates[(ri, ci)] = []
            else:
                candidates[(ri, ci)] = list(cell_set)
                all_candidates |= cell_set

        war_lookup = get_career_war(conn, all_candidates)

        # Sort candidates by WAR descending
        for cell in candidates:
            candidates[cell] = sorted(
                [pid for pid in candidates[cell] if pid in war_lookup],
                key=lambda pid: war_lookup[pid][1],
                reverse=True,
            )

        # Backtracking solver
        solvable_cells = [c for c in cells if c not in unsupported_cells]
        cell_order = sorted(solvable_cells, key=lambda c: len(candidates[c]))
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
            return None, war_lookup, candidates, unsupported_cells

        return grid, war_lookup, candidates, unsupported_cells

    def display_grid(grid, war_lookup, candidates, unsupported_cells, row_labels, col_labels):
        """Display the solved grid as a table."""
        header = [""] + col_labels
        table_rows = []
        for ri in range(3):
            row_data = [row_labels[ri]]
            for ci in range(3):
                if (ri, ci) in unsupported_cells:
                    row_data.append("(unsupported category)")
                elif grid and (ri, ci) in grid:
                    pid = grid[(ri, ci)]
                    name, war = war_lookup[pid]
                    row_data.append(f"{name} ({war:.1f} WAR)")
                else:
                    row_data.append("—")
            table_rows.append(row_data)

        result_df = pd.DataFrame(table_rows, columns=header)
        st.table(result_df)

        # Show candidates per cell
        st.markdown("### Candidates per cell")
        for ri in range(3):
            for ci in range(3):
                if (ri, ci) in unsupported_cells:
                    st.write(f"**{row_labels[ri]}** × **{col_labels[ci]}**: unsupported")
                else:
                    n = len(candidates[(ri, ci)])
                    st.write(f"**{row_labels[ri]}** × **{col_labels[ci]}**: {n} eligible players")

    # ── Mode A: Solve a scraped grid ──────────────────────────
    if grid_mode == "Solve a scraped grid":
        grids = load_grids()
        grid_num = st.number_input("Grid number", min_value=1, max_value=len(grids), value=1)

        g = grids[grid_num - 1]

        # Display conditions
        st.markdown("### Grid conditions")
        cond_cols = st.columns(2)
        with cond_cols[0]:
            st.markdown("**Rows**")
            for pos in ["row1", "row2", "row3"]:
                st.write(f"- {g[f'{pos}_label']}")
        with cond_cols[1]:
            st.markdown("**Columns**")
            for pos in ["col1", "col2", "col3"]:
                st.write(f"- {g[f'{pos}_label']}")

        if st.button("Solve", key="solve_scraped"):
            row_conds = [
                (g["row1_type"], g.get("row1_code", ""), g["row1_label"]),
                (g["row2_type"], g.get("row2_code", ""), g["row2_label"]),
                (g["row3_type"], g.get("row3_code", ""), g["row3_label"]),
            ]
            col_conds = [
                (g["col1_type"], g.get("col1_code", ""), g["col1_label"]),
                (g["col2_type"], g.get("col2_code", ""), g["col2_label"]),
                (g["col3_type"], g.get("col3_code", ""), g["col3_label"]),
            ]

            # Handle NaN codes
            for i, c in enumerate(row_conds):
                if c[1] == "" or (isinstance(c[1], str) and c[1].lower() == "nan"):
                    row_conds[i] = (c[0], None, c[2])
            for i, c in enumerate(col_conds):
                if c[1] == "" or (isinstance(c[1], str) and c[1].lower() == "nan"):
                    col_conds[i] = (c[0], None, c[2])

            with st.spinner("Solving..."):
                grid_solution, war_lookup, candidates, unsupported = solve_grid(row_conds, col_conds)

            if unsupported:
                st.warning("Some cells involve unsupported categories and will be skipped.")

            row_labels = [g["row1_label"], g["row2_label"], g["row3_label"]]
            col_labels = [g["col1_label"], g["col2_label"], g["col3_label"]]

            if grid_solution is None and not unsupported:
                st.error("No valid solution found for this grid.")
            else:
                st.markdown("### Solution")
                display_grid(grid_solution, war_lookup, candidates, unsupported, row_labels, col_labels)

    # ── Mode B: Make your own grid ────────────────────────────
    else:
        st.markdown("Select 3 row conditions and 3 column conditions.")

        all_options = get_grid_condition_options()
        option_labels = []
        for opt in all_options:
            if opt[0] == "team":
                option_labels.append(f"🏟 {opt[2]}")
            else:
                option_labels.append(f"📊 {opt[2]}")

        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("**Rows**")
            r1 = st.selectbox("Row 1", option_labels, key="custom_r1", index=0)
            r2 = st.selectbox("Row 2", option_labels, key="custom_r2", index=1)
            r3 = st.selectbox("Row 3", option_labels, key="custom_r3", index=2)

        with col_right:
            st.markdown("**Columns**")
            c1 = st.selectbox("Col 1", option_labels, key="custom_c1", index=3)
            c2 = st.selectbox("Col 2", option_labels, key="custom_c2", index=4)
            c3 = st.selectbox("Col 3", option_labels, key="custom_c3", index=5)

        if st.button("Solve custom grid", key="solve_custom"):
            r1i, r2i, r3i = option_labels.index(r1), option_labels.index(r2), option_labels.index(r3)
            c1i, c2i, c3i = option_labels.index(c1), option_labels.index(c2), option_labels.index(c3)
            row_conds = [all_options[r1i], all_options[r2i], all_options[r3i]]
            col_conds = [all_options[c1i], all_options[c2i], all_options[c3i]]

            row_labels = [r1, r2, r3]
            col_labels = [c1, c2, c3]

            with st.spinner("Solving..."):
                grid_solution, war_lookup, candidates, unsupported = solve_grid(row_conds, col_conds)

            if unsupported:
                st.warning("Some cells involve unsupported categories and will be skipped.")

            if grid_solution is None and not unsupported:
                st.error("No valid solution found for this grid.")
            else:
                st.markdown("### Solution")
                display_grid(grid_solution, war_lookup, candidates, unsupported, row_labels, col_labels)
