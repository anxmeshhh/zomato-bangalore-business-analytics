# BI&A Final Project — Zomato Bangalore Restaurants

**Dataset:** Kaggle `himanshupoddar/zomato-bangalore-restaurants` (`zomato.csv`, 51,717 rows x 17 cols)
**Final deliverable:** Power BI report (`.pbix`) styled after the Brew House reference dashboard.

---

## Metric mapping (reference dashboard -> Zomato reality)

The reference is a transactional cafe dashboard. Zomato is a restaurant *catalogue* — no orders,
no timestamps, no revenue. Same layout and visual language, remapped metrics:

| Reference tile        | Zomato equivalent                                  |
|-----------------------|----------------------------------------------------|
| Daily Revenue         | Total Restaurants                                  |
| Orders                | Total Votes (engagement proxy)                     |
| Avg. Order Value      | Avg. Cost for Two                                  |
| Repeat Customers      | % Online Ordering enabled                          |
| Table Turnover        | % Table Booking enabled                            |
| Orders Per Hour       | Rating distribution curve (restaurants per rating) |
| Peak Hours            | Top locations by restaurant density                |
| Best-Selling Item     | Top cuisine (by restaurant count + avg rating)     |
| Top-Selling Drinks    | Top cuisines                                       |
| Top-Selling Food      | Top dishes liked (`dish_liked` exploded)           |
| Low Performers        | Lowest-rated restaurant types                      |
| Inventory Alerts      | Data-quality alerts (nulls / unrated / no-cost)    |
| Staff Coverage        | Restaurant types per service category              |
| Loyalty Program       | High-vote ("loyal following") restaurant share     |
| Campaign Performance  | Online-order vs dine-in performance comparison     |
| Today's Top Insights  | Auto-generated insight cards from EDA              |

---

## The 7 experiments

### Experiment 1 — Data Loading & Ingestion
Load raw `zomato.csv`, profile structure, build a data dictionary.
- Shape, dtypes, memory footprint, null counts, cardinality per column
- Identify problem columns (`rate`, `approx_cost(for two people)`, list-shaped columns)
- Output: `data_dictionary.csv`, `exp1_profile.txt`, `staging.parquet` (heavy text columns dropped)

### Experiment 2 — Data Cleaning
- Drop `url`, `phone`, `reviews_list`, `menu_item` (noise / not analysable in Power BI)
- Deduplicate (same restaurant listed once per service category)
- `rate`: `"4.1/5"` -> `4.1`; `"NEW"`, `"-"` -> null
- `approx_cost(for two people)`: `"1,200"` -> `1200` (numeric)
- `online_order` / `book_table`: Yes/No -> boolean
- Trim/normalise text, standardise column names
- Output: `zomato_clean.csv`, `exp2_cleaning_log.txt`

### Experiment 3 — Transformation & Feature Engineering
- Explode `cuisines`, `rest_type`, `dish_liked` into bridge tables (many-to-many)
- Derive: `price_band`, `rating_band`, `votes_band`, `cuisine_count`, `is_premium`, `popularity_score`
- Build a **star schema**: `FactRestaurant` + `DimLocation`, `DimCuisine`, `DimRestType`, `DimCategory`, `DimPriceBand`
- Output: one CSV per table in `data/processed/`

### Experiment 4 — SQL / Database Layer
- DDL to create the star schema in SQL Server (`ZomatoDB`)
- Bulk load the processed CSVs
- 12 analytical queries (top locations, cost vs rating, cuisine leaderboards, online-order lift)
- Output: `sql/01_schema.sql`, `sql/02_load.sql`, `sql/03_analysis.sql`

### Experiment 5 — Exploratory Data Analysis
- Univariate: rating, cost, votes distributions
- Bivariate: cost vs rating, votes vs rating, online-order impact on rating
- Geographic: location concentration, cost by area
- Correlation matrix + statistical tests
- Output: charts in `outputs/figures/`, findings in `exp5_eda_findings.md`

### Experiment 6 — Data Modelling & DAX in Power BI
- Import star schema, set relationships and cardinality, hide surrogate keys
- ~25 DAX measures driving every tile in the mapping table above
- Output: `powerbi/dax_measures.md` (copy-paste ready), `powerbi/model_setup.md`

### Experiment 7 — Dashboard Design & Insights
- 4 pages: **Overview** (the hero screen), **Locations**, **Cuisine Performance**, **Insights**
- Custom Power BI theme JSON matching the cream/espresso palette of the reference
- Written insight narrative + recommendations
- Output: `powerbi/zomato_theme.json`, `powerbi/build_guide.md`, final `.pbix`
