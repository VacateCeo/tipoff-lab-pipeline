import pandas as pd
import numpy as np
import os

TEAM_NAME_MAP = {
    "Atlanta": "ATL", "Boston": "BOS", "Brooklyn": "BKN", "Charlotte": "CHA",
    "Chicago": "CHI", "Cleveland": "CLE", "Dallas": "DAL", "Denver": "DEN",
    "Detroit": "DET", "GoldenState": "GSW", "Houston": "HOU", "Indiana": "IND",
    "LAClippers": "LAC", "LALakers": "LAL", "Memphis": "MEM", "Miami": "MIA",
    "Milwaukee": "MIL", "Minnesota": "MIN", "NewOrleans": "NOP", "NewYork": "NYK",
    "OklahomaCity": "OKC", "Orlando": "ORL", "Philadelphia": "PHI", "Phoenix": "PHX",
    "Portland": "POR", "Sacramento": "SAC", "SanAntonio": "SAS", "Toronto": "TOR",
    "Utah": "UTA", "Washington": "WAS"
}

def parse_vegas_date(date_str, season_str):
    try:
        date_str = str(int(float(str(date_str)))).zfill(4)
        month = int(date_str[:2])
        day = int(date_str[2:])
        year = int(season_str.split("-")[0].split("\\")[-1].strip())
        if month >= 9:
            actual_year = year
        else:
            actual_year = year + 1
        return pd.Timestamp(year=actual_year, month=month, day=day)
    except:
        return None

def get_rolling_team_stats(games_df, team_id, before_date, n=10):
    team_games = games_df[
        (games_df["home_id"] == team_id) &
        (games_df["date"] < before_date)
    ].tail(n)

    if len(team_games) < 3:
        return None

    avg_pts = team_games["home_pts"].mean()
    win_pct = (team_games["result"] == "W").mean()

    return {
        "avg_pts": avg_pts,
        "win_pct": win_pct,
        "n_games": len(team_games)
    }

def build_features():
    print("Loading data...")
    games = pd.read_parquet("data/games.parquet")
    gei = pd.read_parquet("data/gei.parquet")
    vegas = pd.read_parquet("data/vegas.parquet")

    games["date"] = pd.to_datetime(games["date"])

    vegas["real_date"] = vegas.apply(
        lambda r: parse_vegas_date(r["date"], r["season"]), axis=1
    )
    vegas = vegas.dropna(subset=["real_date"])

    vegas["home_team"] = vegas["home_team"].str.strip().map(TEAM_NAME_MAP)
    vegas = vegas.dropna(subset=["home_team"])

    df = games.merge(gei, on="game_id", how="inner")
    print(f"Games with GEI: {len(df)}")

    df = df.merge(
        vegas[["real_date", "home_team", "spread", "total"]],
        left_on=["date", "home_team"],
        right_on=["real_date", "home_team"],
        how="left"
    )
    print(f"Games with Vegas lines: {df['spread'].notna().sum()}")

    features = []

    for i, row in df.iterrows():
        try:
            game_date = row["date"]
            home_id = row["home_id"]

            home_stats = get_rolling_team_stats(games, home_id, game_date)
            if home_stats is None:
                continue

            prev_home = games[
                (games["home_id"] == home_id) &
                (games["date"] < game_date)
            ]["date"]
            home_rest = (game_date - prev_home.max()).days if len(prev_home) > 0 else 7

            # fix swapped spread/total — spread should be < 30, total should be > 150
            raw_spread = row["spread"] if pd.notna(row["spread"]) else np.nan
            raw_total = row["total"] if pd.notna(row["total"]) else np.nan

            if pd.notna(raw_spread) and pd.notna(raw_total):
                if abs(raw_spread) > 30:
                    raw_spread, raw_total = raw_total, raw_spread

            spread_abs = abs(raw_spread) if pd.notna(raw_spread) else np.nan
            total = raw_total if pd.notna(raw_total) else np.nan

            season_year = game_date.year if game_date.month >= 9 else game_date.year - 1

            f = {
                "game_id": row["game_id"],
                "date": game_date,
                "season_year": season_year,
                "gei": row["gei"],
                "home_win_pct": home_stats["win_pct"],
                "home_avg_pts": home_stats["avg_pts"],
                "home_rest_days": min(home_rest, 7),
                "home_b2b": int(home_rest <= 1),
                "late_season": int(game_date.month >= 2),
                "month": game_date.month,
                "spread_abs": spread_abs,
                "total": total,
            }
            features.append(f)

        except Exception as e:
            continue

        if i % 1000 == 0:
            print(f"Progress: {i}/{len(df)}")

    features_df = pd.DataFrame(features)

    features_df["gei_normalized"] = features_df.groupby("season_year")["gei"].transform(
        lambda x: (x - x.mean()) / x.std()
    )

    print(f"\nBuilt features for {len(features_df)} games")
    print(f"Vegas coverage: {features_df['spread_abs'].notna().sum()} games")
    print(f"Bad spreads remaining: {(features_df['spread_abs'] > 30).sum()}")
    print(f"Bad totals remaining: {(features_df['total'] < 30).sum()}")
    print(f"\nSpread stats:\n{features_df['spread_abs'].describe()}")
    print(f"\nTotal stats:\n{features_df['total'].describe()}")
    features_df.to_parquet("data/features.parquet", index=False)
    print("Saved to data/features.parquet")

if __name__ == "__main__":
    build_features()