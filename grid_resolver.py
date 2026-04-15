"""
Maps each Immaculate Grid category label to a SQL query returning playerIDs.

Supports two modes:
  - Standalone: resolve_stat(label) -> set of playerIDs
  - Team-constrained: resolve_stat_for_team(label, franchID) -> set of playerIDs
    who achieved the stat WHILE playing for that franchise (same season/team).

Year-bound categories (season stats, positions, awards, all-star) are filtered
by team+year when paired with a team. Career/lifetime categories are not.
"""

import sqlite3

# Categories that we cannot resolve from our data
UNSUPPORTED_CATEGORIES = {
    "Threw a No\u2011Hitter",       # non-breaking hyphen
    "Threw a No-Hitter",
    "First Round Draft Pick",
    "Played In Major Negro\xa0Lgs",
    "Played In Major Negro Lgs",
}

# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def _normalize(label: str) -> str:
    """Normalize non-breaking spaces, hyphens, and special chars for matching."""
    s = label.replace("\xa0", " ").replace("\u2011", "-")
    s = s.replace("\u2264", "<=")  # ≤ -> <=
    return s


# ---------------------------------------------------------------------------
# Query definitions: standalone and team-constrained variants
# ---------------------------------------------------------------------------
# Each entry is (standalone_sql, team_sql_or_None)
# If team_sql is None, the category is NOT year-bound (career/lifetime),
# so team pairing just intersects independently.
# If team_sql is a string, it contains {franch_filter} placeholder that gets
# replaced with the franchise filter clause.

