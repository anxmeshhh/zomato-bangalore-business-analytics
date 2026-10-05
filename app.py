import pandas as pd

df = pd.read_csv("zomato.csv")

print("Rows:", df.shape[0])
print("Columns:", df.shape[1])

display(df.head())