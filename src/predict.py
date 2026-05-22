import pandas as pd
import numpy as np
import sys
sys.path.insert(0, "src")
from build_features import (
    get_rolling_team_stats,
    get_win_streak,
    get_team_star_power,
    get_team_star_names,
)


def calculate_watchability(
    spread_abs,
    total,
    is_playoffs=False,
    playoff_game_num=0,
    playoff_round=None,
    elimination_game=False,
    home_win_pct=0.5,
    away_win_pct=0.5,
    home_win_streak=0,
    away_win_streak=0,
    home_b2b=False,
    away_b2b=False,
    home_rest_days=2,
    away_rest_days=2,
    home_3in4=False,
    away_3in4=False,
    month=11,
    home_star_power=0,
    away_star_power=0,
    home_top_star_avg=0,
    away_top_star_avg=0,
    home_avg_pts=110,
    away_avg_pts=110,
    home_conf_rank=15,
    away_conf_rank=15,
    home_stars_out=0,
    away_stars_out=0,
    home_stars_dtd=0,
    away_stars_dtd=0,
):
    badges = []
    combined_star_power = home_star_power + away_star_power
    record_parity = 1 - abs(home_win_pct - away_win_pct)
    avg_win_pct = (home_win_pct + away_win_pct) / 2

    # POSITIVE BADGES - only one round-tier badge fires
    if playoff_round == "Finals":
        badges.append(("NBA Finals", 3.0))
    elif playoff_round in ("ECF", "WCF"):
        badges.append(("conference finals", 2.5))
    elif elimination_game:
        badges.append(("elimination game", 2.0))
    elif is_playoffs and playoff_game_num >= 5:
        badges.append(("must-win urgency", 2.5))
    elif is_playoffs:
        badges.append(("playoff stakes", 2.0))

    if spread_abs <= 3:
        badges.append(("pick-em game", 2.0))
    elif spread_abs <= 5:
        badges.append(("tight spread", 1.5))
    elif spread_abs <= 7:
        badges.append(("competitive spread", 0.8))

    if combined_star_power > 140:
        badges.append(("star power matchup", 1.5))
    elif combined_star_power > 100:
        badges.append(("quality stars", 0.8))

    if max(home_top_star_avg, away_top_star_avg) >= 28:
        badges.append(("MVP candidate", 1.0))

    if home_conf_rank <= 2 and away_conf_rank <= 2:
        badges.append(("top-2 matchup", 1.5))

    if home_avg_pts >= 118 and away_avg_pts >= 118:
        badges.append(("high-pace shootout", 1.0))

    if record_parity > 0.85 and avg_win_pct > 0.50:
        badges.append(("evenly matched", 1.2))

    if home_win_streak >= 4 and away_win_streak >= 4:
        badges.append(("momentum clash", 1.2))

    if home_win_pct > 0.55 and away_win_pct > 0.55:
        badges.append(("two good teams", 1.0))

    if month in [3, 4] and not is_playoffs and avg_win_pct > 0.50:
        badges.append(("playoff race", 1.0))

    # NEGATIVE BADGES
    if home_stars_out >= 2 or away_stars_out >= 2:
        badges.append(("multiple stars out", -2.5))
    elif home_stars_out >= 1 or away_stars_out >= 1:
        badges.append(("star player out", -1.5))

    if home_stars_dtd >= 1 or away_stars_dtd >= 1:
        badges.append(("star questionable", -0.5))

    if spread_abs >= 15:
        badges.append(("garbage time likely", -2.5))
    elif spread_abs >= 12:
        badges.append(("potential blowout", -1.8))
    elif spread_abs >= 9:
        badges.append(("lopsided matchup", -1.0))

    if home_win_pct < 0.35 and away_win_pct < 0.35 and month in [3, 4]:
        badges.append(("tanking matchup", -1.5))

    if home_b2b or away_b2b:
        badges.append(("back-to-back fatigue", -0.8))

    if home_3in4 or away_3in4:
        badges.append(("3rd in 4 nights", -0.6))

    if abs(home_rest_days - away_rest_days) >= 3:
        badges.append(("rest disadvantage", -0.6))

    # SCORE
    base = 5.0
    total_adjustment = sum(w for _, w in badges)
    raw_score = base + total_adjustment
    score = round(min(10, max(1, raw_score)), 1)

    positive = sorted([(b, w) for b, w in badges if w > 0], key=lambda x: -x[1])
    negative = sorted([(b, w) for b, w in badges if w < 0], key=lambda x: x[1])
    top_badges = [b for b, _ in (positive + negative)[:3]]
    all_badges = [b for b, _ in (positive + negative)]

    return score, raw_score, record_parity, (home_win_pct < 0.35 and away_win_pct < 0.35 and month in [3, 4]), min(1, combined_star_power / 150), top_badges, all_badges


