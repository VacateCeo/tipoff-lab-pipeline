import pandas as pd
from bs4 import BeautifulSoup
import os
import glob

files = [os.path.join("data", f) for f in os.listdir("data") if f.endswith(".htm") or f.endswith(".html")]
print(f"Found {len(files)} files: {files}")

all_rows = []

for filepath in files:
    season = os.path.basename(filepath)
    with open(filepath, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    
    table = soup.find("table")
    if not table:
        print(f"No table found in {filepath}")
        continue

    rows = table.find_all("tr")
    
    # parse pairs of rows (visitor + home)
    i = 1  # skip header row
    while i < len(rows) - 1:
        try:
            away_cells = [td.text.strip() for td in rows[i].find_all("td")]
            home_cells = [td.text.strip() for td in rows[i+1].find_all("td")]
            
            if len(away_cells) < 10 or len(home_cells) < 10:
                i += 1
                continue
            
            # columns: Date, Rot, VH, Team, 1st, 2nd, 3rd, 4th, Final, Open, Close, ML, 2H
            date = away_cells[0]
            away_team = away_cells[3]
            home_team = home_cells[3]
            
            try:
                away_score = int(away_cells[8])
                home_score = int(home_cells[8])
            except:
                i += 2
                continue
            
            # spread is in home row Close column (index 10)
            # total is in away row Close column (index 10)
            try:
                total = float(away_cells[10])
                spread = float(home_cells[10])  # positive = home dog, negative = home fav
            except:
                i += 2
                continue
            
            all_rows.append({
                "date": date,
                "away_team": away_team,
                "home_team": home_team,
                "away_score": away_score,
                "home_score": home_score,
                "spread": spread,
                "total": total,
                "season": season,
            })
        except Exception as e:
            pass
        i += 2

df = pd.DataFrame(all_rows)
print(f"Parsed {len(df)} games")
print(df.head(10))
df.to_parquet("data/vegas.parquet", index=False)
print("Saved to data/vegas.parquet")