def _build_stat_queries() -> dict[str, tuple[str, str | None]]:
    """Return dict: normalized label -> (standalone_sql, team_constrained_sql | None)."""

    q = {}

    # --- Awards (year-bound: player won award in a year they played for the team) ---
    for label, award_id in [
        ("Gold Glove", "Gold Glove"),
        ("Silver Slugger", "Silver Slugger"),
        ("MVP", "Most Valuable Player"),
        ("Cy Young", "Cy Young Award"),
        ("Rookie of the Year", "Rookie of the Year"),
    ]:
        q[label] = (
            f"SELECT DISTINCT playerID FROM AwardsPlayers WHERE awardID = '{award_id}'",
            f"""SELECT DISTINCT a.playerID FROM AwardsPlayers a
                WHERE a.awardID = '{award_id}'
                AND a.playerID IN (
                    SELECT b.playerID FROM Batting b
                    JOIN Teams t ON b.teamID = t.teamID AND b.yearID = t.yearID
                    WHERE t.franchID = ? AND b.yearID = a.yearID
                    UNION
                    SELECT p.playerID FROM Pitching p
                    JOIN Teams t ON p.teamID = t.teamID AND p.yearID = t.yearID
                    WHERE t.franchID = ? AND p.yearID = a.yearID
                )""",
        )

    # --- All Star (year-bound) ---
    q["All Star"] = (
        "SELECT DISTINCT playerID FROM AllstarFull",
        """SELECT DISTINCT asf.playerID FROM AllstarFull asf
           JOIN Teams t ON asf.teamID = t.teamID AND asf.yearID = t.yearID
           WHERE t.franchID = ?""",
    )

    # --- Hall of Fame (NOT year-bound) ---
    q["Hall of Fame"] = (
        "SELECT DISTINCT playerID FROM HallOfFame WHERE inducted = 'Y'",
        None,
    )

    # --- World Series Champion (year-bound: on roster of WS-winning team) ---
    ws_standalone = """
        SELECT DISTINCT playerID FROM (
            SELECT bp.playerID, bp.teamID, bp.yearID FROM BattingPost bp WHERE bp.round = 'WS'
            UNION
            SELECT pp.playerID, pp.teamID, pp.yearID FROM PitchingPost pp WHERE pp.round = 'WS'
        ) ws
        JOIN Teams t ON ws.teamID = t.teamID AND ws.yearID = t.yearID
        WHERE t.WSWin = 'Y'
    """
    ws_team = """
        SELECT DISTINCT playerID FROM (
            SELECT bp.playerID, bp.teamID, bp.yearID FROM BattingPost bp WHERE bp.round = 'WS'
            UNION
            SELECT pp.playerID, pp.teamID, pp.yearID FROM PitchingPost pp WHERE pp.round = 'WS'
        ) ws
        JOIN Teams t ON ws.teamID = t.teamID AND ws.yearID = t.yearID
        WHERE t.WSWin = 'Y' AND t.franchID = ?
    """
    q["World Series ChampWS Roster"] = (ws_standalone, ws_team)

    # --- Positions (year-bound: played position for that team) ---
    position_map = {
        "Played Catchermin. 1 game": "G_c",
        "Played First Basemin. 1 game": "G_1b",
        "Played Second Basemin. 1 game": "G_2b",
        "Played Third Basemin. 1 game": "G_3b",
        "Played Shortstopmin. 1 game": "G_ss",
        "Played Left Fieldmin. 1 game": "G_lf",
        "Played Center Fieldmin. 1 game": "G_cf",
        "Played Right Fieldmin. 1 game": "G_rf",
        "Played Outfieldmin. 1 game": "G_of",
        "Pitchedmin. 1 game": "G_p",
        "Designated Hittermin. 1 game": "G_dh",
    }
    for label, col in position_map.items():
        q[label] = (
            f"SELECT DISTINCT playerID FROM Appearances WHERE {col} >= 1",
            f"""SELECT DISTINCT ap.playerID FROM Appearances ap
                JOIN Teams t ON ap.teamID = t.teamID AND ap.yearID = t.yearID
                WHERE ap.{col} >= 1 AND t.franchID = ?""",
        )

    q["PlayedMajor Leagues"] = (
        "SELECT DISTINCT playerID FROM Appearances",
        None,  # trivially satisfied if they played for the team
    )

    # --- Batting season thresholds (year-bound) ---
    batting_season = {
        ".300+ AVG SeasonBatting": "AB >= 1 AND (1.0 * H / AB) >= 0.300",
        "30+ HR SeasonBatting": "HR >= 30",
        "40+ HR SeasonBatting": "HR >= 40",
        "10+ HR SeasonBatting": "HR >= 10",
        "100+ RBI SeasonBatting": "RBI >= 100",
        "100+ Run SeasonBatting": "R >= 100",
        "200+ Hits SeasonBatting": "H >= 200",
        "40+ 2B SeasonBatting": '"2B" >= 40',
        "30+ SB Season": "SB >= 30",
    }
    for label, where in batting_season.items():
        q[label] = (
            f"SELECT DISTINCT playerID FROM Batting WHERE {where}",
            f"""SELECT DISTINCT b.playerID FROM Batting b
                JOIN Teams t ON b.teamID = t.teamID AND b.yearID = t.yearID
                WHERE {where.replace('AB', 'b.AB').replace('H', 'b.H').replace('HR', 'b.HR').replace('RBI', 'b.RBI').replace('R', 'b.R').replace('SB', 'b.SB')}
                AND t.franchID = ?""",
        )

    # Override the ones where naive replace would break (H -> b.H affects HR, etc.)
    # Let me just write these explicitly to be safe
    q[".300+ AVG SeasonBatting"] = (
        "SELECT DISTINCT playerID FROM Batting WHERE AB >= 1 AND (1.0 * H / AB) >= 0.300",
        """SELECT DISTINCT b.playerID FROM Batting b
           JOIN Teams t ON b.teamID = t.teamID AND b.yearID = t.yearID
           WHERE b.AB >= 1 AND (1.0 * b.H / b.AB) >= 0.300 AND t.franchID = ?""",
    )
    q["30+ HR SeasonBatting"] = (
        "SELECT DISTINCT playerID FROM Batting WHERE HR >= 30",
        """SELECT DISTINCT b.playerID FROM Batting b
           JOIN Teams t ON b.teamID = t.teamID AND b.yearID = t.yearID
           WHERE b.HR >= 30 AND t.franchID = ?""",
    )
    q["40+ HR SeasonBatting"] = (
        "SELECT DISTINCT playerID FROM Batting WHERE HR >= 40",
        """SELECT DISTINCT b.playerID FROM Batting b
           JOIN Teams t ON b.teamID = t.teamID AND b.yearID = t.yearID
           WHERE b.HR >= 40 AND t.franchID = ?""",
    )
    q["10+ HR SeasonBatting"] = (
        "SELECT DISTINCT playerID FROM Batting WHERE HR >= 10",
        """SELECT DISTINCT b.playerID FROM Batting b
           JOIN Teams t ON b.teamID = t.teamID AND b.yearID = t.yearID
           WHERE b.HR >= 10 AND t.franchID = ?""",
    )
    q["100+ RBI SeasonBatting"] = (
        "SELECT DISTINCT playerID FROM Batting WHERE RBI >= 100",
        """SELECT DISTINCT b.playerID FROM Batting b
           JOIN Teams t ON b.teamID = t.teamID AND b.yearID = t.yearID
           WHERE b.RBI >= 100 AND t.franchID = ?""",
    )
    q["100+ Run SeasonBatting"] = (
        "SELECT DISTINCT playerID FROM Batting WHERE R >= 100",
        """SELECT DISTINCT b.playerID FROM Batting b
           JOIN Teams t ON b.teamID = t.teamID AND b.yearID = t.yearID
           WHERE b.R >= 100 AND t.franchID = ?""",
    )
    q["200+ Hits SeasonBatting"] = (
        "SELECT DISTINCT playerID FROM Batting WHERE H >= 200",
        """SELECT DISTINCT b.playerID FROM Batting b
           JOIN Teams t ON b.teamID = t.teamID AND b.yearID = t.yearID
           WHERE b.H >= 200 AND t.franchID = ?""",
    )
    q["40+ 2B SeasonBatting"] = (
        'SELECT DISTINCT playerID FROM Batting WHERE "2B" >= 40',
        """SELECT DISTINCT b.playerID FROM Batting b
           JOIN Teams t ON b.teamID = t.teamID AND b.yearID = t.yearID
           WHERE b."2B" >= 40 AND t.franchID = ?""",
    )
    q["30+ SB Season"] = (
        "SELECT DISTINCT playerID FROM Batting WHERE SB >= 30",
        """SELECT DISTINCT b.playerID FROM Batting b
           JOIN Teams t ON b.teamID = t.teamID AND b.yearID = t.yearID
           WHERE b.SB >= 30 AND t.franchID = ?""",
    )

    # 6+ WAR Season (year-bound, but WAR is aggregated across batting+pitching)
    q["6+ WAR Season"] = (
        """SELECT DISTINCT playerID FROM (
            SELECT playerID, yearID, SUM(WAR) AS war FROM Batting GROUP BY playerID, yearID
            UNION ALL
            SELECT playerID, yearID, SUM(WAR) AS war FROM Pitching GROUP BY playerID, yearID
        ) GROUP BY playerID, yearID HAVING SUM(war) >= 6.0""",
        """SELECT DISTINCT sub.playerID FROM (
            SELECT b.playerID, b.yearID, SUM(b.WAR) AS war
            FROM Batting b
            JOIN Teams t ON b.teamID = t.teamID AND b.yearID = t.yearID
            WHERE t.franchID = ?
            GROUP BY b.playerID, b.yearID
            UNION ALL
            SELECT p.playerID, p.yearID, SUM(p.WAR) AS war
            FROM Pitching p
            JOIN Teams t ON p.teamID = t.teamID AND p.yearID = t.yearID
            WHERE t.franchID = ?
            GROUP BY p.playerID, p.yearID
        ) sub GROUP BY sub.playerID, sub.yearID HAVING SUM(sub.war) >= 6.0""",
    )

    # 30+ HR / 30+ SB season (year-bound)
    q["30+ HR /30+ SB SeasonBatting"] = (
        """SELECT DISTINCT playerID FROM (
            SELECT playerID, yearID, SUM(HR) AS hr, SUM(SB) AS sb
            FROM Batting GROUP BY playerID, yearID HAVING hr >= 30 AND sb >= 30
        )""",
        """SELECT DISTINCT sub.playerID FROM (
            SELECT b.playerID, b.yearID, SUM(b.HR) AS hr, SUM(b.SB) AS sb
            FROM Batting b
            JOIN Teams t ON b.teamID = t.teamID AND b.yearID = t.yearID
            WHERE t.franchID = ?
            GROUP BY b.playerID, b.yearID HAVING hr >= 30 AND sb >= 30
        ) sub""",
    )

    # --- Batting career thresholds (NOT year-bound) ---
    q[".300+ AVG CareerBatting"] = ("SELECT playerID FROM Career_Batting WHERE AVG >= 0.300 AND AB >= 1000", None)
    q["300+ HR CareerBatting"] = ("SELECT playerID FROM Career_Batting WHERE HR >= 300", None)
    q["500+ HR CareerBatting"] = ("SELECT playerID FROM Career_Batting WHERE HR >= 500", None)
    q["2000+ Hits CareerBatting"] = ("SELECT playerID FROM Career_Batting WHERE H >= 2000", None)
    q["3000+ Hits CareerBatting"] = ("SELECT playerID FROM Career_Batting WHERE H >= 3000", None)
    q["40+ WAR Career"] = (
        """SELECT playerID FROM (
            SELECT playerID, SUM(war) AS total_war FROM (
                SELECT playerID, WAR AS war FROM Career_Batting WHERE WAR IS NOT NULL
                UNION ALL
                SELECT playerID, WAR AS war FROM Career_Pitching WHERE WAR IS NOT NULL
            ) GROUP BY playerID HAVING total_war >= 40.0
        )""",
        None,
    )

    # --- Pitching season thresholds (year-bound) ---
    q["200+ K SeasonPitching"] = (
        "SELECT DISTINCT playerID FROM Pitching WHERE SO >= 200",
        """SELECT DISTINCT p.playerID FROM Pitching p
           JOIN Teams t ON p.teamID = t.teamID AND p.yearID = t.yearID
           WHERE p.SO >= 200 AND t.franchID = ?""",
    )
    q["10+ Win SeasonPitching"] = (
        "SELECT DISTINCT playerID FROM Pitching WHERE W >= 10",
        """SELECT DISTINCT p.playerID FROM Pitching p
           JOIN Teams t ON p.teamID = t.teamID AND p.yearID = t.yearID
           WHERE p.W >= 10 AND t.franchID = ?""",
    )
    q["20+ Win SeasonPitching"] = (
        "SELECT DISTINCT playerID FROM Pitching WHERE W >= 20",
        """SELECT DISTINCT p.playerID FROM Pitching p
           JOIN Teams t ON p.teamID = t.teamID AND p.yearID = t.yearID
           WHERE p.W >= 20 AND t.franchID = ?""",
    )
    q["30+ Save SeasonPitching"] = (
        "SELECT DISTINCT playerID FROM Pitching WHERE SV >= 30",
        """SELECT DISTINCT p.playerID FROM Pitching p
           JOIN Teams t ON p.teamID = t.teamID AND p.yearID = t.yearID
           WHERE p.SV >= 30 AND t.franchID = ?""",
    )
    q["40+ Save SeasonPitching"] = (
        "SELECT DISTINCT playerID FROM Pitching WHERE SV >= 40",
        """SELECT DISTINCT p.playerID FROM Pitching p
           JOIN Teams t ON p.teamID = t.teamID AND p.yearID = t.yearID
           WHERE p.SV >= 40 AND t.franchID = ?""",
    )
    q["<= 3.00 ERA Season"] = (
        "SELECT DISTINCT playerID FROM Pitching WHERE ERA <= 3.00 AND IPouts >= 162",
        """SELECT DISTINCT p.playerID FROM Pitching p
           JOIN Teams t ON p.teamID = t.teamID AND p.yearID = t.yearID
           WHERE p.ERA <= 3.00 AND p.IPouts >= 162 AND t.franchID = ?""",
    )

    # --- Pitching career thresholds (NOT year-bound) ---
    q["200+ Wins CareerPitching"] = ("SELECT playerID FROM Career_Pitching WHERE W >= 200", None)
    q["300+ Wins CareerPitching"] = ("SELECT playerID FROM Career_Pitching WHERE W >= 300", None)
    q["2000+ K CareerPitching"] = ("SELECT playerID FROM Career_Pitching WHERE SO >= 2000", None)
    q["3000+ K CareerPitching"] = ("SELECT playerID FROM Career_Pitching WHERE SO >= 3000", None)
    q["300+ Save CareerPitching"] = ("SELECT playerID FROM Career_Pitching WHERE SV >= 300", None)
    q["<= 3.00 ERA CareerPitching"] = (
        "SELECT playerID FROM Career_Pitching WHERE ERA <= 3.00 AND IPouts >= 1000",
        None,
    )

    # --- Other ---
    q["Only One Team"] = (
        """SELECT playerID FROM (
            SELECT b.playerID, COUNT(DISTINCT t.franchID) AS n_franch
            FROM Batting b
            JOIN Teams t ON b.teamID = t.teamID AND b.yearID = t.yearID
            GROUP BY b.playerID HAVING n_franch = 1
        )""",
        None,
    )
    q["Born Outside US 50 States and DC"] = (
        "SELECT playerID FROM People WHERE birthCountry != 'USA' AND birthCountry IS NOT NULL",
        None,
    )

    return q


