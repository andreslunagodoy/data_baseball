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
# Display labels: clean versions for the UI
# ---------------------------------------------------------------------------

_DISPLAY_LABELS = {
    # Awards
    "Gold Glove": "Gold Glove",
    "Silver Slugger": "Silver Slugger",
    "MVP": "MVP",
    "Cy Young": "Cy Young",
    "Rookie of the Year": "Rookie of the Year",
    # Accolades
    "All Star": "All-Star",
    "Hall of Fame": "Hall of Fame",
    "World Series ChampWS Roster": "World Series Champ",
    # Positions
    "Played Catchermin. 1 game": "Played Catcher",
    "Played First Basemin. 1 game": "Played 1B",
    "Played Second Basemin. 1 game": "Played 2B",
    "Played Third Basemin. 1 game": "Played 3B",
    "Played Shortstopmin. 1 game": "Played SS",
    "Played Left Fieldmin. 1 game": "Played LF",
    "Played Center Fieldmin. 1 game": "Played CF",
    "Played Right Fieldmin. 1 game": "Played RF",
    "Played Outfieldmin. 1 game": "Played OF",
    "Pitchedmin. 1 game": "Pitched",
    "Designated Hittermin. 1 game": "Played DH",
    "PlayedMajor Leagues": "Played in MLB",
    # Batting season
    ".300+ AVG SeasonBatting": ".300+ AVG (season)",
    "30+ HR SeasonBatting": "30+ HR (season)",
    "40+ HR SeasonBatting": "40+ HR (season)",
    "10+ HR SeasonBatting": "10+ HR (season)",
    "100+ RBI SeasonBatting": "100+ RBI (season)",
    "100+ Run SeasonBatting": "100+ R (season)",
    "200+ Hits SeasonBatting": "200+ H (season)",
    "40+ 2B SeasonBatting": "40+ 2B (season)",
    "30+ SB Season": "30+ SB (season)",
    "6+ WAR Season": "6+ WAR (season)",
    "30+ HR /30+ SB SeasonBatting": "30+ HR & 30+ SB (season)",
    # Batting career
    ".300+ AVG CareerBatting": ".300+ AVG (career)",
    "300+ HR CareerBatting": "300+ HR (career)",
    "500+ HR CareerBatting": "500+ HR (career)",
    "2000+ Hits CareerBatting": "2000+ H (career)",
    "3000+ Hits CareerBatting": "3000+ H (career)",
    "40+ WAR Career": "40+ WAR (career)",
    # Pitching season
    "200+ K SeasonPitching": "200+ K (season)",
    "10+ Win SeasonPitching": "10+ W (season)",
    "20+ Win SeasonPitching": "20+ W (season)",
    "30+ Save SeasonPitching": "30+ SV (season)",
    "40+ Save SeasonPitching": "40+ SV (season)",
    "<= 3.00 ERA Season": "≤ 3.00 ERA (season)",
    # Pitching career
    "200+ Wins CareerPitching": "200+ W (career)",
    "300+ Wins CareerPitching": "300+ W (career)",
    "2000+ K CareerPitching": "2000+ K (career)",
    "3000+ K CareerPitching": "3000+ K (career)",
    "300+ Save CareerPitching": "300+ SV (career)",
    "<= 3.00 ERA CareerPitching": "≤ 3.00 ERA (career)",
    # Other
    "Only One Team": "Only One Team",
    "Born Outside US 50 States and DC": "Born Outside US",
}

# Reverse mapping: display label -> internal label
_INTERNAL_LABELS = {v: k for k, v in _DISPLAY_LABELS.items()}


def display_label(label: str) -> str:
    """Convert an internal/scraped label to a clean display label."""
    norm = _normalize(label)
    if norm in _DISPLAY_LABELS:
        return _DISPLAY_LABELS[norm]
    for key, val in _DISPLAY_LABELS.items():
        if _normalize(key) == norm:
            return val
    return label


def internal_label(disp: str) -> str:
    """Convert a display label back to the internal label."""
    return _INTERNAL_LABELS.get(disp, disp)