def predict_game(home_team, away_team, game_date, games_df, model, spread=None, total=None, playoff_game_num=0, team_injuries={}):
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
    spread_abs = abs(spread) if spread is not None else 6.0
    default_total = 210.0 if is_playoffs else 217.0
    total_val = total if total is not None else default_total

    home_win_streak = get_win_streak(games_df, home_id, game_date)
    away_win_streak = get_win_streak(games_df, away_id, game_date)
    home_star_power = get_team_star_power(games_df, home_id, game_date)
    away_star_power = get_team_star_power(games_df, away_id, game_date)
    home_star_names = get_team_star_names(games_df, home_id, game_date)
    away_star_names = get_team_star_names(games_df, away_id, game_date)
    home_injured = team_injuries.get(home_team, {})
    away_injured = team_injuries.get(away_team, {})
    all_out = set(home_injured.get('out', []) + away_injured.get('out', []))
    all_dtd = set(home_injured.get('dtd', []) + away_injured.get('dtd', []))

    def match_injury(star_names, injury_set):
        count = 0
        for name, avg in star_names:
            if avg >= 14:
                for injured_name in injury_set:
                    injured_parts = injured_name.lower().split()
                    if any(part in name.lower() for part in injured_parts):
                        count += 1
                        break
        return count

    home_stars_out = match_injury(home_star_names, all_out)
    away_stars_out = match_injury(away_star_names, all_out)
    home_stars_dtd = match_injury(home_star_names, all_dtd)
    away_stars_dtd = match_injury(away_star_names, all_dtd)

    # 3-in-4 nights detection
    def games_in_last_n_days(team_id, n):
        cutoff = game_date - pd.Timedelta(days=n)
        return len(games_df[
            ((games_df["home_id"] == team_id) | (games_df["away_id"] == team_id)) &
            (games_df["date"] < game_date) &
            (games_df["date"] >= cutoff)
        ])

    home_3in4 = games_in_last_n_days(home_id, 4) >= 2
    away_3in4 = games_in_last_n_days(away_id, 4) >= 2

    # Top star avg (highest scorer on each team)
    home_top_star_avg = max([avg for _, avg in home_star_names], default=0)
    away_top_star_avg = max([avg for _, avg in away_star_names], default=0)

    # Avg pts (from rolling stats)
    home_avg_pts = home_stats["avg_pts"]
    away_avg_pts = away_stats["avg_pts"]

    # Conference rank (simplified - rank by win pct within last season)
    # For now use a rough proxy: top 2 = win_pct > 0.65, otherwise default to 15
    home_conf_rank = 1 if home_win_pct >= 0.70 else (2 if home_win_pct >= 0.62 else 15)
    away_conf_rank = 1 if away_win_pct >= 0.70 else (2 if away_win_pct >= 0.62 else 15)

    # Playoff round detection - simple month-based rules
    # Finals: June (or very late May with low game num)
    # Conf Finals: mid-to-late May
    # Earlier rounds: April through early May
    playoff_round = None
    if is_playoffs:
        if month == 6:
            playoff_round = "Finals"
        elif month == 5 and game_date.day >= 14:
            playoff_round = "WCF"  # conference finals (treated same as ECF)

    # Elimination game - we don't have series state available, leave False for now
    elimination_game = False

    watchability, raw, record_parity, tanking, star_power_norm, reasons, all_badges = calculate_watchability(
        spread_abs=spread_abs,
        total=total_val,
        is_playoffs=is_playoffs,
        playoff_game_num=playoff_game_num,
        playoff_round=playoff_round,
        elimination_game=elimination_game,
        home_win_pct=home_win_pct,
        away_win_pct=away_win_pct,
        home_win_streak=home_win_streak,
        away_win_streak=away_win_streak,
        home_b2b=home_b2b,
        away_b2b=away_b2b,
        home_rest_days=home_rest_days,
        away_rest_days=away_rest_days,
        home_3in4=home_3in4,
        away_3in4=away_3in4,
        month=month,
        home_star_power=home_star_power,
        away_star_power=away_star_power,
        home_top_star_avg=home_top_star_avg,
        away_top_star_avg=away_top_star_avg,
        home_avg_pts=home_avg_pts,
        away_avg_pts=away_avg_pts,
        home_conf_rank=home_conf_rank,
        away_conf_rank=away_conf_rank,
        home_stars_out=home_stars_out,
        away_stars_out=away_stars_out,
        home_stars_dtd=home_stars_dtd,
        away_stars_dtd=away_stars_dtd,
    )

    if not reasons:
        reasons = ["standard matchup"]

    return {
        "home_team": home_team,
        "away_team": away_team,
        "watchability": watchability,
        "reasons": reasons,
        "badges": all_badges,
        "raw_score": round(float(raw), 4),
    }


def predict_today(game_date, matchups, games_df, model, team_injuries={}):
    results = []
    for home, away, spread, total, playoff_game_num in matchups:
        result = predict_game(home, away, game_date, games_df, model, spread, total, playoff_game_num, team_injuries)
        if result:
            results.append(result)

    results.sort(key=lambda x: x["watchability"], reverse=True)
    return results


if __name__ == "__main__":
    games = pd.read_parquet("data/games.parquet")
    games["date"] = pd.to_datetime(games["date"])

    matchups = [
        ("BOS", "MIA", 5.5, 214.0, 0),
        ("LAL", "GSW", 3.0, 228.0, 0),
        ("DEN", "OKC", 4.0, 220.0, 0),
    ]

    results = predict_today("2024-03-01", matchups, games, model=None)

    print("\nTonight's Watchability Rankings:")
    print("-" * 40)
    for r in results:
        print(f"{r['watchability']:.1f}/10 - {r['away_team']} @ {r['home_team']}")
        print(f"   {', '.join(r['reasons'])}")
        print()