# Pre-build the mapping
_STAT_QUERIES = _build_stat_queries()


def get_all_stat_labels() -> list[str]:
    """Return all supported stat labels (sorted)."""
    return sorted(_STAT_QUERIES.keys())


def is_unsupported(label: str) -> bool:
    """Check if a category label is unsupported."""
    return _normalize(label) in {_normalize(u) for u in UNSUPPORTED_CATEGORIES}


def _find_query(label: str) -> tuple[str, str | None] | None:
    """Find the query tuple for a label, handling normalization."""
    norm = _normalize(label)
    if norm in _STAT_QUERIES:
        return _STAT_QUERIES[norm]
    for key, val in _STAT_QUERIES.items():
        if _normalize(key) == norm:
            return val
    return None


def resolve_stat(conn: sqlite3.Connection, label: str) -> set[str]:
    """Resolve a stat label to a set of playerIDs (standalone, no team constraint)."""
    if is_unsupported(label):
        return set()

    entry = _find_query(label)
    if entry is None:
        return set()

    standalone_sql, _ = entry
    rows = conn.execute(standalone_sql).fetchall()
    return {row[0] for row in rows}


def resolve_stat_for_team(conn: sqlite3.Connection, label: str, franch_id: str) -> set[str]:
    """
    Resolve a stat label constrained to a specific franchise.

    For year-bound categories (season stats, positions, awards, all-star),
    returns only players who achieved the stat while playing for that franchise.

    For career/lifetime categories, falls back to intersection:
    players who satisfy the stat AND played for the franchise.
    """
    if is_unsupported(label):
        return set()

    entry = _find_query(label)
    if entry is None:
        return set()

    standalone_sql, team_sql = entry

    if team_sql is not None:
        # Year-bound: use the team-constrained query
        # Count how many ? placeholders the query needs
        n_params = team_sql.count("?")
        params = [franch_id] * n_params
        rows = conn.execute(team_sql, params).fetchall()
        return {row[0] for row in rows}
    else:
        # Not year-bound: intersect stat set with team set
        stat_set = {r[0] for r in conn.execute(standalone_sql).fetchall()}
        team_set = resolve_team(conn, franch_id)
        return stat_set & team_set


