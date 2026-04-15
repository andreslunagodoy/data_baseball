# Baseball Data Project

A data engineering and analysis project built around the **Lahman Baseball Database** and **Baseball Reference WAR data**. Includes database construction, SQL exploration, WAR integration, interactive Streamlit apps, and an Immaculate Grid scraper/solver.

Technologies: Python, pandas, SQLite, SQL, Streamlit, Jupyter Notebook, BeautifulSoup

---

## Project Structure

```
.
├── app_lahman.py                # Streamlit app – Lahman database explorer
├── app_ig.py                    # Streamlit app – Baseball Explorer (4 tabs)
├── grid_resolver.py             # Maps Immaculate Grid categories to SQL queries
├── build_db_lahman.py           # Builds lahman.db from raw Lahman CSVs
├── build_db_ig.py               # Builds war_games.db (all-time Lahman + WAR + career aggregates)
├── build_tables_augmented.py    # Merges WAR into Lahman batting/pitching tables
├── build_tables_subset.py       # Filters Lahman data to 2000+ subset
├── scraper_bbref.py             # Scrapes WAR from Baseball Reference (resumable)
├── databases/
│   ├── lahman.db                # SQLite – basic Lahman tables
│   └── war_games.db             # SQLite – all-time stats + WAR + career aggregates
├── scraper_ig/
│   ├── scraper_ig_grids.py      # Scrapes Immaculate Grid puzzles from the website
│   ├── immaculate_grids.csv     # 1,102 scraped grid definitions
│   └── analysis_ig_grids.ipynb  # Analysis of grid patterns and distributions
├── notebooks/
│   ├── exploring_lahman.ipynb   # SQL exploration on lahman.db
│   ├── queries.ipynb            # Advanced queries and Immaculate Grid logic
│   ├── test_db.ipynb            # Validation for war_games.db
│   └── test_augmented.ipynb     # Validation for augmented CSV files
├── raw_data/                    # Original Lahman CSV files (27 tables)
├── my_data/                     # Processed CSVs (WAR data + augmented tables)
└── future_work/
```

---

## Data Pipeline

```
Baseball Reference (all years)
    ↓  scraper_bbref.py (resumable, with rate-limit retry)
BBRef_Batting_WAR.csv, BBRef_Pitching_WAR.csv  →  my_data/

raw_data/ (Lahman CSVs, all years)  +  WAR CSVs
    ↓  build_db_ig.py (merges WAR, creates career aggregates)
war_games.db  →  databases/

Immaculate Grid website
    ↓  scraper_ig/scraper_ig_grids.py
immaculate_grids.csv  →  scraper_ig/
```

---

## Databases

### lahman.db
Basic Lahman tables: `People`, `Batting`, `Pitching`, `Teams`, `Salaries`.

### war_games.db
Full database covering all MLB history (1871–present):
- `People`, `Teams`, `TeamsFranchises`, `Salaries`
- `Batting`, `Pitching` (with WAR merged where available)
- `Appearances`, `AwardsPlayers`, `HallOfFame`
- `AllstarFull`, `BattingPost`, `PitchingPost`
- `Career_Batting`, `Career_Pitching` (aggregated career stats with AVG, OBP, SLG, OPS, ERA, WHIP)

---

## Streamlit Apps

### Lahman Explorer (`app_lahman.py`)

```bash
streamlit run app_lahman.py
```

- Filter by year range, team, and player
- View batting stats table and bar charts

### Baseball Explorer (`app_ig.py`)

```bash
streamlit run app_ig.py
```

Four tabs:

- **Home** – Overview of the app and data sources.
- **Player Lookup** – Search for any player, view season-by-season batting and pitching stats (AVG, OBP, SLG, OPS, ERA, WHIP), filter by year range.
- **Condition Explorer** – Combine up to 5 conditions (teams, awards, stat thresholds, positions) and find players who satisfy all of them. Supports team-constrained mode (Immaculate Grid rules: season stats must be achieved while on the selected team) and standalone mode.
- **Immaculate Grid** – Solve any of the 1,102 scraped grids or build a custom grid from ~50 categories. Uses backtracking with highest career WAR preference.

### Grid Resolver (`grid_resolver.py`)

Maps each of the ~54 Immaculate Grid stat categories to SQL queries. Supports two modes:
- **Standalone**: returns all players matching a category.
- **Team-constrained**: for year-bound categories (season stats, positions, awards, All-Star), only returns players who achieved it while on a specific franchise.

Currently unsupported categories (require external data): Threw a No-Hitter, First Round Draft Pick, Played in Major Negro Leagues.

---

## Notebooks

- **exploring_lahman.ipynb** – SQL practice on lahman.db
- **queries.ipynb** – Advanced analysis on war_games.db, Immaculate Grid solver logic
- **test_db.ipynb** – Validates war_games.db: row counts, WAR coverage, referential integrity
- **test_augmented.ipynb** – Validates augmented CSVs
- **scraper_ig/analysis_ig_grids.ipynb** – Analysis of Immaculate Grid patterns: team frequencies, stat category distributions, grid compositions

---

## Running the Project

### 1. Scrape WAR data (optional – CSVs already in my_data/)

```bash
python scraper_bbref.py              # all years, resumes from existing data
python scraper_bbref.py 1950 1999    # specific year range
```

### 2. Build war_games.db

```bash
python build_db_ig.py
```

### 3. Launch the app

```bash
streamlit run app_ig.py
```

---

## Author

Andres Luna

https://github.com/andreslunagodoy
https://www.linkedin.com/in/andres-luna-06a31b101/
