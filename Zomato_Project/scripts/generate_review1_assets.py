"""
Zomato Bangalore Restaurants - Review 1 Master Analysis Script
Covers: Data Understanding -> Cleaning -> EDA -> 6 Visualizations -> Modelling -> Model Evaluation -> Feature Importance
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer

# Set aesthetic styling
sns.set_theme(style="whitegrid", font_scale=1.1)
plt.rcParams['font.sans-serif'] = 'Arial'
plt.rcParams['axes.edgecolor'] = '#cccccc'
plt.rcParams['axes.linewidth'] = 0.8

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FIG_DIR = os.path.join(BASE_DIR, "outputs", "figures")
OUTPUT_REP_DIR = os.path.join(BASE_DIR, "outputs", "reports")
os.makedirs(OUTPUT_FIG_DIR, exist_ok=True)
os.makedirs(OUTPUT_REP_DIR, exist_ok=True)

# Path to raw data
CSV_PATH = os.path.join(os.path.dirname(BASE_DIR), "zomato.csv")
if not os.path.exists(CSV_PATH):
    CSV_PATH = "zomato.csv"

print("================================================================================")
print("STEP 1: DATASET UNDERSTANDING")
print("================================================================================")
df_raw = pd.read_csv(CSV_PATH)
print(f"Dataset Loaded Successfully!")
print(f"Number of Rows: {df_raw.shape[0]:,}")
print(f"Number of Columns: {df_raw.shape[1]}")
print(f"Columns: {list(df_raw.columns)}")
print(f"Exact Duplicate Rows across all 17 cols: {df_raw.duplicated().sum()}")
print("\nMissing values per column:")
print(df_raw.isnull().sum())

num_cols = df_raw.select_dtypes(include=[np.number]).columns.tolist()
cat_cols = df_raw.select_dtypes(include=['object']).columns.tolist()
print(f"\nRaw Numerical Columns: {num_cols}")
print(f"Raw Categorical Columns: {cat_cols}")

print("\n================================================================================")
print("STEP 2: DATA CLEANING & PREPROCESSING")
print("================================================================================")
# 1. Drop irrelevant columns
drop_cols = ['url', 'phone', 'reviews_list', 'menu_item', 'address']
df_clean = df_raw.drop(columns=[c for c in drop_cols if c in df_raw.columns])
print(f"Dropped non-analytical text/metadata columns: {drop_cols}")
print(f"Shape after dropping non-essential columns: {df_clean.shape}")

# 2. Deduplicate
before_dedup = len(df_clean)
df_clean = df_clean.drop_duplicates()
after_dedup = len(df_clean)
print(f"Removed {before_dedup - after_dedup} exact duplicate rows. Remaining: {after_dedup:,}")

# 3. Clean 'rate'
def parse_rate(val):
    if pd.isna(val) or str(val).strip() in ['NEW', '-', '']:
        return np.nan
    try:
        return float(str(val).split('/')[0].strip())
    except:
        return np.nan

df_clean['rate'] = df_clean['rate'].apply(parse_rate)
unrated_count = df_clean['rate'].isna().sum()
print(f"Cleaned 'rate': converted 'X/5' strings to float. Handled 'NEW' and '-' as NaN ({unrated_count:,} unrated rows).")

# 4. Clean 'approx_cost(for two people)'
def parse_cost(val):
    if pd.isna(val):
        return np.nan
    try:
        return float(str(val).replace(',', '').strip())
    except:
        return np.nan

cost_col = 'approx_cost(for two people)'
df_clean['approx_cost'] = df_clean[cost_col].apply(parse_cost)
df_clean.drop(columns=[cost_col], inplace=True)
print("Cleaned 'approx_cost': stripped commas (e.g. '1,200' -> 1200) and converted to numeric float.")

# 5. Clean votes
df_clean['votes'] = pd.to_numeric(df_clean['votes'], errors='coerce').fillna(0).astype(int)

# 6. Encode binary features
df_clean['online_order_encoded'] = df_clean['online_order'].map({'Yes': 1, 'No': 0})
df_clean['book_table_encoded'] = df_clean['book_table'].map({'Yes': 1, 'No': 0})
print("Encoded 'online_order' and 'book_table' to binary (1 = Yes, 0 = No).")

# 7. Drop rows missing target variable 'rate' and 'approx_cost' for analytics & modelling
df_valid = df_clean.dropna(subset=['rate', 'approx_cost', 'rest_type', 'cuisines', 'location']).copy()
print(f"Valid cleaned records ready for analysis & modelling: {len(df_valid):,} rows (from {len(df_raw):,} raw).")

# Extract primary cuisine and primary rest_type
df_valid['primary_rest_type'] = df_valid['rest_type'].apply(lambda x: str(x).split(',')[0].strip())
df_valid['primary_cuisine'] = df_valid['cuisines'].apply(lambda x: str(x).split(',')[0].strip())

print("\n================================================================================")
print("STEP 3: EXPLORATORY DATA ANALYSIS (EDA)")
print("================================================================================")
rate_mean = df_valid['rate'].mean()
rate_median = df_valid['rate'].median()
rate_min = df_valid['rate'].min()
rate_max = df_valid['rate'].max()
rate_std = df_valid['rate'].std()

cost_mean = df_valid['approx_cost'].mean()
cost_median = df_valid['approx_cost'].median()
cost_min = df_valid['approx_cost'].min()
cost_max = df_valid['approx_cost'].max()

votes_mean = df_valid['votes'].mean()
votes_median = df_valid['votes'].median()
votes_min = df_valid['votes'].min()
votes_max = df_valid['votes'].max()

print("Key Descriptive Statistics:")
print(f"Rating      : Mean = {rate_mean:.2f}, Median = {rate_median:.2f}, Min = {rate_min:.1f}, Max = {rate_max:.1f}, Std = {rate_std:.2f}")
print(f"Cost for 2  : Mean = Rs.{cost_mean:.2f}, Median = Rs.{cost_median:.0f}, Min = Rs.{cost_min:.0f}, Max = Rs.{cost_max:.0f}")
print(f"Votes       : Mean = {votes_mean:.1f}, Median = {votes_median:.0f}, Min = {votes_min}, Max = {votes_max:,}")

# Online ordering stats
online_rate = df_valid.groupby('online_order')['rate'].agg(['count', 'mean', 'median', 'std'])
print("\nOnline Ordering vs Rating:")
print(online_rate)

# Table booking stats
book_rate = df_valid.groupby('book_table')['rate'].agg(['count', 'mean', 'median', 'std'])
print("\nTable Booking vs Rating:")
print(book_rate)

# Correlations
corr_votes = df_valid['rate'].corr(df_valid['votes'])
corr_cost = df_valid['rate'].corr(df_valid['approx_cost'])
corr_online = df_valid['rate'].corr(df_valid['online_order_encoded'])
corr_book = df_valid['rate'].corr(df_valid['book_table_encoded'])
print(f"\nCorrelations with Rating:")
print(f"  Votes            : {corr_votes:+.4f} (Strong positive)")
print(f"  Table Booking    : {corr_book:+.4f} (Strong positive)")
print(f"  Approx Cost      : {corr_cost:+.4f} (Moderate positive)")
print(f"  Online Ordering  : {corr_online:+.4f} (Slight positive)")

# Top locations
top_locs = df_valid.groupby('location').agg(
    count=('rate', 'count'),
    mean_rate=('rate', 'mean'),
    median_cost=('approx_cost', 'median'),
    mean_votes=('votes', 'mean')
).sort_values(by='count', ascending=False)
print("\nTop 10 Locations by Restaurant Count:")
print(top_locs.head(10))

# Top Restaurant Types
top_types = df_valid.groupby('primary_rest_type').agg(
    count=('rate', 'count'),
    mean_rate=('rate', 'mean')
).sort_values(by='count', ascending=False)
print("\nTop 10 Restaurant Types:")
print(top_types.head(10))

# Top Cuisines
top_cuisines = df_valid.groupby('primary_cuisine').agg(
    count=('rate', 'count'),
    mean_rate=('rate', 'mean')
).sort_values(by='count', ascending=False)
print("\nTop 10 Cuisines:")
print(top_cuisines.head(10))

print("\n================================================================================")
print("STEP 4: GENERATING PRESENTATION-QUALITY VISUALIZATIONS")
print("================================================================================")
PRIMARY_COLOR = '#E23744'  # Zomato Red
ACCENT_NAVY = '#1C2938'
ACCENT_TEAL = '#008080'
ACCENT_AMBER = '#FFAA00'

# 1. Rating Distribution
plt.figure(figsize=(9, 5.5))
ax = sns.histplot(df_valid['rate'], bins=31, kde=True, color=PRIMARY_COLOR, edgecolor='white', alpha=0.85)
plt.axvline(rate_mean, color='#1A237E', linestyle='--', linewidth=2, label=f'Mean Rating: {rate_mean:.2f}')
plt.axvline(rate_median, color='#004D40', linestyle=':', linewidth=2, label=f'Median Rating: {rate_median:.2f}')
plt.title("Figure 1: Distribution of Restaurant Ratings in Bangalore", fontsize=14, fontweight='bold', pad=15)
plt.xlabel("Zomato Rating (out of 5.0)", fontsize=12, labelpad=10)
plt.ylabel("Number of Restaurants", fontsize=12, labelpad=10)
plt.xlim(1.5, 5.0)
plt.legend(frameon=True, facecolor='white', framealpha=0.9, fontsize=11)
plt.tight_layout()
fig1_path = os.path.join(OUTPUT_FIG_DIR, "01_rating_distribution.png")
plt.savefig(fig1_path, dpi=300)
plt.close()
print(f"Saved: {fig1_path}")

# 2. Rating vs Votes
plt.figure(figsize=(9, 5.5))
# Create vote brackets for clear, interpretable visualization
bins_votes = [0, 50, 150, 500, 1000, 5000, 20000]
labels_votes = ['<50 (Low)', '50-150', '150-500 (Moderate)', '500-1k (High)', '1k-5k (Very High)', '5k+ (Mega)']
df_valid['vote_bracket'] = pd.cut(df_valid['votes'], bins=bins_votes, labels=labels_votes, include_lowest=True)
vote_bracket_stats = df_valid.groupby('vote_bracket', observed=True)['rate'].agg(['mean', 'count', 'std']).reset_index()

ax = sns.barplot(x='vote_bracket', y='mean', data=vote_bracket_stats, palette='Blues_r', edgecolor='#222222')
for p in ax.patches:
    h = p.get_height()
    ax.annotate(f"{h:.2f}", (p.get_x() + p.get_width() / 2., h - 0.25),
                ha='center', va='center', color='white', fontweight='bold', fontsize=11)
plt.title(f"Figure 2: Customer Engagement (Votes) vs Average Rating (Corr: +{corr_votes:.2f})", fontsize=14, fontweight='bold', pad=15)
plt.xlabel("Customer Votes Engagement Tier", fontsize=12, labelpad=10)
plt.ylabel("Average Rating (out of 5.0)", fontsize=12, labelpad=10)
plt.ylim(3.0, 4.6)
plt.tight_layout()
fig2_path = os.path.join(OUTPUT_FIG_DIR, "02_rating_vs_votes.png")
plt.savefig(fig2_path, dpi=300)
plt.close()
print(f"Saved: {fig2_path}")

# 3. Rating vs Approximate Cost
plt.figure(figsize=(9, 5.5))
bins_cost = [0, 300, 600, 1000, 2000, 7000]
labels_cost = ['Budget (<300)', 'Mid-Low (300-600)', 'Mid-High (600-1k)', 'Premium (1k-2k)', 'Fine Dining (>2k)']
df_valid['cost_bracket'] = pd.cut(df_valid['approx_cost'], bins=bins_cost, labels=labels_cost, include_lowest=True)
cost_bracket_stats = df_valid.groupby('cost_bracket', observed=True)['rate'].agg(['mean', 'count']).reset_index()

ax = sns.barplot(x='cost_bracket', y='mean', data=cost_bracket_stats, palette='YlOrRd', edgecolor='#222222')
for p in ax.patches:
    h = p.get_height()
    ax.annotate(f"{h:.2f}", (p.get_x() + p.get_width() / 2., h - 0.25),
                ha='center', va='center', color='white', fontweight='bold', fontsize=11)
plt.title(f"Figure 3: Approximate Cost for Two vs Average Rating (Corr: +{corr_cost:.2f})", fontsize=14, fontweight='bold', pad=15)
plt.xlabel("Cost for Two People (INR)", fontsize=12, labelpad=10)
plt.ylabel("Average Rating (out of 5.0)", fontsize=12, labelpad=10)
plt.ylim(3.0, 4.6)
plt.tight_layout()
fig3_path = os.path.join(OUTPUT_FIG_DIR, "03_rating_vs_cost.png")
plt.savefig(fig3_path, dpi=300)
plt.close()
print(f"Saved: {fig3_path}")

# 4. Average Rating by Restaurant Type (Top 12)
plt.figure(figsize=(10, 6))
top_types_12 = top_types.head(12).reset_index().sort_values(by='mean_rate', ascending=True)
colors = ['#1C2938' if r >= 3.8 else '#888888' for r in top_types_12['mean_rate']]
ax = plt.barh(top_types_12['primary_rest_type'], top_types_12['mean_rate'], color=colors, edgecolor='none')
for p in ax:
    w = p.get_width()
    plt.text(w + 0.03, p.get_y() + p.get_height()/2, f"{w:.2f}", va='center', fontsize=10, fontweight='bold', color='#1C2938')
plt.title("Figure 4: Average Restaurant Rating by Format / Dining Style", fontsize=14, fontweight='bold', pad=15)
plt.xlabel("Average Rating (out of 5.0)", fontsize=12, labelpad=10)
plt.ylabel("Restaurant Format", fontsize=12)
plt.xlim(3.0, 4.4)
plt.axvline(rate_mean, color=PRIMARY_COLOR, linestyle='--', label=f'City Average: {rate_mean:.2f}')
plt.legend(loc='lower right', frameon=True)
plt.tight_layout()
fig4_path = os.path.join(OUTPUT_FIG_DIR, "04_avg_rating_by_rest_type.png")
plt.savefig(fig4_path, dpi=300)
plt.close()
print(f"Saved: {fig4_path}")

# 5. Average Rating by Location (Top 15 volume hubs)
plt.figure(figsize=(10, 6.5))
top_locs_15 = top_locs.head(15).reset_index().sort_values(by='mean_rate', ascending=True)
loc_colors = ['#2E7D32' if r >= 3.8 else ('#D32F2F' if r < 3.6 else '#F57C00') for r in top_locs_15['mean_rate']]
bars = plt.barh(top_locs_15['location'], top_locs_15['mean_rate'], color=loc_colors)
for p in bars:
    w = p.get_width()
    plt.text(w + 0.03, p.get_y() + p.get_height()/2, f"{w:.2f}", va='center', fontsize=10, fontweight='bold')
plt.title("Figure 5: Performance Benchmark of Top 15 Bangalore Hubs by Volume", fontsize=14, fontweight='bold', pad=15)
plt.xlabel("Average Rating (out of 5.0)", fontsize=12, labelpad=10)
plt.ylabel("Bangalore Neighborhood / Hub", fontsize=12)
plt.xlim(3.0, 4.3)
plt.axvline(rate_mean, color='#1A237E', linestyle='--', label=f'City Average ({rate_mean:.2f})')
plt.legend(loc='lower right', frameon=True)
plt.tight_layout()
fig5_path = os.path.join(OUTPUT_FIG_DIR, "05_avg_rating_by_location.png")
plt.savefig(fig5_path, dpi=300)
plt.close()
print(f"Saved: {fig5_path}")

# 6. Online Ordering Availability vs Rating
plt.figure(figsize=(8, 5.5))
sns.boxplot(x='online_order', y='rate', data=df_valid, palette=['#78909C', PRIMARY_COLOR], width=0.45,
            boxprops=dict(alpha=0.9), medianprops=dict(color='black', linewidth=2))
means = df_valid.groupby('online_order')['rate'].mean()
plt.scatter([0, 1], [means['No'], means['Yes']], color='yellow', s=100, zorder=5, edgecolors='black', label='Mean Rating')
for i, m in enumerate([means['No'], means['Yes']]):
    plt.text(i, m + 0.12, f"Mean: {m:.2f}", ha='center', fontweight='bold', fontsize=11, color='#111111')
plt.title(f"Figure 6: Impact of Online Ordering on Ratings (Lift: +{means['Yes'] - means['No']:.2f})", fontsize=14, fontweight='bold', pad=15)
plt.xlabel("Online Ordering Available on Zomato", fontsize=12, labelpad=10)
plt.ylabel("Rating (out of 5.0)", fontsize=12, labelpad=10)
plt.ylim(1.8, 5.2)
plt.legend(loc='upper left', frameon=True)
plt.tight_layout()
fig6_path = os.path.join(OUTPUT_FIG_DIR, "06_online_order_vs_rating.png")
plt.savefig(fig6_path, dpi=300)
plt.close()
print(f"Saved: {fig6_path}")

print("\n================================================================================")
print("STEP 5: BUSINESS ANALYSIS & STATISTICAL TESTING")
print("================================================================================")
# T-test for online ordering
ttest_online = stats.ttest_ind(
    df_valid[df_valid['online_order'] == 'Yes']['rate'],
    df_valid[df_valid['online_order'] == 'No']['rate'],
    equal_var=False
)
print(f"Online Order T-test: t = {ttest_online.statistic:.4f}, p-value = {ttest_online.pvalue:.4e}")

# T-test for table booking
ttest_table = stats.ttest_ind(
    df_valid[df_valid['book_table'] == 'Yes']['rate'],
    df_valid[df_valid['book_table'] == 'No']['rate'],
    equal_var=False
)
print(f"Table Booking T-test: t = {ttest_table.statistic:.4f}, p-value = {ttest_table.pvalue:.4e}")

print("\n================================================================================")
print("STEP 6: PREDICTIVE MODELLING")
print("================================================================================")
# Features preparation
top_loc_list = df_valid['location'].value_counts().nlargest(20).index
df_valid['location_clean'] = df_valid['location'].apply(lambda x: x if x in top_loc_list else 'Other')

top_cui_list = df_valid['primary_cuisine'].value_counts().nlargest(15).index
df_valid['cuisine_clean'] = df_valid['primary_cuisine'].apply(lambda x: x if x in top_cui_list else 'Other')

top_type_list = df_valid['primary_rest_type'].value_counts().nlargest(10).index
df_valid['rest_type_clean'] = df_valid['primary_rest_type'].apply(lambda x: x if x in top_type_list else 'Other')

features_list = ['votes', 'approx_cost', 'online_order_encoded', 'book_table_encoded', 'location_clean', 'rest_type_clean', 'cuisine_clean']
X = df_valid[features_list].copy()
y = df_valid['rate'].copy()

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=42)
print(f"Train Set: {X_train.shape[0]:,} samples | Test Set: {X_test.shape[0]:,} samples")

cat_features = ['location_clean', 'rest_type_clean', 'cuisine_clean']
num_features = ['votes', 'approx_cost', 'online_order_encoded', 'book_table_encoded']

ohe = OneHotEncoder(drop='first', sparse_output=False, handle_unknown='ignore')
ct = ColumnTransformer(
    transformers=[
        ('num', 'passthrough', num_features),
        ('cat', ohe, cat_features)
    ]
)

X_train_trans = ct.fit_transform(X_train)
X_test_trans = ct.transform(X_test)
cat_names = ct.named_transformers_['cat'].get_feature_names_out(cat_features)
all_feature_names = num_features + list(cat_names)

# 1. Linear Regression
lr = LinearRegression()
lr.fit(X_train_trans, y_train)
y_pred_lr = lr.predict(X_test_trans)

mae_lr = mean_absolute_error(y_test, y_pred_lr)
rmse_lr = np.sqrt(mean_squared_error(y_test, y_pred_lr))
r2_lr = r2_score(y_test, y_pred_lr)

# 2. Random Forest Regressor
rf = RandomForestRegressor(n_estimators=100, max_depth=16, min_samples_split=5, random_state=42, n_jobs=-1)
rf.fit(X_train_trans, y_train)
y_pred_rf = rf.predict(X_test_trans)

mae_rf = mean_absolute_error(y_test, y_pred_rf)
rmse_rf = np.sqrt(mean_squared_error(y_test, y_pred_rf))
r2_rf = r2_score(y_test, y_pred_rf)

print("\nModel Evaluation Benchmark:")
print(f"{'Model':<25} | {'MAE':<8} | {'RMSE':<8} | {'R2 Score':<8}")
print("-" * 55)
print(f"{'Linear Regression':<25} | {mae_lr:<8.4f} | {rmse_lr:<8.4f} | {r2_lr:<8.4f}")
print(f"{'Random Forest Regressor':<25} | {mae_rf:<8.4f} | {rmse_rf:<8.4f} | {r2_rf:<8.4f}")

# Model Comparison Chart
plt.figure(figsize=(9, 5))
metrics_df = pd.DataFrame({
    'Metric': ['MAE (Lower is Better)', 'RMSE (Lower is Better)', 'R² Score (Higher is Better)'],
    'Linear Regression': [mae_lr, rmse_lr, r2_lr],
    'Random Forest Regressor': [mae_rf, rmse_rf, r2_rf]
})
metrics_melted = metrics_df.melt(id_vars='Metric', var_name='Model', value_name='Value')

ax = sns.barplot(x='Metric', y='Value', hue='Model', data=metrics_melted, palette=['#607D8B', PRIMARY_COLOR])
for p in ax.patches:
    h = p.get_height()
    if h > 0:
        ax.annotate(f"{h:.3f}", (p.get_x() + p.get_width() / 2., h + 0.02),
                    ha='center', va='bottom', fontsize=10, fontweight='bold')
plt.title("Figure 7: Predictive Model Performance Comparison (Test Set)", fontsize=14, fontweight='bold', pad=15)
plt.ylabel("Metric Score", fontsize=12)
plt.ylim(0, 1.0)
plt.legend(frameon=True, facecolor='white', framealpha=0.9)
plt.tight_layout()
fig7_path = os.path.join(OUTPUT_FIG_DIR, "07_model_comparison.png")
plt.savefig(fig7_path, dpi=300)
plt.close()
print(f"Saved: {fig7_path}")

print("\n================================================================================")
print("STEP 7: FEATURE IMPORTANCE & MODEL ANALYSIS")
print("================================================================================")
rf_importances = pd.Series(rf.feature_importances_, index=all_feature_names).sort_values(ascending=False)

# Domain grouping
group_imp = {
    'Customer Engagement (Votes)': rf.feature_importances_[0],
    'Location (Geography)': sum([rf.feature_importances_[i] for i, name in enumerate(all_feature_names) if 'location' in name]),
    'Price Level (Approx Cost)': rf.feature_importances_[1],
    'Cuisine Offering': sum([rf.feature_importances_[i] for i, name in enumerate(all_feature_names) if 'cuisine' in name]),
    'Dining Format (Rest Type)': sum([rf.feature_importances_[i] for i, name in enumerate(all_feature_names) if 'rest_type' in name]),
    'Table Booking Support': rf.feature_importances_[3],
    'Online Ordering Enabled': rf.feature_importances_[2],
}
group_imp_series = pd.Series(group_imp).sort_values(ascending=True)

plt.figure(figsize=(10, 6))
bar_colors = [PRIMARY_COLOR if v > 0.15 else ('#1C2938' if v > 0.05 else '#78909C') for v in group_imp_series.values]
ax = plt.barh(group_imp_series.index, group_imp_series.values * 100, color=bar_colors)
for p in ax:
    w = p.get_width()
    plt.text(w + 1.0, p.get_y() + p.get_height()/2, f"{w:.1f}%", va='center', fontsize=11, fontweight='bold', color='#1C2938')
plt.title("Figure 8: Domain Feature Importance in Predicting Restaurant Ratings (Random Forest)", fontsize=14, fontweight='bold', pad=15)
plt.xlabel("Relative Importance (%)", fontsize=12, labelpad=10)
plt.xlim(0, 75)
plt.tight_layout()
fig8_path = os.path.join(OUTPUT_FIG_DIR, "08_rf_feature_importance.png")
plt.savefig(fig8_path, dpi=300)
plt.close()
print(f"Saved: {fig8_path}")

print("\nAll tasks completed successfully!")
