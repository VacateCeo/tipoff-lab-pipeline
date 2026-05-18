import pandas as pd
import numpy as np
import sys
sys.path.insert(0, "src")
from build_features import (
    get_rolling_team_stats,
    get_win_streak,
    get_team_star_power,
)


def calculate_watchability(
    spread_abs,
    total,
    is_playoffs=False,
    playoff_game_num=0,
    home_win_pct=0.5,
    away_win_pct=0.5,
    home_win_streak=0,
    away_win_streak=0,
    home_b2b=False,
    away_b2b=False,
    home_rest_days=2,
    away_rest_days=2,
    month=11,
    home_star_power=0,
    away_star_power=0,
):
    # COMPETITIVENESS (50%)
    spread_score = max(0, (10 - spread_abs) / 10)

    # PACE BONUS
    total_score = min(1, max(0, (total - 200) / 40))

    # STAKES
    if is_playoffs:
        stakes_score = 0.5 + (playoff_game_num / 7) * 0.5
    else:
        avg_win_pct = (home_win_pct + away_win_pct) / 2
        stakes_score = avg_win_pct
        if month in [3, 4]:
            stakes_score = min(1, stakes_score + 0.15)

    # MATCHUP QUALITY
    record_parity = 1 - abs(home_win_pct - away_win_pct)
    streak_parity = 1 - min(1, abs(home_win_streak - away_win_streak) / 8)
    star_power = min(1, (home_star_power + away_star_power) / 150)
    matchup_score = (record_parity * 0.4 + streak_parity * 0.3 + star_power * 0.3)

    # WEIGHTED BASE — playoff weighting boosts stakes
    if is_playoffs:
        base = (
            spread_score * 0.50 +
            total_score * 0.10 +
            stakes_score * 0.35 +
            matchup_score * 0.05
        )
    else:
        base = (
            spread_score * 0.50 +
            total_score * 0.15 +
            stakes_score * 0.20 +
            matchup_score * 0.15
        )

    # PENALTIES
    penalty = 0
    tanking = home_win_pct < 0.35 and away_win_pct < 0.35 and month in [3, 4]
    if tanking:
        penalty += 0.15
    if home_b2b:
        penalty += 0.04
    if away_b2b:
        penalty += 0.04
    if abs(home_rest_days - away_rest_days) >= 3:
        penalty += 0.05

    raw = base - penalty
    score = min(10, max(0, raw * 10))
    return round(score, 1), raw, record_parity, tanking, star_power


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

    home_win_pct = home_stats["win_pct"]
    away_win_pct = away_stats["win_pct"]
    home_rest_days = min(home_rest, 7)
    away_rest_days = min(away_rest, 7)
    home_b2b = home_rest <= 1
    away_b2b = away_rest <= 1
    month = game_date.month
    is_playoffs = month in (4, 5, 6)
    playoff_game_num = 0
    spread_abs = abs(spread) if spread is not None else 6.0
    total_val = total if total is not None else 217.0

    home_win_streak = get_win_streak(games_df, home_id, game_date)
    away_win_streak = get_win_streak(games_df, away_id, game_date)
    home_star_power = get_team_star_power(games_df, home_id, game_date)
    away_star_power = get_team_star_power(games_df, away_id, game_date)

    watchability, raw, record_parity, tanking, star_power_norm = calculate_watchability(
        spread_abs=spread_abs,
        total=total_val,
        is_playoffs=is_playoffs,
        playoff_game_num=0,
        home_win_pct=home_win_pct,
        away_win_pct=away_win_pct,
        home_win_streak=home_win_streak,
        away_win_streak=away_win_streak,
        home_b2b=home_b2b,
        away_b2b=away_b2b,
        home_rest_days=home_rest_days,
        away_rest_days=away_rest_days,
        month=month,
        home_star_power=home_star_power,
        away_star_power=away_star_power,
    )

    home_avg_pts = home_stats["avg_pts"]
    away_avg_pts = away_stats["avg_pts"]
    home_avg_pts_allowed = home_stats["avg_pts_allowed"]
    away_avg_pts_allowed = away_stats["avg_pts_allowed"]
    combined_star_power = home_star_power + away_star_power

    positive_reasons = []
    if spread_abs <= 4:
        positive_reasons.append("tight matchup")
    if is_playoffs:
        positive_reasons.append("playoff stakes")
    if combined_star_power > 80:
        positive_reasons.append("star power on display")
    if record_parity > 0.85:
        positive_reasons.append("evenly matched records")
    if home_win_streak >= 4 and away_win_streak >= 4:
        positive_reasons.append("momentum clash")
    if home_avg_pts > 118 and away_avg_pts > 118:
        positive_reasons.append("two elite offenses")
    if home_avg_pts_allowed < 108 and away_avg_pts_allowed < 108:
        positive_reasons.append("defensive battle")
    if is_playoffs and playoff_game_num >= 5:
        positive_reasons.append("must-win urgency")

    negative_reasons = []
    if home_b2b or away_b2b:
        negative_reasons.append("back-to-back fatigue")
    if abs(home_rest_days - away_rest_days) >= 3:
        negative_reasons.append("lopsided rest advantage")
    if spread_abs >= 10:
        negative_reasons.append("potential blowout")
    if home_win_pct < 0.35 and away_win_pct < 0.35:
        negative_reasons.append("tanking matchup")
    if away_win_pct < 0.40:
        negative_reasons.append("weak road team")
    if home_win_pct < 0.40:
        negative_reasons.append("struggling home team")
    if (home_win_streak >= 5 and away_win_streak <= -5) or (away_win_streak >= 5 and home_win_streak <= -5):
        negative_reasons.append("cold vs hot")

    all_reasons = positive_reasons + negative_reasons
    reasons = all_reasons[:3] if all_reasons else ["standard matchup"]

    return {
        "home_team": home_team,
        "away_team": away_team,
        "watchability": watchability,
        "reasons": reasons,
        "raw_score": round(float(raw), 4),
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
    games = pd.read_parquet("data/games.parquet")
    games["date"] = pd.to_datetime(games["date"])

    matchups = [
        ("BOS", "MIA", 5.5, 214.0),
        ("LAL", "GSW", 3.0, 228.0),
        ("DEN", "OKC", 4.0, 220.0),
    ]

    results = predict_today("2024-03-01", matchups, games, model=None)

    print("\nTonight's Watchability Rankings:")
    print("-" * 40)
    for r in results:
        print(f"{r['watchability']:.1f}/10 — {r['away_team']} @ {r['home_team']}")
        print(f"   {', '.join(r['reasons'])}")
        print()
