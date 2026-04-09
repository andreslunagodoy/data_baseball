# Baseball Data Project

A data engineering and analysis project built around the **Lahman Baseball Database** and **Baseball Reference WAR data**. The project covers database construction, SQL exploration, WAR integration, and interactive Streamlit apps.

Technologies: Python, pandas, SQLite, SQL, Streamlit, Jupyter Notebook, BeautifulSoup

---

## Project Structure

```
.
├── app_lahman.py                # Streamlit app – Lahman database explorer
├── app_ig.py                    # Streamlit app – Immaculate Grid solver
├── build_db_lahman.py           # Builds lahman.db from raw Lahman CSVs
├── build_db_ig.py               # Builds war_games.db (Lahman + WAR + awards)
├── build_tables_augmented.py    # Merges WAR into Lahman batting/pitching tables
├── build_tables_subset.py       # Filters Lahman data to 2000+ subset
├── scraper_bbref.py             # Scrapes WAR from Baseball Reference (2000–2025)
├── databases/
│   ├── lahman.db                # SQLite – basic Lahman tables
│   └── war_games.db             # SQLite – Lahman + WAR + awards + HoF
├── notebooks/
│   ├── exploring_lahman.ipynb   # SQL exploration on lahman.db
│   ├── queries.ipynb            # Advanced queries and Immaculate Grid logic
│   ├── test_db.ipynb            # Validation for war_games.db
│   └── test_augmented.ipynb     # Validation for augmented CSV files
├── raw_data/                    # Original Lahman CSV files (27 tables)
├── my_data/                     # Processed CSVs (filtered + WAR-augmented)
└── future_work/
```

---

## Data Pipeline

```
Baseball Reference (2000–2025)
    ↓  scraper_bbref.py
BBRef_Batting_WAR.csv, BBRef_Pitching_WAR.csv
    ↓  build_tables_subset.py (filters Lahman to 2000+)
    ↓  build_tables_augmented.py (merges WAR)
Batting_with_WAR.csv, Pitching_with_WAR.csv  →  my_data/
    ↓  build_db_ig.py
war_games.db  →  databases/

raw_data/ (Lahman CSVs)
    ↓  build_db_lahman.py
lahman.db  →  databases/
```

---

## Databases

### lahman.db
Basic Lahman tables: `People`, `Batting`, `Pitching`, `Teams`, `Salaries`.

### war_games.db
Extended database with WAR and metadata:
- `People`, `Teams`, `Salaries`
- `Batting_with_WAR`, `Pitching_with_WAR`
- `Appearances`, `AwardsPlayers`, `HallOfFame`

Foreign keys enforced. Data covers 2000–2025.

---

## Streamlit Apps

### Lahman Explorer (`app_lahman.py`)

```bash
streamlit run app_lahman.py
```

- Filter by year range, team, and player
- View batting stats table and bar charts

### Immaculate Grid Solver (`app_ig.py`)

```bash
streamlit run app_ig.py
```

- Select 3 row franchises and 3 column franchises
- Solves the 3x3 grid: finds players who played for both franchises
- Includes batters and pitchers
- Uses backtracking with highest career WAR preference

---

## Notebooks

- **exploring_lahman.ipynb** – SQL practice on lahman.db: SELECT, WHERE, JOIN, GROUP BY, aggregates, batting average leaders, HR trends, team win %
- **queries.ipynb** – Advanced analysis on war_games.db: top WAR seasons, franchise stats, Immaculate Grid solver logic
- **test_db.ipynb** – Validates war_games.db: row counts, WAR coverage, referential integrity, spot checks
- **test_augmented.ipynb** – Validates augmented CSVs: WAR availability, multi-team players, spot checks

---

## Running the Project

### 1. Build the Lahman database

```bash
python build_db_lahman.py
```

### 2. Scrape WAR data (optional – CSVs already in my_data/)

```bash
python scraper_bbref.py
```

### 3. Build augmented tables and war_games.db

```bash
python build_tables_subset.py
python build_tables_augmented.py
python build_db_ig.py
```

### 4. Launch an app

```bash
streamlit run app_lahman.py
streamlit run app_ig.py
```

---

## Author

Andres Luna

https://github.com/andreslunagodoy
https://www.linkedin.com/in/andres-luna-06a31b101/
