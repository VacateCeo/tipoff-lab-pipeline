import pandas as pd
import numpy as np
import pickle
import sys
import os
from datetime import date, datetime
from supabase import create_client
from dotenv import load_dotenv
from nba_api.live.nba.endpoints import scoreboard

sys.path.insert(0, "src")
from build_features import get_rolling_team_stats
from predict import predict_today

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

TEAM_ID_MAP = {
    1610612737: "ATL", 1610612738: "BOS", 1610612751: "BKN", 1610612766: "CHA",
    1610612741: "CHI", 1610612739: "CLE", 1610612742: "DAL", 1610612743: "DEN",
    1610612765: "DET", 1610612744: "GSW", 1610612745: "HOU", 1610612754: "IND",
    1610612746: "LAC", 1610612747: "LAL", 1610612763: "MEM", 1610612748: "MIA",
    1610612749: "MIL", 1610612750: "MIN", 1610612740: "NOP", 1610612752: "NYK",
    1610612760: "OKC", 1610612753: "ORL", 1610612755: "PHI", 1610612756: "PHX",
    1610612757: "POR", 1610612758: "SAC", 1610612759: "SAS", 1610612761: "TOR",
    1610612762: "UTA", 1610612764: "WAS"
}

def get_todays_games():
    """Fetch today's NBA games from the NBA API."""
    games_data = scoreboard.ScoreBoard()
    games_dict = games_data.get_dict()
    
    matchups = []
    try:
        games_list = games_dict["scoreboard"]["games"]
        for game in games_list:
            home_id = game["homeTeam"]["teamId"]
            away_id = game["awayTeam"]["teamId"]
            home = TEAM_ID_MAP.get(int(home_id))
            away = TEAM_ID_MAP.get(int(away_id))
            if home and away:
                matchups.append((home, away, None, None))
    except Exception as e:
        print(f"Error parsing games: {e}")
        return []

    print(f"Found {len(matchups)} games today: {matchups}")
    return matchups

def run_daily_update(game_date=None):
    if game_date is None:
        game_date = date.today().strftime("%Y-%m-%d")

    print(f"Running daily update for {game_date}...")

    print("Loading model and data...")
    with open("data/model.pkl", "rb") as f:
        model = pickle.load(f)

    games = pd.read_parquet("data/games.parquet")
    games["date"] = pd.to_datetime(games["date"])

    matchups = get_todays_games()
    if not matchups:
        print("No games today, exiting.")
        return

    results = predict_today(game_date, matchups, games, model)

    if not results:
        print("No predictions generated.")
        return

    print(f"Generated {len(results)} predictions")
    for r in results:
        print(f"  {r['watchability']:.1f}/10 — {r['away_team']} @ {r['home_team']}: {r['reasons']}")

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # delete existing predictions for today
    supabase.table("predictions").delete().eq("game_date", game_date).execute()

    # insert new predictions
    rows = []
    for r in results:
        rows.append({
            "game_date": game_date,
            "home_team": r["home_team"],
            "away_team": r["away_team"],
            "watchability": r["watchability"],
            "reasons": r["reasons"],
            "spread": r.get("spread"),
            "total": r.get("total"),
        })

    supabase.table("predictions").insert(rows).execute()
    print(f"Saved {len(rows)} predictions to Supabase.")

if __name__ == "__main__":
    run_daily_update()