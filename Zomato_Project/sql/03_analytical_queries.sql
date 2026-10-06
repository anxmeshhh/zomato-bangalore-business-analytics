-- ==============================================================================
-- ZOMATO BANGALORE - SQL SERVER ANALYTICAL QUERIES (SSMS)
-- Database: ZomatoDB
-- ==============================================================================

USE ZomatoDB;
GO

-- 1. Executive Summary KPIs
SELECT 
    COUNT(*) AS Total_Restaurants,
    ROUND(AVG(rate), 2) AS Average_Rating,
    ROUND(AVG(approx_cost), 2) AS Average_Cost_For_Two,
    SUM(votes) AS Total_Customer_Votes,
    ROUND(100.0 * SUM(CASE WHEN online_order = 'Yes' THEN 1 ELSE 0 END) / COUNT(*), 1) AS Pct_Online_Order,
    ROUND(100.0 * SUM(CASE WHEN book_table = 'Yes' THEN 1 ELSE 0 END) / COUNT(*), 1) AS Pct_Table_Booking
FROM dbo.Restaurants;
GO

-- 2. Rating Distribution by Brackets (Figure 1 in SQL)
SELECT 
    Rating_Bracket,
    Rating_Bracket_Sort,
    COUNT(*) AS Restaurant_Count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS Pct_Share
FROM dbo.Restaurants
GROUP BY Rating_Bracket, Rating_Bracket_Sort
ORDER BY Rating_Bracket_Sort;
GO

-- 3. Customer Engagement (Votes) vs Average Rating (Figure 2 in SQL)
SELECT 
    Vote_Bracket,
    Vote_Bracket_Sort,
    COUNT(*) AS Restaurant_Count,
    ROUND(AVG(rate), 2) AS Avg_Rating,
    ROUND(AVG(approx_cost), 0) AS Avg_Cost
FROM dbo.Restaurants
GROUP BY Vote_Bracket, Vote_Bracket_Sort
ORDER BY Vote_Bracket_Sort;
GO

-- 4. Spend Tiers (Cost for Two) vs Average Rating (Figure 3 in SQL)
SELECT 
    Cost_Bracket,
    Cost_Bracket_Sort,
    COUNT(*) AS Restaurant_Count,
    ROUND(AVG(rate), 2) AS Avg_Rating,
    ROUND(AVG(CAST(votes AS FLOAT)), 0) AS Avg_Votes
FROM dbo.Restaurants
GROUP BY Cost_Bracket, Cost_Bracket_Sort
ORDER BY Cost_Bracket_Sort;
GO

-- 5. Top 15 Restaurant Formats by Performance (Figure 4 in SQL)
SELECT TOP 15
    primary_rest_type AS Dining_Format,
    COUNT(*) AS Total_Outlets,
    ROUND(AVG(rate), 2) AS Avg_Rating,
    ROUND(AVG(approx_cost), 0) AS Avg_Cost_For_Two
FROM dbo.Restaurants
GROUP BY primary_rest_type
HAVING COUNT(*) >= 50
ORDER BY Avg_Rating DESC;
GO

-- 6. Top 15 Geographic Hubs by Outlet Volume & Rating Benchmark (Figure 5 in SQL)
SELECT TOP 15
    location AS Neighborhood,
    COUNT(*) AS Total_Outlets,
    ROUND(AVG(rate), 2) AS Avg_Rating,
    ROUND(AVG(approx_cost), 0) AS Avg_Cost_For_Two,
    ROUND(AVG(CAST(votes AS FLOAT)), 0) AS Avg_Votes_Per_Outlet
FROM dbo.Restaurants
GROUP BY location
ORDER BY Total_Outlets DESC;
GO

-- 7. Digital Capabilities Impact (Figure 6 in SQL)
SELECT 
    book_table AS Table_Booking,
    online_order AS Online_Order,
    COUNT(*) AS Outlets_Count,
    ROUND(AVG(rate), 2) AS Avg_Rating,
    ROUND(AVG(approx_cost), 0) AS Avg_Cost,
    SUM(votes) AS Total_Votes
FROM dbo.Restaurants
GROUP BY book_table, online_order
ORDER BY Avg_Rating DESC;
GO

-- 8. Top 10 Elite Cuisines with High Customer Acceptance
SELECT TOP 10
    primary_cuisine AS Cuisine,
    COUNT(*) AS Outlets_Count,
    ROUND(AVG(rate), 2) AS Avg_Rating,
    ROUND(AVG(approx_cost), 0) AS Avg_Cost
FROM dbo.Restaurants
GROUP BY primary_cuisine
HAVING COUNT(*) >= 100
ORDER BY Avg_Rating DESC;
GO
