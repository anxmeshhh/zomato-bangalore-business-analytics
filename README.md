# 🍽️ Zomato Bangalore Restaurants — Business Analytics & Predictive Modelling

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Scikit-Learn](https://img.shields.io/badge/Library-Scikit--Learn-orange.svg)](https://scikit-learn.org/)
[![Pandas](https://img.shields.io/badge/Data-Pandas-brightgreen.svg)](https://pandas.pydata.org/)
[![Matplotlib](https://img.shields.io/badge/Visuals-Seaborn%20%26%20Matplotlib-red.svg)](https://matplotlib.org/)

> **Academic Coursework:** Business Intelligence & Analytics (BI&A)  
> **Milestone:** Review 1 (Modelling, Visualization & Empirical Business Analysis)  
> **Core Research Question:** *What factors influence restaurant ratings and customer preferences in Bangalore?*

---

## 📌 Executive Summary
This project provides an empirical, end-to-end Business Analytics study on the Bangalore restaurant sector using Kaggle's Zomato Bangalore Restaurants dataset (51,717 raw listings $\rightarrow$ 41,190 cleaned records). The study addresses pricing power, customer engagement, spatial clustering, format viability, and operational digitization, culminating in predictive machine learning models that forecast restaurant ratings.

---

## 🚀 Key Results At a Glance
- **Dataset Evaluated:** 41,190 complete restaurant listings.
- **Rating Benchmark:** Mean = 3.70 / 5.0, Median = 3.70, Range: 1.8 to 4.9.
- **Engagement Driver:** Customer review votes correlate positively with rating ($r = +0.435$) and account for **63.55%** of predictive power.
- **Table Booking Lift:** Restaurants supporting table reservations achieve a **+0.52 rating advantage** (4.14 vs 3.62, $p < 0.0001$).
- **Top ML Model:** Random Forest Regressor achieves **$R^2 = 79.18\%$** with an average error (MAE) of just **0.13 rating points**, outperforming Linear Regression ($R^2 = 37.64\%$).

---

## 📊 Visualizations & Key Charts
Generated at 300 DPI in `Zomato_Project/outputs/figures/`:
1. **Rating Distribution:** Bell-shaped normal curve centered at 3.70.
2. **Customer Engagement vs Rating:** Monotonic rating growth across review volume brackets ($<50$ votes at 3.49 up to $>5,000$ votes at 4.38).
3. **Approximate Cost vs Rating:** Higher spend brackets consistently achieve higher customer ratings ($r = +0.385$).
4. **Format Benchmark:** Experiential formats (Pubs: 4.10, Cafes: 3.87) strongly outperform quick-turnover units (Quick Bites: 3.55).
5. **Geographic Clustering:** Koramangala 5th Block (4.01) and Indiranagar (3.83) beat student/budget hubs like BTM (3.57).
6. **Online Ordering Lift:** Statistically significant positive lift of +0.064 rating points ($p < 10^{-40}$).
7. **Model Comparison:** Random Forest vs Linear Regression benchmark on MAE, RMSE, and $R^2$.
8. **Feature Importance:** Domain attribution showing votes (63.6%), location (11.0%), and price level (8.6%) as dominant factors.

---

## 🤖 Predictive Machine Learning Benchmark

| Model | MAE | RMSE | $R^2$ Score (Variance Explained) |
| :--- | :---: | :---: | :---: |
| **Linear Regression (Baseline)** | 0.2670 | 0.3437 | 37.64% |
| **Random Forest Regressor** | **0.1302** | **0.1986** | **79.18%** |

---

## 💡 Top Strategic Business Insights (Finding → Evidence → Implication)
1. **Customer Engagement is King:** Reviews generate algorithmic momentum and trust. Managing post-dining review collection is the highest-ROI operational activity.
2. **Table Booking Signals Quality:** Adding reservation capability unlocks premium perception and +0.52 rating lift.
3. **Price Quality Heuristic:** Price discounting in Bangalore harms perceived quality. Diners willingly pay for ambiance and hygiene.
4. **Experience Over Speed:** Cafes and Pubs command greater consumer sentiment than fast food.
5. **Density $\neq$ Excellence:** BTM has the highest volume (3,873 listings) but lower average ratings due to cut-throat price competition; Koramangala delivers both density and culinary quality.

---

## 📁 Repository Structure
```
├── Zomato_Bangalore_Review_1_Business_Analytics.ipynb   # Colab/Jupyter Notebook
├── zomato.csv (Ignored from git due to >100MB limit)
├── Zomato_Project/
│   ├── scripts/
│   │   ├── generate_review1_assets.py                 # Master execution pipeline
│   │   └── build_colab_notebook.py                    # Notebook builder
│   └── outputs/
│       └── figures/                                   # 8 High-res 300 DPI figures
│           ├── 01_rating_distribution.png
│           ├── 02_rating_vs_votes.png
│           ├── 03_rating_vs_cost.png
│           ├── 04_avg_rating_by_rest_type.png
│           ├── 05_avg_rating_by_location.png
│           ├── 06_online_order_vs_rating.png
│           ├── 07_model_comparison.png
│           └── 08_rf_feature_importance.png
├── .gitignore                                         # Excludes files >100MB
└── README.md
```

---

## 🛠️ How to Run Locally or in Google Colab
1. Clone this repository:
   ```bash
   git clone https://github.com/<your-username>/zomato-bangalore-business-analytics.git
   cd zomato-bangalore-business-analytics
   ```
2. Download `zomato.csv` from [Kaggle](https://www.kaggle.com/datasets/himanshupoddar/zomato-bangalore-restaurants) and place it in the project root.
3. Run the automated script:
   ```bash
   python Zomato_Project/scripts/generate_review1_assets.py
   ```
   Or open [`Zomato_Bangalore_Review_1_Business_Analytics.ipynb`](Zomato_Bangalore_Review_1_Business_Analytics.ipynb) in Google Colab / Jupyter Notebook and execute all cells!
