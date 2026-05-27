import pandas as pd
import pickle
import sys
sys.path.insert(0, "src")
from predict import predict_game
from supabase import create_client
from get_standings import get_standings
from get_player_stats import get_player_stats
from cache_manager import load_cache, save_cache
import os
from dotenv import load_dotenv

load_dotenv()

games = pd.read_parquet("data/games.parquet")
games["date"] = pd.to_datetime(games["date"])
with open("data/model.pkl", "rb") as f:
    model = pickle.load(f)

standings = load_cache("standings")
if standings is None:
    standings = get_standings()
    save_cache("standings", standings)

player_stats = load_cache("player_stats")
if player_stats is None:
    player_stats = get_player_stats()
    save_cache("player_stats", player_stats)

sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
rows = sb.table("predictions").select("id,game_date,home_team,away_team,spread,total").execute().data
print(f"Found {len(rows)} predictions to recalculate")

for r in rows:
    result = predict_game(r["home_team"], r["away_team"], r["game_date"], games, model, r.get("spread"), r.get("total"), standings=standings, player_stats=player_stats)
    if result:
        sb.table("predictions").update({
            "watchability": result["watchability"],
            "reasons": result["reasons"],
            "badges": result["badges"],
        }).eq("id", r["id"]).execute()
        print(f"  Updated {r['away_team']} @ {r['home_team']} {r['game_date']}: {result['watchability']} {result['reasons']}")

print("Done.")
