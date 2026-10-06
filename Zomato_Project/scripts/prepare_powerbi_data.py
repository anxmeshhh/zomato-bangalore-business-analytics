"""
Prepare enriched data and theme for Power BI Dashboard
"""
import os
import json
import pandas as pd
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN_CSV = os.path.join(os.path.dirname(BASE), "zomato_clean.csv")
POWERBI_DIR = os.path.join(BASE, "powerbi")
os.makedirs(POWERBI_DIR, exist_ok=True)

df = pd.read_csv(CLEAN_CSV)
print(f"Loaded {len(df):,} cleaned rows.")

# 1. Rating Bracket
rating_bins = [0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
rating_labels = ['< 2.5', '2.5 - 3.0', '3.0 - 3.5', '3.5 - 4.0', '4.0 - 4.5', '4.5 - 5.0']
df['Rating_Bracket'] = pd.cut(df['rate'], bins=rating_bins, labels=rating_labels, include_lowest=True)
rating_sort_map = {label: i+1 for i, label in enumerate(rating_labels)}
df['Rating_Bracket_Sort'] = df['Rating_Bracket'].map(rating_sort_map)

# 2. Vote Bracket
vote_bins = [0, 50, 150, 500, 1000, 5000, 50000]
vote_labels = ['<50 (Low)', '50-150', '150-500 (Moderate)', '500-1k (High)', '1k-5k (Very High)', '5k+ (Mega)']
df['Vote_Bracket'] = pd.cut(df['votes'], bins=vote_bins, labels=vote_labels, include_lowest=True)
vote_sort_map = {label: i+1 for i, label in enumerate(vote_labels)}
df['Vote_Bracket_Sort'] = df['Vote_Bracket'].map(vote_sort_map)

# 3. Cost Bracket
cost_bins = [0, 300, 600, 1000, 2000, 10000]
cost_labels = ['Budget (<₹300)', 'Mid-Low (₹300-₹600)', 'Mid-High (₹600-₹1k)', 'Premium (₹1k-₹2k)', 'Fine Dining (>₹2k)']
df['Cost_Bracket'] = pd.cut(df['approx_cost'], bins=cost_bins, labels=cost_labels, include_lowest=True)
cost_sort_map = {label: i+1 for i, label in enumerate(cost_labels)}
df['Cost_Bracket_Sort'] = df['Cost_Bracket'].map(cost_sort_map)

# 4. Top Rated Flag
df['Performance_Tier'] = np.where(df['rate'] >= 4.0, 'Top Rated (≥4.0)', 'Standard (<4.0)')

# Save enriched CSV
out_csv = os.path.join(POWERBI_DIR, "zomato_powerbi.csv")
df.to_csv(out_csv, index=False)
root_csv = os.path.join(os.path.dirname(BASE), "zomato_powerbi.csv")
df.to_csv(root_csv, index=False)
print(f"Saved enriched Power BI dataset to: {out_csv} and {root_csv}")

# 5. Create Power BI Theme JSON
theme = {
    "name": "ZomatoAnalyticsTheme",
    "dataColors": [
        "#E23744",  # Zomato Crimson
        "#1C2938",  # Espresso / Navy
        "#008080",  # Teal Accent
        "#FFAA00",  # Amber Gold
        "#43A047",  # Emerald Green
        "#5E35B1",  # Deep Purple
        "#00ACC1",  # Cyan
        "#FB8C00"   # Orange
    ],
    "background": "#F8F9FA",
    "foreground": "#1C2938",
    "tableAccent": "#E23744",
    "visualStyles": {
        "*": {
            "*": {
                "background": [{"color": {"solid": {"color": "#FFFFFF"}}, "transparency": 0}],
                "border": [{"show": True, "color": {"solid": {"color": "#E0E0E0"}}, "radius": 6}],
                "dropShadow": [{"show": True, "color": {"solid": {"color": "#000000"}}, "transparency": 95, "position": "Outer"}],
                "title": [{"fontFamily": "Segoe UI", "fontSize": 12, "color": {"solid": {"color": "#1C2938"}}, "bold": True}]
            }
        },
        "card": {
            "*": {
                "labels": [{"color": {"solid": {"color": "#E23744"}}, "fontSize": 24, "fontFamily": "Segoe UI Semibold"}],
                "categoryLabels": [{"color": {"solid": {"color": "#555555"}}, "fontSize": 10, "fontFamily": "Segoe UI"}]
            }
        }
    }
}

theme_path = os.path.join(POWERBI_DIR, "zomato_theme.json")
with open(theme_path, "w", encoding="utf-8") as f:
    json.dump(theme, f, indent=2)
print(f"Saved custom Power BI theme to: {theme_path}")

# 6. Create DAX measures file
dax_content = """// ==============================================================================
// ZOMATO BANGALORE - POWER BI DAX MEASURES LIBRARY
// ==============================================================================

// 1. Total Restaurants
Total Restaurants = COUNTROWS(zomato_powerbi)

// 2. Average Rating
Average Rating = AVERAGE(zomato_powerbi[rate])

// 3. Average Cost for Two
Average Cost for Two = AVERAGE(zomato_powerbi[approx_cost])

// 4. Total Votes (Customer Engagement)
Total Votes = SUM(zomato_powerbi[votes])

// 5. Average Votes Per Outlet
Average Votes = AVERAGE(zomato_powerbi[votes])

// 6. Online Ordering Share %
Online Order Share % = 
DIVIDE(
    CALCULATE(COUNTROWS(zomato_powerbi), zomato_powerbi[online_order] = "Yes"),
    COUNTROWS(zomato_powerbi),
    0
)

// 7. Table Booking Share %
Table Booking Share % = 
DIVIDE(
    CALCULATE(COUNTROWS(zomato_powerbi), zomato_powerbi[book_table] = "Yes"),
    COUNTROWS(zomato_powerbi),
    0
)

// 8. Top Rated Outlets Count (Rating >= 4.0)
Top Rated Outlets = 
CALCULATE(
    COUNTROWS(zomato_powerbi),
    zomato_powerbi[rate] >= 4.0
)

// 9. Top Rated Outlets Share %
Top Rated Share % = 
DIVIDE([Top Rated Outlets], [Total Restaurants], 0)

// 10. Table Booking Rating Lift (Rating difference)
Table Booking Lift = 
VAR WithBooking = CALCULATE(AVERAGE(zomato_powerbi[rate]), zomato_powerbi[book_table] = "Yes")
VAR WithoutBooking = CALCULATE(AVERAGE(zomato_powerbi[rate]), zomato_powerbi[book_table] = "No")
RETURN
WithBooking - WithoutBooking
"""

dax_path = os.path.join(POWERBI_DIR, "dax_measures.dax")
with open(dax_path, "w", encoding="utf-8") as f:
    f.write(dax_content)
print(f"Saved DAX measures to: {dax_path}")
