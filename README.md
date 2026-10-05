# 🍽️ Zomato Bangalore Restaurants — Business Analytics & ML (Review 1)

[![GitHub Repo](https://img.shields.io/badge/GitHub-anxmeshhh-blue.svg)](https://github.com/anxmeshhh/zomato-bangalore-business-analytics)
[![Python](https://img.shields.io/badge/Python-3.12-brightgreen.svg)](https://www.python.org/)
[![Scikit-Learn](https://img.shields.io/badge/ML-Scikit--Learn-orange.svg)](https://scikit-learn.org/)

**Core Research Question:** *What measurable factors truly influence restaurant ratings and customer preferences on Zomato in Bangalore?*

---

## 🗺️ Code & System Reference Map

| Pipeline Step | Source Code File | Output / Deliverable |
| :--- | :--- | :--- |
| **Ingestion & Profiling** | [`Zomato_Bangalore_Review_1_Business_Analytics.ipynb`](Zomato_Bangalore_Review_1_Business_Analytics.ipynb) (Cell 1-2) | Profiling table, missing value audit |
| **Data Cleaning** | [`Zomato_Project/scripts/generate_review1_assets.py`](Zomato_Project/scripts/generate_review1_assets.py) | 41,190 cleaned analytical records |
| **EDA & Statistical Tests** | Notebook (Section 3 & 5) | Correlation matrix, two-sample t-tests |
| **Visualizations** | `generate_review1_assets.py` | 8 High-Res PNGs in `Zomato_Project/outputs/figures/` |
| **Predictive Modelling** | Notebook (Section 6) | Linear Regression vs Random Forest evaluation |
| **Feature Importance** | Notebook (Section 7) | Domain attribution breakdown |

---

## ⚡ Key Facts At a Glance

* **Cleaned Cohort:** **41,190 restaurants** (from 51,717 raw listings after removing 400MB text noise and unrated entries).
* **Rating Benchmark:** Mean = **3.70**, Median = **3.70**, IQR = **[3.40, 4.00]**, Range = **[1.80, 4.90]**.
* **Engagement Engine:** Votes correlate **+0.435** with rating. $>1,000$ votes average **4.17** vs **3.49** for $<50$ votes.
* **Pricing Power:** Cost for two correlates **+0.385** with rating. Fine dining ($>₹2,000$) averages **4.24** vs **3.46** for budget ($<₹300$).
* **Format Difference:** Pubs (**4.10**) and Cafes (**3.87**) outperform Quick Bites (**3.55**).
* **Location Disparity:** Koramangala 5th Block averages **4.01** with 965 votes/outlet. BTM has high volume (3,873 outlets) but lags at **3.57**.
* **Operational Lift:** Table booking provides a **+0.52 rating lift** ($4.14$ vs $3.62$, $t = 118.16, p < 0.0001$).

---

## 🤖 Predictive Machine Learning Benchmark

*Evaluated on an unseen 20% test holdout ($n = 8,238$ restaurants):*

| Model Evaluated | MAE (Mean Absolute Error) | RMSE | $R^2$ Score (Variance Explained) |
| :--- | :---: | :---: | :---: |
| **Linear Regression (Baseline)** | 0.2670 | 0.3437 | 37.64% |
| **Random Forest Regressor** | **0.1302** | **0.1986** | **79.18%** |

### Random Forest Feature Importance
1. **Customer Engagement (`votes`):** **63.55%**
2. **Location (`location`):** **11.01%**
3. **Price Level (`approx_cost`):** **8.59%**
4. **Cuisine Offering:** **7.69%**
5. **Dining Format (`rest_type`):** **5.20%**
6. **Table Booking & Online Ordering:** **3.96%**

---

## 💡 Top Strategic Takeaways (Finding → Action)
1. **Drive Reviews:** 63.6% of predictive power is votes ($r = +0.435$). Prompt happy diners to cross 500+ votes.
2. **Enable Reservations:** Table booking gives a **+0.52 rating advantage** and signals quality dining.
3. **Avoid Price Wars:** Higher spend correlates with higher ratings ($r = +0.385$). Price for margin and food quality.
4. **Lifestyle Formats Win:** Experiential spaces (Cafes/Pubs) outperform high-turnover quick bites.
5. **Target Quality Corridors:** Koramangala (4.01) delivers customer purchasing power that dense student clusters like BTM (3.57) lack.

---

## 🛠️ How to Run
```bash
# Clone repository
git clone https://github.com/anxmeshhh/zomato-bangalore-business-analytics.git
cd zomato-bangalore-business-analytics

# Run end-to-end Python pipeline
python Zomato_Project/scripts/generate_review1_assets.py
```
Or open [`Zomato_Bangalore_Review_1_Business_Analytics.ipynb`](Zomato_Bangalore_Review_1_Business_Analytics.ipynb) directly in Google Colab / Jupyter!
