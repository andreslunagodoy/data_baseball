# app.py
import streamlit as st
import pandas as pd
import sqlite3

# --------------------------
# Database Connection
# --------------------------
@st.cache_resource
def get_connection(db_path="lahman.db"):
    """Connect to the SQLite database."""
    conn = sqlite3.connect(db_path)
    return conn

conn = get_connection()

st.title("Lahman Baseball Database Explorer")
st.write("Explore player batting stats dynamically from the Lahman Database.")

# --------------------------
# Load Dropdown Data
# --------------------------
@st.cache_data
def get_initial_dropdown_data():
    """Fetch lists for initial dropdowns (all teams and years)."""
    teams = pd.read_sql(
        "SELECT DISTINCT teamID FROM Batting WHERE yearID > 2013 ORDER BY teamID", conn
    )['teamID'].tolist()
    years = pd.read_sql(
        "SELECT DISTINCT yearID FROM Batting WHERE yearID > 2013 ORDER BY yearID", conn
    )['yearID'].tolist()
    return teams, years

teams, years = get_initial_dropdown_data()

# --------------------------
# Streamlit UI Elements
# --------------------------
# Year range slider
selected_years = st.slider(
    "Select year range",
    min_value=min(years),
    max_value=max(years),
    value=(min(years), max(years))
)

# Team dropdown
selected_team = st.selectbox("Select a team", ["All"] + teams)

# Player dropdown, filtered dynamically by team and year range
@st.cache_data
def get_filtered_players(team, year_start, year_end):
    filters = ["AB > 300"]
    if team != "All":
        filters.append(f"teamID = '{team}'")
    filters.append(f"yearID BETWEEN {year_start} AND {year_end}")
    where_clause = " AND ".join(filters)
    query = f"""
        SELECT DISTINCT playerID AS player
        FROM Batting
        WHERE {where_clause}
        ORDER BY player
    """
    return pd.read_sql(query, conn)['player'].tolist()

filtered_players = get_filtered_players(selected_team, selected_years[0], selected_years[1])
selected_player = st.selectbox("Select a player", filtered_players)

# Stat selector for the chart
stat_choice = st.selectbox(
    "Select a stat to visualize",
    ['hits', '2B', '3B', 'home_runs', 'RBI']
)

# --------------------------
# Dynamic SQL Query
# --------------------------
@st.cache_data
def get_player_stats(player, team, year_start, year_end):
    """Query the database for player stats based on user input."""
    query = f"""
    SELECT playerID,
           yearID,
           teamID,
           G AS games,
           AB AS at_bats,
           H AS hits,
           `2B`,
           `3B`,
           HR AS home_runs,
           RBI AS rbis
    FROM Batting
    WHERE playerID = '{player}'
      AND yearID BETWEEN {year_start} AND {year_end}
    """
    if team != "All":
        query += f" AND teamID = '{team}'"
    return pd.read_sql(query, conn)

stats_df = get_player_stats(selected_player, selected_team, selected_years[0], selected_years[1])

# --------------------------
# Display Table & Chart
# --------------------------
st.subheader("Player Stats Table")
st.dataframe(stats_df)

if not stats_df.empty:
    st.subheader(f"{stat_choice} over Years for {selected_player}")
    chart_df = stats_df.set_index('yearID')[[stat_choice]]
    st.bar_chart(chart_df)
else:
    st.info("No data found for selected filters.")