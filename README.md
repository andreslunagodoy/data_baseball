# Lahman Baseball Database Explorer

This project is a small data engineering and analysis workflow built around the **Lahman Baseball Database**. The goal is to practice working with relational databases, SQL queries, and building a simple interactive data application.

The project uses:

- **SQLite** for the database
- **Python + Jupyter Notebook** for data loading and SQL exploration
- **Streamlit** for a lightweight web interface

The dataset comes from the Lahman baseball database, which contains historical Major League Baseball statistics.

---

# Project Structure

```
.
├── app.py
├── bbref.py
├── bbref2.py
├── project.ipynb
├── lahman.db
├── BBRef_Batting_1900_2025.csv
├── BBRef_Pitching_1900_2025.csv
├── data/
│   ├── People.csv
│   ├── Batting.csv
│   ├── Pitching.csv
│   ├── Teams.csv
│   ├── Salaries.csv
│   └── ...
```

Key files:

- **project.ipynb** – Jupyter notebook used to build the database and explore SQL queries.
- **lahman.db** – SQLite database created from the Lahman CSV files.
- **app.py** – Streamlit application for interactive exploration of player statistics.
- **data/** – Raw Lahman CSV files used to populate the database.

---

# Stage 1 – Database Construction

The notebook loads CSV files from the Lahman dataset and constructs a relational SQLite database.

Tables currently used in the project:

- `People`
- `Batting`
- `Pitching`
- `Teams`
- `Salaries`

### Steps performed

1. Load CSV files using **pandas**
2. Inspect column names and data types
3. Create a SQLite database (`lahman.db`)
4. Define primary keys and foreign keys
5. Create SQL tables
6. Insert data from the DataFrames
7. Perform sanity checks to verify row counts

Example checks:

- Compare SQLite table lengths with DataFrame lengths
- Inspect schemas using:

```sql
PRAGMA table_info(Batting);
```

---

# Stage 2 – SQL Exploration (Jupyter)

The notebook is used to practice SQL queries on the baseball data.

Topics covered:

### Basic Queries

- `SELECT`
- `WHERE`
- `ORDER BY`
- `LIMIT`

Example:

```sql
SELECT playerID, yearID, HR
FROM Batting
ORDER BY HR DESC
LIMIT 10;
```

### Aggregation

- `GROUP BY`
- `SUM`
- `AVG`
- `HAVING`

Example:

```sql
SELECT playerID,
       SUM(HR) AS career_hr
FROM Batting
GROUP BY playerID
ORDER BY career_hr DESC
LIMIT 10;
```

### Joins

Example joining player names with batting data:

```sql
SELECT p.nameFirst,
       p.nameLast,
       SUM(b.HR) AS career_hr
FROM Batting b
JOIN People p
    ON b.playerID = p.playerID
GROUP BY b.playerID
ORDER BY career_hr DESC
LIMIT 10;
```

### Exploratory Questions

Some exploratory analyses included:

- Career batting average leaders
- Home run totals by season
- Best teams by winning percentage
- Stolen base trends over time

Reusable helper function in the notebook:

```python
def run_query(query, params=None):
    return pd.read_sql_query(query, conn, params=params)
```

---

# Stage 3 – Streamlit Web App

A simple interactive application is built using **Streamlit**.

The app allows users to:

- Select a **year range**
- Filter by **team**
- Select a **player**
- Choose a statistic to visualize

The application dynamically generates SQL queries based on user input.

Example query structure:

```sql
SELECT playerID,
       yearID,
       teamID,
       G AS games,
       AB AS at_bats,
       H AS hits,
       2B,
       3B,
       HR AS home_runs,
       RBI AS rbis
FROM Batting
WHERE playerID = ?
AND yearID BETWEEN ? AND ?
```

The results are displayed as:

- A **data table**
- A **bar chart of selected statistics over time**

---

# Running the Project

## 1. Create the Database

Run the Jupyter notebook:

```
project.ipynb
```

This will generate:

```
lahman.db
```

---

## 2. Launch the Streamlit App

From the project directory:

```bash
streamlit run app.py
```

Then open the browser interface that Streamlit launches.

---

# Example App Features

The app allows users to dynamically explore:

- Player seasonal statistics
- Team filters
- Time ranges
- Individual stat visualization

Example chart options:

- Hits
- Doubles
- Triples
- Home Runs
- RBIs

---

# Possible Future Improvements

Potential extensions for the project:

- Add pitching statistics
- Add team-level analysis
- Add player name lookup instead of playerID
- Include additional Lahman tables (Fielding, Awards, AllStar)
- Add advanced metrics (OPS, SLG, OBP)
- Improve charts with **Altair** or **Plotly**

---

# Technologies Used

- Python
- pandas
- SQLite
- SQL
- Streamlit
- Jupyter Notebook

# Author
Andres Luna

https://github.com/andreslunagodoy
https://www.linkedin.com/in/andres-luna-06a31b101/

SQL Learning Project

Focus: **Basic SQL queries and deployment**