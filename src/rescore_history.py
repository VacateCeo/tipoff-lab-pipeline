import pandas as pd
import pickle
import sys
sys.path.insert(0, "src")
from predict import predict_game
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

games = pd.read_parquet("data/games.parquet")
games["date"] = pd.to_datetime(games["date"])
with open("data/model.pkl", "rb") as f:
    model = pickle.load(f)

sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
rows = sb.table("predictions").select("id,game_date,home_team,away_team,spread,total").execute().data
print(f"Found {len(rows)} predictions to recalculate")

for r in rows:
    result = predict_game(r["home_team"], r["away_team"], r["game_date"], games, model, r.get("spread"), r.get("total"))
    if result:
        sb.table("predictions").update({
            "watchability": result["watchability"],
            "reasons": result["reasons"],
            "badges": result["badges"],
        }).eq("id", r["id"]).execute()
        print(f"  Updated {r['away_team']} @ {r['home_team']} {r['game_date']}: {result['watchability']} {result['reasons']}")

print("Done.")
