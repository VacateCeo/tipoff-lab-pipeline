import pandas as pd
import numpy as np
import pickle
import sys
sys.path.insert(0, "src")
from build_features import get_rolling_team_stats, parse_vegas_date, TEAM_NAME_MAP

FEATURE_COLS = [
    "spread_abs", "total",
    "home_win_pct", "away_win_pct", "win_pct_diff",
    "home_avg_pts", "away_avg_pts", "combined_avg_pts",
    "home_avg_pts_allowed", "away_avg_pts_allowed",
    "home_rest_days", "away_rest_days",
    "home_b2b", "away_b2b",
    "late_season", "month"
]

PHRASE_TEMPLATES = {
    "spread_abs":            ("expected blowout", "expected to be close"),
    "win_pct_diff":          ("mismatched records", "evenly matched teams"),
    "combined_avg_pts":      ("low-scoring styles", "both teams scoring well lately"),
    "home_avg_pts_allowed":  ("home team stingy defense", "home team leaking points"),
    "away_avg_pts_allowed":  ("away team stingy defense", "away team leaking points"),
    "away_win_pct":          ("away team struggling", "strong away team"),
    "home_win_pct":          ("home team struggling", "strong home team"),
    "total":                 ("low Vegas total", "high Vegas total"),
    "late_season":           ("early season game", "late season stakes"),
    "home_b2b":              ("home team fresh", "home team on back-to-back"),
    "away_b2b":              ("away team fresh", "away team on back-to-back"),
}

def predict_game(home_team, away_team, game_date, games_df, model, spread=None, total=None):
    game_date = pd.Timestamp(game_date)

    home_row = games_df[games_df["home_team"] == home_team].head(1)
    away_row = games_df[games_df["away_team"] == away_team].head(1)

    if len(home_row) == 0 or len(away_row) == 0:
        print(f"Could not find team IDs for {home_team} or {away_team}")
        return None

    home_id = home_row["home_id"].values[0]
    away_id = away_row["away_id"].values[0]

    home_stats = get_rolling_team_stats(games_df, home_id, game_date)
    away_stats = get_rolling_team_stats(games_df, away_id, game_date)

    if home_stats is None or away_stats is None:
        print("Not enough historical data for one of the teams")
        return None

    prev_home = games_df[
        ((games_df["home_id"] == home_id) | (games_df["away_id"] == home_id)) &
        (games_df["date"] < game_date)
    ]["date"]
    home_rest = (game_date - prev_home.max()).days if len(prev_home) > 0 else 7

    prev_away = games_df[
        ((games_df["home_id"] == away_id) | (games_df["away_id"] == away_id)) &
        (games_df["date"] < game_date)
    ]["date"]
    away_rest = (game_date - prev_away.max()).days if len(prev_away) > 0 else 7

    spread_abs = abs(spread) if spread is not None else 6.0
    total_val = total if total is not None else 217.0

    win_pct_diff = abs(home_stats["win_pct"] - away_stats["win_pct"])

    features = {
        "spread_abs": spread_abs,
        "total": total_val,
        "home_win_pct": home_stats["win_pct"],
        "away_win_pct": away_stats["win_pct"],
        "win_pct_diff": win_pct_diff,
        "home_avg_pts": home_stats["avg_pts"],
        "away_avg_pts": away_stats["avg_pts"],
        "combined_avg_pts": home_stats["avg_pts"] + away_stats["avg_pts"],
        "home_avg_pts_allowed": home_stats["avg_pts_allowed"],
        "away_avg_pts_allowed": away_stats["avg_pts_allowed"],
        "home_rest_days": min(home_rest, 7),
        "away_rest_days": min(away_rest, 7),
        "home_b2b": int(home_rest <= 1),
        "away_b2b": int(away_rest <= 1),
        "late_season": int(game_date.month >= 2),
        "month": game_date.month,
    }

    X = pd.DataFrame([features])[FEATURE_COLS]
    raw_score = model.predict(X)[0]

    watchability = round(float(np.clip((raw_score + 2.5) / 5.0 * 10, 0, 10)), 1)

    try:
        import shap
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)
        shap_series = pd.Series(shap_values[0], index=FEATURE_COLS)
        top_features = shap_series.abs().nlargest(3).index.tolist()

        reasons = []
        for feat in top_features:
            if feat in PHRASE_TEMPLATES:
                low, high = PHRASE_TEMPLATES[feat]
                reasons.append(high if shap_series[feat] > 0 else low)
    except:
        reasons = ["based on team form and Vegas lines"]

    return {
        "home_team": home_team,
        "away_team": away_team,
        "watchability": watchability,
        "reasons": reasons,
        "raw_score": round(float(raw_score), 4),
    }

def predict_today(game_date, matchups, games_df, model):
    results = []
    for home, away, spread, total in matchups:
        result = predict_game(home, away, game_date, games_df, model, spread, total)
        if result:
            results.append(result)

    results.sort(key=lambda x: x["watchability"], reverse=True)
    return results

if __name__ == "__main__":
    print("Loading model and data...")
    with open("data/model.pkl", "rb") as f:
        model = pickle.load(f)

    games = pd.read_parquet("data/games.parquet")
    games["date"] = pd.to_datetime(games["date"])

    matchups = [
        ("BOS", "MIA", 5.5, 214.0),
        ("LAL", "GSW", 3.0, 228.0),
        ("DEN", "OKC", 4.0, 220.0),
    ]

    results = predict_today("2024-03-01", matchups, games, model)

    print("\nTonight's Watchability Rankings:")
    print("-" * 40)
    for r in results:
        print(f"{r['watchability']:.1f}/10 — {r['away_team']} @ {r['home_team']}")
        print(f"   {', '.join(r['reasons'])}")
        print()