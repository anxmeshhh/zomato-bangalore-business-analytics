# 📊 Power BI Dashboard Build Guide — Zomato Bangalore Analytics

This step-by-step recipe recreates all Review 1 visuals in **Power BI Desktop** in under 10 minutes.

---

## ⚡ STEP 1: Load Data & Apply Theme (2 Minutes)

1. **Open Power BI Desktop** (Search `Power BI Desktop` in Windows Start Menu).
2. **Import Dataset:**
   - Click **`Get Data`** $\rightarrow$ **`Text/CSV`**.
   - Browse to `C:\Users\Animesh\Desktop\BI&A\` and select **[`zomato_powerbi.csv`](zomato_powerbi.csv)**.
   - Click **`Load`**.
3. **Apply the Custom Zomato Theme:**
   - Go to the top ribbon $\rightarrow$ click the **`View`** tab.
   - Click the **`Themes`** dropdown $\rightarrow$ click **`Browse for themes`**.
   - Browse to `C:\Users\Animesh\Desktop\BI&A\Zomato_Project\powerbi\` and select **[`zomato_theme.json`](zomato_theme.json)**.
   - *Result:* Instantly styles the report with Zomato Crimson (`#E23744`), clean slate cards, and modern fonts!

---

## 🔢 STEP 2: Set Column Sort Orders (1 Minute)
*(Ensures brackets display logically from low to high instead of alphabetically)*

1. In the right-hand **Data** pane, click on the **`Rating_Bracket`** column.
   - In the top ribbon, click **`Column tools`** $\rightarrow$ click **`Sort by column`** $\rightarrow$ select **`Rating_Bracket_Sort`**.
2. Click on the **`Vote_Bracket`** column:
   - Click **`Sort by column`** $\rightarrow$ select **`Vote_Bracket_Sort`**.
3. Click on the **`Cost_Bracket`** column:
   - Click **`Sort by column`** $\rightarrow$ select **`Cost_Bracket_Sort`**.

---

## 📐 STEP 3: Create Key DAX Measures (2 Minutes)

Click on **`Home`** $\rightarrow$ **`New Measure`** and paste these measures one by one:

```dax
// 1. Total Restaurants
Total Restaurants = COUNTROWS(zomato_powerbi)

// 2. Average Rating
Average Rating = AVERAGE(zomato_powerbi[rate])

// 3. Average Cost for Two
Average Cost for Two = AVERAGE(zomato_powerbi[approx_cost])

// 4. Total Engagement (Votes)
Total Votes = SUM(zomato_powerbi[votes])

// 5. Online Order Share %
Online Order Share % = 
DIVIDE(
    CALCULATE(COUNTROWS(zomato_powerbi), zomato_powerbi[online_order] = "Yes"),
    COUNTROWS(zomato_powerbi),
    0
)

// 6. Table Booking Share %
Table Booking Share % = 
DIVIDE(
    CALCULATE(COUNTROWS(zomato_powerbi), zomato_powerbi[book_table] = "Yes"),
    COUNTROWS(zomato_powerbi),
    0
)
```

---

## 🎨 STEP 4: Build Visuals (Drag-and-Drop Recipe)

### 1. Top KPI Cards Ribbon (Top of Canvas)
Add **6 Card Visuals** in a horizontal row across the top:
* Card 1: Field = `[Total Restaurants]` (Displays `41.2K`)
* Card 2: Field = `[Average Rating]` (Format as `0.00`, displays `3.70`)
* Card 3: Field = `[Average Cost for Two]` (Format as Currency `₹0`, displays `₹604`)
* Card 4: Field = `[Total Votes]` (Displays `14.5M`)
* Card 5: Field = `[Online Order Share %]` (Format as `%`, displays `65.7%`)
* Card 6: Field = `[Table Booking Share %]` (Format as `%`, displays `15.2%`)

---

### 2. Slicers (Top Right or Left Sidebar)
Add **3 Slicer Visuals** for interactive filtering:
* **Slicer 1 (Location):** Field = `location` (Dropdown style)
* **Slicer 2 (Dining Format):** Field = `primary_rest_type`
* **Slicer 3 (Online Order):** Field = `online_order` (Tile style)

---

### 3. Visual 1: Distribution of Restaurant Ratings
* **Visual Type:** **Clustered Column Chart**
* **X-axis:** `Rating_Bracket`
* **Y-axis:** `Total Restaurants`
* **Title:** *"Figure 1: Distribution of Restaurant Ratings"*
* **Insight:** Bell-curve centered at 3.70; elite top 25% starts at $\ge 4.0$.

---

### 4. Visual 2: Engagement (Votes) vs Rating
* **Visual Type:** **Clustered Column Chart**
* **X-axis:** `Vote_Bracket`
* **Y-axis:** `Average Rating`
* **Title:** *"Figure 2: Customer Engagement (Votes) vs Rating"*
* **Data Labels:** Turn **On** (Shows $3.49 \rightarrow 3.79 \rightarrow 4.01 \rightarrow 4.17 \rightarrow 4.38$).

---

### 5. Visual 3: Approximate Cost for Two vs Rating
* **Visual Type:** **Clustered Column Chart**
* **X-axis:** `Cost_Bracket`
* **Y-axis:** `Average Rating`
* **Title:** *"Figure 3: Cost for Two vs Average Rating"*
* **Data Labels:** Turn **On** (Shows $3.46 \rightarrow 3.65 \rightarrow 3.88 \rightarrow 4.10 \rightarrow 4.24$).

---

### 6. Visual 4: Rating by Dining Format
* **Visual Type:** **Clustered Bar Chart (Horizontal)**
* **Y-axis:** `primary_rest_type`
* **X-axis:** `Average Rating`
* **Filter (Visual Level):** Filter `primary_rest_type` by **Top 10** by `Total Restaurants`.
* **Title:** *"Figure 4: Average Rating by Dining Format"*
* **Insight:** Pubs (4.10) & Cafes (3.87) comfortably beat Quick Bites (3.55).

---

### 7. Visual 5: Performance Benchmark across Top 15 Locations
* **Visual Type:** **Clustered Bar Chart (Horizontal)**
* **Y-axis:** `location`
* **X-axis:** `Average Rating`
* **Filter (Visual Level):** Filter `location` by **Top 15** by `Total Restaurants`.
* **Title:** *"Figure 5: Performance Benchmark across Top 15 Hubs"*
* **Insight:** Koramangala 5th Block averages 4.01; BTM lags at 3.57.

---

### 8. Visual 6: Digital Operational Impact
* **Visual Type:** **Clustered Column Chart**
* **X-axis:** `book_table`
* **Y-axis:** `Average Rating`
* **Legend:** `online_order`
* **Title:** *"Figure 6: Table Booking & Online Ordering Lift"*
* **Insight:** Table booking yields $+0.52$ rating lift ($4.14$ vs $3.62$).

---

## 💾 STEP 5: Save & Present

* Click **`File`** $\rightarrow$ **`Save As`** $\rightarrow$ save as **`Zomato_Bangalore_Analytics.pbix`** in `C:\Users\Animesh\Desktop\BI&A\`.
* When presenting, clicking on any slicer (e.g. `Koramangala 5th Block` or `Yes` for Table Booking) will dynamically cross-filter every chart on the screen!