_ORDERED_LABELS = [
    # Season stats - batting
    ".300+ AVG SeasonBatting",
    "10+ HR SeasonBatting",
    "30+ HR SeasonBatting",
    "40+ HR SeasonBatting",
    "100+ RBI SeasonBatting",
    "100+ Run SeasonBatting",
    "200+ Hits SeasonBatting",
    "40+ 2B SeasonBatting",
    "30+ SB Season",
    "30+ HR /30+ SB SeasonBatting",
    # Season stats - pitching
    "10+ Win SeasonPitching",
    "20+ Win SeasonPitching",
    "200+ K SeasonPitching",
    "30+ Save SeasonPitching",
    "40+ Save SeasonPitching",
    "<= 3.00 ERA Season",
    # Season stats - general
    "6+ WAR Season",
    # Career stats - batting
    ".300+ AVG CareerBatting",
    "300+ HR CareerBatting",
    "500+ HR CareerBatting",
    "2000+ Hits CareerBatting",
    "3000+ Hits CareerBatting",
    # Career stats - pitching
    "200+ Wins CareerPitching",
    "300+ Wins CareerPitching",
    "2000+ K CareerPitching",
    "3000+ K CareerPitching",
    "300+ Save CareerPitching",
    "<= 3.00 ERA CareerPitching",
    # Career stats - general
    "40+ WAR Career",
    # Positions
    "Played Catchermin. 1 game",
    "Played First Basemin. 1 game",
    "Played Second Basemin. 1 game",
    "Played Third Basemin. 1 game",
    "Played Shortstopmin. 1 game",
    "Played Left Fieldmin. 1 game",
    "Played Center Fieldmin. 1 game",
    "Played Right Fieldmin. 1 game",
    "Played Outfieldmin. 1 game",
    "Pitchedmin. 1 game",
    "Designated Hittermin. 1 game",
    "PlayedMajor Leagues",
    # Awards
    "MVP",
    "Cy Young",
    "Gold Glove",
    "Silver Slugger",
    "Rookie of the Year",
    # Accolades
    "All Star",
    "Hall of Fame",
    "World Series ChampWS Roster",
    # Other
    "Only One Team",
    "Born Outside US 50 States and DC",
]


def get_all_display_labels() -> list[str]:
    """Return all supported display labels in curated order."""
    return [_DISPLAY_LABELS[k] for k in _ORDERED_LABELS]