def resolve_team(conn: sqlite3.Connection, franch_id: str) -> set[str]:
    """Resolve a franchise ID to a set of playerIDs who played for that franchise."""
    sql = """
        SELECT DISTINCT playerID FROM (
            SELECT DISTINCT b.playerID FROM Batting b
            JOIN Teams t ON b.teamID = t.teamID AND b.yearID = t.yearID
            WHERE t.franchID = ?
            UNION
            SELECT DISTINCT p.playerID FROM Pitching p
            JOIN Teams t ON p.teamID = t.teamID AND p.yearID = t.yearID
            WHERE t.franchID = ?
        )
    """
    rows = conn.execute(sql, (franch_id, franch_id)).fetchall()
    return {row[0] for row in rows}


def resolve_cell(conn: sqlite3.Connection,
                 row_cond: tuple, col_cond: tuple) -> tuple[set[str], bool]:
    """
    Resolve a single grid cell (row_cond x col_cond) to a set of playerIDs.

    Each cond is (type, code, label).
    When a team is paired with a year-bound stat, enforces same-season constraint.

    Returns (player_set, has_unsupported).
    """
    r_type, r_code, r_label = row_cond
    c_type, c_code, c_label = col_cond

    # Check for unsupported
    if r_type == "stat" and is_unsupported(r_label):
        return set(), True
    if c_type == "stat" and is_unsupported(c_label):
        return set(), True

    if r_type == "team" and c_type == "team":
        # Both teams: intersection of players for each franchise
        return resolve_team(conn, r_code) & resolve_team(conn, c_code), False

    elif r_type == "team" and c_type == "stat":
        # Team + stat: use team-constrained resolver
        return resolve_stat_for_team(conn, c_label, r_code), False

    elif r_type == "stat" and c_type == "team":
        # Stat + team: use team-constrained resolver
        return resolve_stat_for_team(conn, r_label, c_code), False

    else:
        # Both stats: intersection
        return resolve_stat(conn, r_label) & resolve_stat(conn, c_label), False


