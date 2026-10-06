"""
Load cleaned Zomato dataset into Microsoft SQL Server (ZomatoDB)
"""
import os
import pyodbc
import pandas as pd
import numpy as np

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "zomato_powerbi.csv")
print(f"Reading dataset: {CSV_PATH}")
df = pd.read_csv(CSV_PATH)
df = df.replace({np.nan: None})

print(f"Dataset shape to insert: {df.shape}")

# Connection string
conn_str = (
    "Driver={ODBC Driver 18 for SQL Server};"
    "Server=localhost;"
    "Database=ZomatoDB;"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)

conn = pyodbc.connect(conn_str)
cursor = conn.cursor()
cursor.fast_executemany = True

# 1. Create Table
create_table_sql = """
IF OBJECT_ID('dbo.Restaurants', 'U') IS NOT NULL
    DROP TABLE dbo.Restaurants;

CREATE TABLE dbo.Restaurants (
    restaurant_id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(255),
    online_order VARCHAR(10),
    book_table VARCHAR(10),
    rate FLOAT,
    votes INT,
    location NVARCHAR(150),
    rest_type NVARCHAR(200),
    dish_liked NVARCHAR(MAX),
    cuisines NVARCHAR(400),
    listed_in_type NVARCHAR(100),
    listed_in_city NVARCHAR(100),
    approx_cost FLOAT,
    primary_rest_type NVARCHAR(100),
    primary_cuisine NVARCHAR(100),
    Rating_Bracket VARCHAR(50),
    Rating_Bracket_Sort INT,
    Vote_Bracket VARCHAR(50),
    Vote_Bracket_Sort INT,
    Cost_Bracket VARCHAR(50),
    Cost_Bracket_Sort INT,
    Performance_Tier VARCHAR(50)
);
"""
print("Creating dbo.Restaurants table in ZomatoDB...")
cursor.execute(create_table_sql)
conn.commit()

# 2. Insert Data
insert_sql = """
INSERT INTO dbo.Restaurants (
    name, online_order, book_table, rate, votes, location, rest_type,
    dish_liked, cuisines, listed_in_type, listed_in_city, approx_cost,
    primary_rest_type, primary_cuisine, Rating_Bracket, Rating_Bracket_Sort,
    Vote_Bracket, Vote_Bracket_Sort, Cost_Bracket, Cost_Bracket_Sort, Performance_Tier
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
"""

# Prepare rows
records = df[[
    'name', 'online_order', 'book_table', 'rate', 'votes', 'location', 'rest_type',
    'dish_liked', 'cuisines', 'listed_in(type)', 'listed_in(city)', 'approx_cost',
    'primary_rest_type', 'primary_cuisine', 'Rating_Bracket', 'Rating_Bracket_Sort',
    'Vote_Bracket', 'Vote_Bracket_Sort', 'Cost_Bracket', 'Cost_Bracket_Sort', 'Performance_Tier'
]].values.tolist()

print(f"Inserting {len(records):,} records with fast_executemany...")
cursor.executemany(insert_sql, records)
conn.commit()
print("Bulk insertion complete!")

# 3. Create Analytical View
create_view_sql = """
IF OBJECT_ID('dbo.vw_RestaurantAnalytics', 'V') IS NOT NULL
    DROP VIEW dbo.vw_RestaurantAnalytics;
GO
CREATE VIEW dbo.vw_RestaurantAnalytics AS
SELECT 
    restaurant_id,
    name AS Restaurant_Name,
    online_order AS Online_Order,
    book_table AS Table_Booking,
    rate AS Rating,
    votes AS Votes,
    location AS Neighborhood,
    primary_rest_type AS Dining_Format,
    primary_cuisine AS Primary_Cuisine,
    approx_cost AS Cost_For_Two,
    Rating_Bracket,
    Rating_Bracket_Sort,
    Vote_Bracket,
    Vote_Bracket_Sort,
    Cost_Bracket,
    Cost_Bracket_Sort,
    Performance_Tier
FROM dbo.Restaurants;
"""
# Execute view statements splitting by GO
for statement in create_view_sql.split("GO"):
    if statement.strip():
        cursor.execute(statement)
conn.commit()
print("Created view: dbo.vw_RestaurantAnalytics")

# 4. Verify Count
cursor.execute("SELECT COUNT(*), AVG(rate), AVG(approx_cost) FROM dbo.Restaurants;")
row = cursor.fetchone()
print(f"Verification -> Count: {row[0]:,}, Avg Rating: {row[1]:.2f}, Avg Cost: Rs.{row[2]:.2f}")

conn.close()
print("SQL Server ingestion finished successfully!")
