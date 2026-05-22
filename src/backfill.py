import pandas as pd
import numpy as np
import pickle
import sys
import os
import requests
import time
import random
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, "src")
from predict import predict_game
from fetch_results import compute_excitement

load_dotenv()

ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
ESPN_SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary"

ESPN_TRICODE_FIX = {
    "GS": "GSW", "NO": "NOP", "NY": "NYK",
    "SA": "SAS", "UTAH": "UTA", "WSH": "WAS",
}

def normalize_tricode(code):
    return ESPN_TRICODE_FIX.get(code, code)

def fetch_completed_games(game_date):
    params = {"dates": game_date.replace("-", "")}
    try:
        r = requests.get(ESPN_SCOREBOARD_URL, params=params, timeout=10)
        r.raise_for_status()
        completed = []
        for event in r.json().get("events", []):
            if event["status"]["type"]["completed"]:
                comp = event["competitions"][0]
                home = normalize_tricode(next(t["team"]["abbreviation"] for t in comp["competitors"] if t["homeAway"] == "home"))
                away = normalize_tricode(next(t["team"]["abbreviation"] for t in comp["competitors"] if t["homeAway"] == "away"))
                completed.append({"event_id": event["id"], "home": home, "away": away})
        return completed
    except Exception as e:
        print(f"  Error fetching scoreboard for {game_date}: {e}")
        return []

def fetch_excitement(event_id):
    try:
        r = requests.get(ESPN_SUMMARY_URL, params={"event": event_id}, timeout=10)
        r.raise_for_status()
        wp = r.json().get("winprobability", [])
        return compute_excitement(wp)
    except Exception as e:
        print(f"  Error fetching excitement for event {event_id}: {e}")
        return None

def run_backfill(n_samples=800, output_path="data/backfill_calibration.csv"):
    print("Loading games and model...")
    games = pd.read_parquet("data/games.parquet")
    games["date"] = pd.to_datetime(games["date"])

    with open("data/model.pkl", "rb") as f:
        model = pickle.load(f)

    all_dates = games["date"].dt.strftime("%Y-%m-%d").unique().tolist()
    all_dates = [d for d in all_dates if d >= "2019-01-01"]
    sampled_dates = random.sample(all_dates, min(n_samples // 5, len(all_dates)))
    sampled_dates.sort()
    print(f"Sampling {len(sampled_dates)} dates from {sampled_dates[0]} to {sampled_dates[-1]}")

    rows = []
    total_games = 0
    failed = 0

    for i, game_date in enumerate(sampled_dates):
        print(f"[{i+1}/{len(sampled_dates)}] {game_date}...")
        completed = fetch_completed_games(game_date)
        if not completed:
            continue

        for game in completed:
            home, away = game["home"], game["away"]
            result = predict_game(home, away, game_date, games, model)
            if not result:
                failed += 1
                continue

            excitement = fetch_excitement(game["event_id"])
            if excitement is None:
                failed += 1
                continue

            rows.append({
                "game_date": game_date,
                "home_team": home,
                "away_team": away,
                "predicted": result["watchability"],
                "actual": excitement,
                "delta": round(result["watchability"] - excitement, 2),
            })
            total_games += 1
            time.sleep(0.3)

        if len(rows) >= n_samples:
            break

        time.sleep(0.5)

    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False)
    print(f"\nDone. {total_games} games saved to {output_path}")
    print(f"Failed: {failed}")
    print(f"\nPredicted: min {df['predicted'].min()}, max {df['predicted'].max()}, mean {round(df['predicted'].mean(),2)}, std {round(df['predicted'].std(),2)}")
    print(f"Actual:    min {df['actual'].min()}, max {df['actual'].max()}, mean {round(df['actual'].mean(),2)}, std {round(df['actual'].std(),2)}")
    print(f"Correlation: {round(df['predicted'].corr(df['actual']), 3)}")

if __name__ == "__main__":
    run_backfill()