def resolve_condition(conn: sqlite3.Connection, cond_type: str,
                      code: str | None, label: str) -> tuple[set[str], bool]:
    """
    Resolve a single grid condition (type/code/label) to a set of playerIDs.
    Returns (player_set, is_unsupported_flag).

    NOTE: For grid solving, prefer resolve_cell() which handles team+stat pairing.
    This function is still useful for the Condition Explorer (standalone lookups).
    """
    if cond_type == "team":
        return resolve_team(conn, code), False
    else:
        if is_unsupported(label):
            return set(), True
        return resolve_stat(conn, label), False


def get_career_war(conn: sqlite3.Connection, player_ids: set[str]) -> dict[str, tuple[str, float]]:
    """Get career WAR + name for a set of players. Returns {playerID: (name, war)}."""
    if not player_ids:
        return {}
    placeholders = ",".join("?" for _ in player_ids)
    pids = list(player_ids)
    rows = conn.execute(f"""
        SELECT p.playerID,
               p.nameFirst || ' ' || p.nameLast AS name,
               COALESCE(cb.WAR, 0) + COALESCE(cp.WAR, 0) AS career_war
        FROM People p
        LEFT JOIN Career_Batting cb ON p.playerID = cb.playerID
        LEFT JOIN Career_Pitching cp ON p.playerID = cp.playerID
        WHERE p.playerID IN ({placeholders})
    """, pids).fetchall()
    return {r[0]: (r[1], r[2] or 0.0) for r in rows}