def get_all_stat_labels_ordered() -> list[str]:
    """Return all supported internal labels in curated order."""
    return list(_ORDERED_LABELS)


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
        "SELECT DISTINCT playerID FROM HallOfFame WHERE inducted = 'Y' AND category = 'Player'",
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
            SELECT playerID, yearID, SUM(HR) AS tot_hr, SUM(SB) AS tot_sb
            FROM Batting GROUP BY playerID, yearID HAVING tot_hr >= 30 AND tot_sb >= 30
        )""",
        """SELECT DISTINCT sub.playerID FROM (
            SELECT b.playerID, b.yearID, SUM(b.HR) AS tot_hr, SUM(b.SB) AS tot_sb
            FROM Batting b
            JOIN Teams t ON b.teamID = t.teamID AND b.yearID = t.yearID
            WHERE t.franchID = ?
            GROUP BY b.playerID, b.yearID HAVING tot_hr >= 30 AND tot_sb >= 30
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


# ---------------------------------------------------------------------------
# Condition detail fetchers
# ---------------------------------------------------------------------------
# Each returns {playerID: detail_value} for display in the results table.

def _placeholders(pids):
    return ",".join("?" for _ in pids), list(pids)


def _get_team_detail(conn, player_ids, franch_id):
    """Per-team batting detail: years range, AB, HR, RBI, AVG, WAR."""
    ph, pids = _placeholders(player_ids)
    rows = conn.execute(f"""
        SELECT b.playerID,
               MIN(b.yearID) || '-' || MAX(b.yearID) AS years,
               SUM(b.AB) AS AB, SUM(b.H) AS H, SUM(b.HR) AS HR,
               SUM(b.RBI) AS RBI,
               CASE WHEN SUM(b.AB) > 0 THEN ROUND(1.0 * SUM(b.H) / SUM(b.AB), 3) END AS AVG,
               ROUND(SUM(b.WAR), 1) AS WAR
        FROM Batting b
        JOIN Teams t ON b.teamID = t.teamID AND b.yearID = t.yearID
        WHERE t.franchID = ? AND b.playerID IN ({ph})
        GROUP BY b.playerID
    """, [franch_id] + pids).fetchall()
    return {r[0]: {"Years": r[1], "AB": r[2], "H": r[3], "HR": r[4],
                    "RBI": r[5], "AVG": r[6], "WAR": r[7]} for r in rows}


def _get_team_detail_pitching(conn, player_ids, franch_id):
    """Per-team pitching detail: years range, IP, W, SO, ERA, SV, WAR."""
    ph, pids = _placeholders(player_ids)
    rows = conn.execute(f"""
        SELECT p.playerID,
               MIN(p.yearID) || '-' || MAX(p.yearID) AS years,
               SUM(p.W) AS W,
               SUM(p.SO) AS SO, SUM(p.SV) AS SV,
               SUM(p.IPouts) AS IPouts,
               CASE WHEN SUM(p.IPouts) > 0
                    THEN ROUND(9.0 * SUM(p.ER) / (SUM(p.IPouts) / 3.0), 2) END AS ERA,
               ROUND(SUM(p.WAR), 1) AS WAR
        FROM Pitching p
        JOIN Teams t ON p.teamID = t.teamID AND p.yearID = t.yearID
        WHERE t.franchID = ? AND p.playerID IN ({ph})
        GROUP BY p.playerID
    """, [franch_id] + pids).fetchall()
    return {r[0]: {"Years": r[1], "W": r[2],
                    "SO": r[3], "SV": r[4],
                    "IP": round(r[5] / 3, 1) if r[5] else 0,
                    "ERA": r[6], "WAR": r[7]} for r in rows}


def get_pitcher_set(conn, player_ids):
    """Determine which players are primarily pitchers.

    A player is a pitcher if their career games pitched > 50% of total games
    OR they have no batting record but do have a pitching record.
    """
    if not player_ids:
        return set()
    ph, pids = _placeholders(player_ids)
    rows = conn.execute(f"""
        SELECT a.playerID, SUM(a.G_p) AS gp, SUM(a.G_all) AS g_all
        FROM Appearances a
        WHERE a.playerID IN ({ph})
        GROUP BY a.playerID
    """, pids).fetchall()
    pitchers = set()
    for pid, gp, g_all in rows:
        if gp and g_all and gp > g_all * 0.5:
            pitchers.add(pid)
    return pitchers


def get_team_ab(conn, player_ids, franch_ids):
    """Get AB per team for a set of players. Returns {playerID: {franchID: AB}}."""
    if not player_ids or not franch_ids:
        return {}
    ph, pids = _placeholders(player_ids)
    franch_ph = ",".join("?" for _ in franch_ids)
    rows = conn.execute(f"""
        SELECT b.playerID, t.franchID, SUM(b.AB) AS ab
        FROM Batting b
        JOIN Teams t ON b.teamID = t.teamID AND b.yearID = t.yearID
        WHERE b.playerID IN ({ph}) AND t.franchID IN ({franch_ph})
        GROUP BY b.playerID, t.franchID
    """, pids + list(franch_ids)).fetchall()
    result = {}
    for pid, fid, ab in rows:
        result.setdefault(pid, {})[fid] = ab or 0
    return result


def get_team_ipouts(conn, player_ids, franch_ids):
    """Get IPouts per team for a set of players. Returns {playerID: {franchID: IPouts}}."""
    if not player_ids or not franch_ids:
        return {}
    ph, pids = _placeholders(player_ids)
    franch_ph = ",".join("?" for _ in franch_ids)
    rows = conn.execute(f"""
        SELECT p.playerID, t.franchID, SUM(p.IPouts) AS ipouts
        FROM Pitching p
        JOIN Teams t ON p.teamID = t.teamID AND p.yearID = t.yearID
        WHERE p.playerID IN ({ph}) AND t.franchID IN ({franch_ph})
        GROUP BY p.playerID, t.franchID
    """, pids + list(franch_ids)).fetchall()
    result = {}
    for pid, fid, ipouts in rows:
        result.setdefault(pid, {})[fid] = ipouts or 0
    return result


def _qualify_columns(where_clause, alias):
    """Add table alias to column names in a WHERE clause."""
    import re
    cols = ["AB", "HR", "RBI", "HBP", "SF", "SB", "IPouts", "ER",
            "ERA", "SO", "SV", "H", "R", "W", "L"]
    # Sort by length descending to avoid partial matches
    cols.sort(key=len, reverse=True)
    result = where_clause
    for col in cols:
        result = re.sub(rf'\b{col}\b', f'{alias}.{col}', result)
    # Handle quoted column "2B"
    result = result.replace('"2B"', f'{alias}."2B"')
    return result


def _get_season_batting_count(conn, player_ids, where_clause, franch_ids=None):
    """Count of seasons satisfying a batting threshold."""
    ph, pids = _placeholders(player_ids)
    qualified = _qualify_columns(where_clause, "b")
    if franch_ids:
        franch_ph = ",".join("?" for _ in franch_ids)
        rows = conn.execute(f"""
            SELECT b.playerID, COUNT(DISTINCT b.yearID) AS n
            FROM Batting b
            JOIN Teams t ON b.teamID = t.teamID AND b.yearID = t.yearID
            WHERE b.playerID IN ({ph}) AND t.franchID IN ({franch_ph}) AND {qualified}
            GROUP BY b.playerID
        """, pids + list(franch_ids)).fetchall()
    else:
        rows = conn.execute(f"""
            SELECT b.playerID, COUNT(DISTINCT b.yearID) AS n
            FROM Batting b
            WHERE b.playerID IN ({ph}) AND {qualified}
            GROUP BY b.playerID
        """, pids).fetchall()
    return {r[0]: r[1] for r in rows}


def _get_season_pitching_count(conn, player_ids, where_clause, franch_ids=None):
    """Count of seasons satisfying a pitching threshold."""
    ph, pids = _placeholders(player_ids)
    qualified = _qualify_columns(where_clause, "p")
    if franch_ids:
        franch_ph = ",".join("?" for _ in franch_ids)
        rows = conn.execute(f"""
            SELECT p.playerID, COUNT(DISTINCT p.yearID) AS n
            FROM Pitching p
            JOIN Teams t ON p.teamID = t.teamID AND p.yearID = t.yearID
            WHERE p.playerID IN ({ph}) AND t.franchID IN ({franch_ph}) AND {qualified}
            GROUP BY p.playerID
        """, pids + list(franch_ids)).fetchall()
    else:
        rows = conn.execute(f"""
            SELECT p.playerID, COUNT(DISTINCT p.yearID) AS n
            FROM Pitching p
            WHERE p.playerID IN ({ph}) AND {qualified}
            GROUP BY p.playerID
        """, pids).fetchall()
    return {r[0]: r[1] for r in rows}


# Mapping: internal label -> (column_name, detail_type, extra_args)
# detail_type: "season_bat", "season_pit", "career_bat", "career_pit",
#              "award", "allstar", "hof", "ws", "position", "country",
#              "one_team", "war_season", "war_career"

_SEASON_BAT_WHERE = {
    ".300+ AVG SeasonBatting": ("Seasons .300+", "AB >= 1 AND (1.0 * H / AB) >= 0.300"),
    "30+ HR SeasonBatting": ("Seasons 30+ HR", "HR >= 30"),
    "40+ HR SeasonBatting": ("Seasons 40+ HR", "HR >= 40"),
    "10+ HR SeasonBatting": ("Seasons 10+ HR", "HR >= 10"),
    "100+ RBI SeasonBatting": ("Seasons 100+ RBI", "RBI >= 100"),
    "100+ Run SeasonBatting": ("Seasons 100+ R", "R >= 100"),
    "200+ Hits SeasonBatting": ("Seasons 200+ H", "H >= 200"),
    "40+ 2B SeasonBatting": ('Seasons 40+ 2B', '"2B" >= 40'),
    "30+ SB Season": ("Seasons 30+ SB", "SB >= 30"),
}

_SEASON_PIT_WHERE = {
    "200+ K SeasonPitching": ("Seasons 200+ K", "SO >= 200"),
    "10+ Win SeasonPitching": ("Seasons 10+ W", "W >= 10"),
    "20+ Win SeasonPitching": ("Seasons 20+ W", "W >= 20"),
    "30+ Save SeasonPitching": ("Seasons 30+ SV", "SV >= 30"),
    "40+ Save SeasonPitching": ("Seasons 40+ SV", "SV >= 40"),
    "<= 3.00 ERA Season": ("Seasons ≤3 ERA", "ERA <= 3.00 AND IPouts >= 162"),
}

_CAREER_BAT_COLS = {
    ".300+ AVG CareerBatting": ("Career AVG", "AVG"),
    "300+ HR CareerBatting": ("Career HR", "HR"),
    "500+ HR CareerBatting": ("Career HR", "HR"),
    "2000+ Hits CareerBatting": ("Career H", "H"),
    "3000+ Hits CareerBatting": ("Career H", "H"),
}

_CAREER_PIT_COLS = {
    "200+ Wins CareerPitching": ("Career W", "W"),
    "300+ Wins CareerPitching": ("Career W", "W"),
    "2000+ K CareerPitching": ("Career K", "SO"),
    "3000+ K CareerPitching": ("Career K", "SO"),
    "300+ Save CareerPitching": ("Career SV", "SV"),
    "<= 3.00 ERA CareerPitching": ("Career ERA", "ERA"),
}

_POSITION_COLS = {
    "Played Catchermin. 1 game": ("Games at C", "G_c"),
    "Played First Basemin. 1 game": ("Games at 1B", "G_1b"),
    "Played Second Basemin. 1 game": ("Games at 2B", "G_2b"),
    "Played Third Basemin. 1 game": ("Games at 3B", "G_3b"),
    "Played Shortstopmin. 1 game": ("Games at SS", "G_ss"),
    "Played Left Fieldmin. 1 game": ("Games at LF", "G_lf"),
    "Played Center Fieldmin. 1 game": ("Games at CF", "G_cf"),
    "Played Right Fieldmin. 1 game": ("Games at RF", "G_rf"),
    "Played Outfieldmin. 1 game": ("Games at OF", "G_of"),
    "Pitchedmin. 1 game": ("Games pitched", "G_p"),
    "Designated Hittermin. 1 game": ("Games at DH", "G_dh"),
}

_AWARD_IDS = {
    "Gold Glove": ("Gold Glove", "Gold Glove"),
    "Silver Slugger": ("Silver Slugger", "Silver Slugger"),
    "MVP": ("MVP years", "Most Valuable Player"),
    "Cy Young": ("Cy Young years", "Cy Young Award"),
    "Rookie of the Year": ("ROY year", "Rookie of the Year"),
}


def get_condition_detail(conn, player_ids, cond_type, code, label, franch_ids=None):
    """
    Get detail column(s) for a condition and set of players.

    Returns (column_name, {playerID: value}) or None if no special detail.
    For team conditions, returns (None, {playerID: {col: val, ...}}) — a dict of dicts.
    """
    if not player_ids:
        return None

    norm = _normalize(label)
    ph, pids = _placeholders(player_ids)

    # --- Teams: per-franchise breakdown ---
    if cond_type == "team":
        detail = _get_team_detail(conn, player_ids, code)
        return None, detail

    # --- Season batting ---
    if norm in _SEASON_BAT_WHERE:
        col_name, where = _SEASON_BAT_WHERE[norm]
        detail = _get_season_batting_count(conn, player_ids, where, franch_ids)
        return col_name, detail

    # --- Season pitching ---
    if norm in _SEASON_PIT_WHERE:
        col_name, where = _SEASON_PIT_WHERE[norm]
        detail = _get_season_pitching_count(conn, player_ids, where, franch_ids)
        return col_name, detail

    # --- 30+ HR / 30+ SB season ---
    if norm == "30+ HR /30+ SB SeasonBatting":
        rows = conn.execute(f"""
            SELECT playerID, COUNT(*) AS n FROM (
                SELECT playerID, yearID, SUM(HR) AS tot_hr, SUM(SB) AS tot_sb
                FROM Batting WHERE playerID IN ({ph})
                GROUP BY playerID, yearID HAVING tot_hr >= 30 AND tot_sb >= 30
            ) GROUP BY playerID
        """, pids).fetchall()
        return "30/30 seasons", {r[0]: r[1] for r in rows}

    # --- 6+ WAR season ---
    if norm == "6+ WAR Season":
        rows = conn.execute(f"""
            SELECT playerID, COUNT(*) AS n FROM (
                SELECT playerID, yearID, SUM(war) AS total FROM (
                    SELECT playerID, yearID, SUM(WAR) AS war FROM Batting
                    WHERE playerID IN ({ph}) GROUP BY playerID, yearID
                    UNION ALL
                    SELECT playerID, yearID, SUM(WAR) AS war FROM Pitching
                    WHERE playerID IN ({ph}) GROUP BY playerID, yearID
                ) GROUP BY playerID, yearID HAVING total >= 6.0
            ) GROUP BY playerID
        """, pids + pids).fetchall()
        return "6+ WAR seasons", {r[0]: r[1] for r in rows}

    # --- Career batting stat ---
    if norm in _CAREER_BAT_COLS:
        col_name, db_col = _CAREER_BAT_COLS[norm]
        rows = conn.execute(f"""
            SELECT playerID, {db_col} FROM Career_Batting
            WHERE playerID IN ({ph})
        """, pids).fetchall()
        return col_name, {r[0]: r[1] for r in rows}

    # --- Career pitching stat ---
    if norm in _CAREER_PIT_COLS:
        col_name, db_col = _CAREER_PIT_COLS[norm]
        rows = conn.execute(f"""
            SELECT playerID, {db_col} FROM Career_Pitching
            WHERE playerID IN ({ph})
        """, pids).fetchall()
        return col_name, {r[0]: r[1] for r in rows}

    # --- 40+ WAR career ---
    if norm == "40+ WAR Career":
        rows = conn.execute(f"""
            SELECT playerID, SUM(war) AS total FROM (
                SELECT playerID, WAR AS war FROM Career_Batting WHERE playerID IN ({ph})
                UNION ALL
                SELECT playerID, WAR AS war FROM Career_Pitching WHERE playerID IN ({ph})
            ) GROUP BY playerID
        """, pids + pids).fetchall()
        return "Career WAR", {r[0]: round(r[1], 1) if r[1] else 0 for r in rows}

    # --- Positions ---
    if norm in _POSITION_COLS:
        col_name, db_col = _POSITION_COLS[norm]
        rows = conn.execute(f"""
            SELECT playerID, SUM({db_col}) AS total
            FROM Appearances WHERE playerID IN ({ph})
            GROUP BY playerID
        """, pids).fetchall()
        return col_name, {r[0]: r[1] for r in rows}

    # --- Awards ---
    if norm in _AWARD_IDS:
        col_name, award_id = _AWARD_IDS[norm]
        rows = conn.execute(f"""
            SELECT playerID, GROUP_CONCAT(yearID, ', ') AS years
            FROM AwardsPlayers
            WHERE awardID = ? AND playerID IN ({ph})
            GROUP BY playerID
            ORDER BY playerID
        """, [award_id] + pids).fetchall()
        return col_name, {r[0]: r[1] for r in rows}

    # --- All-Star ---
    if norm == "All Star":
        rows = conn.execute(f"""
            SELECT playerID, COUNT(DISTINCT yearID) AS n
            FROM AllstarFull WHERE playerID IN ({ph})
            GROUP BY playerID
        """, pids).fetchall()
        return "All-Star selections", {r[0]: r[1] for r in rows}

    # --- Hall of Fame ---
    if norm == "Hall of Fame":
        rows = conn.execute(f"""
            SELECT playerID, MIN(yearid) AS year
            FROM HallOfFame WHERE inducted = 'Y' AND category = 'Player' AND playerID IN ({ph})
            GROUP BY playerID
        """, pids).fetchall()
        return "Inducted", {r[0]: r[1] for r in rows}

    # --- World Series Champ ---
    if norm == "World Series ChampWS Roster":
        rows = conn.execute(f"""
            SELECT sub.playerID, GROUP_CONCAT(sub.yearID, ', ') AS years FROM (
                SELECT DISTINCT ws.playerID, ws.yearID FROM (
                    SELECT bp.playerID, bp.teamID, bp.yearID FROM BattingPost bp WHERE bp.round = 'WS'
                    UNION
                    SELECT pp.playerID, pp.teamID, pp.yearID FROM PitchingPost pp WHERE pp.round = 'WS'
                ) ws
                JOIN Teams t ON ws.teamID = t.teamID AND ws.yearID = t.yearID
                WHERE t.WSWin = 'Y' AND ws.playerID IN ({ph})
                ORDER BY ws.yearID
            ) sub GROUP BY sub.playerID
        """, pids).fetchall()
        return "WS titles", {r[0]: r[1] for r in rows}

    # --- Born outside US ---
    if norm == "Born Outside US 50 States and DC":
        rows = conn.execute(f"""
            SELECT playerID, birthCountry FROM People
            WHERE playerID IN ({ph})
        """, pids).fetchall()
        return "Country", {r[0]: r[1] for r in rows}

    # --- Only one team ---
    if norm == "Only One Team":
        rows = conn.execute(f"""
            SELECT b.playerID, MAX(tf.franchName) AS team
            FROM Batting b
            JOIN Teams t ON b.teamID = t.teamID AND b.yearID = t.yearID
            JOIN TeamsFranchises tf ON t.franchID = tf.franchID
            WHERE b.playerID IN ({ph})
            GROUP BY b.playerID
        """, pids).fetchall()
        return "Team", {r[0]: r[1] for r in rows}

    # --- Played in MLB (no useful detail) ---
    if norm == "PlayedMajor Leagues":
        return None, {}

    return None, {}
