# Baseball Data Project

A data engineering and analysis project built around the **Lahman Baseball Database** and **Baseball Reference WAR data**. Includes database construction, WAR integration, an interactive Streamlit app, and an Immaculate Grid scraper/solver.

Technologies: Python, pandas, SQLite, SQL, Streamlit, Jupyter Notebook, BeautifulSoup

---

## Project Structure

```
.
├── app_ig.py                    # Streamlit app – MLB Players Explorer
├── grid_resolver.py             # Maps Immaculate Grid categories to SQL queries
├── build_db_ig.py               # Builds war_games.db from raw data + WAR
├── databases/
│   └── war_games.db             # SQLite – all-time stats + WAR + career aggregates
├── my_data/                     # Scraped data outputs
│   ├── BBRef_Batting_WAR.csv    # WAR per player-season (batting)
│   ├── BBRef_Pitching_WAR.csv   # WAR per player-season (pitching)
│   └── immaculate_grids.csv     # 1,102 scraped grid definitions
├── raw_data/                    # Original Lahman CSV files (27 tables)
├── scrapers/
│   ├── scraper_bbref.py         # Scrapes WAR from Baseball Reference (resumable)
│   ├── scraper_ig_grids.py      # Scrapes Immaculate Grid puzzles
│   └── analysis_ig_grids.ipynb  # Analysis of grid patterns and distributions
└── war_augmented/               # Augmented CSVs for pandas/notebook work
    ├── build_tables_augmented.py
    ├── Batting_with_WAR.csv
    ├── Pitching_with_WAR.csv
    ├── queries.ipynb            # Advanced queries and Immaculate Grid solver logic
    ├── test_db.ipynb            # Validates war_games.db
    └── test_augmented.ipynb     # Validates augmented CSVs
```

---

## Data Pipeline

```
Baseball Reference (1871–2025)
    ↓  scrapers/scraper_bbref.py (resumable, with rate-limit retry)
BBRef WAR CSVs  →  my_data/

Immaculate Grid website
    ↓  scrapers/scraper_ig_grids.py
immaculate_grids.csv  →  my_data/

raw_data/ (Lahman CSVs)  +  my_data/ (WAR CSVs)
    ↓  build_db_ig.py (filters to AL/NL, merges WAR, creates career aggregates)
war_games.db  →  databases/

raw_data/ + my_data/
    ↓  war_augmented/build_tables_augmented.py
Batting_with_WAR.csv, Pitching_with_WAR.csv  →  war_augmented/
```

---

## Database: war_games.db

Full database covering all MLB history (1871–present), AL and NL only:

- `People`, `Teams`, `TeamsFranchises`, `Salaries`
- `Batting`, `Pitching` (with WAR merged, 100% coverage)
- `Appearances`, `AwardsPlayers`, `HallOfFame`
- `AllstarFull`, `BattingPost`, `PitchingPost`
- `Career_Batting`, `Career_Pitching` (aggregated career stats with AVG, OBP, SLG, OPS, ERA, WHIP)

---

## Streamlit App

```bash
streamlit run app_ig.py
```

Four tabs:

- **Player Finder** – Combine up to 5 conditions (teams, stat milestones, awards, positions) and find players who satisfy all of them. Team-only queries show separate batter and pitcher tables with per-team stats. Results are sorted contextually: by AB/IP for team queries, by stat value for stat queries, by count for milestones.
- **Immaculate Grid** – Solve any of the 1,102 scraped grids or build a custom grid from ~50 categories. Uses backtracking with highest career WAR preference. Team + season-stat pairings enforce same-season constraints.
- **Player Stats** – Search for any player, view season-by-season batting and pitching lines (AVG, OBP, SLG, OPS, ERA, WHIP), filter by year range, with career totals.
- **About** – Data sources and methodology.

### Grid Resolver (`grid_resolver.py`)

Maps ~50 Immaculate Grid stat categories to SQL queries. Two modes:
- **Standalone**: all players matching a category.
- **Team-constrained**: year-bound categories (season stats, positions, awards, All-Star) require the player to have achieved it while on a specific franchise.

Unsupported categories (require external data): Threw a No-Hitter, First Round Draft Pick, Played in Major Negro Leagues.

---

## Running the Project

### 1. Scrape data (optional – CSVs already in my_data/)

```bash
python scrapers/scraper_bbref.py              # all years, resumes from existing data
python scrapers/scraper_bbref.py 1950 1999    # specific year range
python scrapers/scraper_ig_grids.py           # immaculate grid definitions
```

### 2. Build the database

```bash
python build_db_ig.py
```

### 3. Build augmented CSVs (optional – for pandas/notebook work)

```bash
cd war_augmented && python build_tables_augmented.py
```

### 4. Launch the app

```bash
streamlit run app_ig.py
```

---

## Author

Andres Luna

https://github.com/andreslunagodoy
https://www.linkedin.com/in/andres-luna-06a31b101/
