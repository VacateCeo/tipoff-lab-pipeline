import time
import pandas as pd
from nba_api.stats.endpoints import leaguegamefinder

SEASONS = [
    "2015-16", "2016-17", "2017-18", "2018-19", "2019-20",
    "2020-21", "2021-22", "2022-23", "2023-24"
]

all_games = []

for season in SEASONS:
    print(f"Pulling {season}...")
    finder = leaguegamefinder.LeagueGameFinder(
        season_nullable=season,
        season_type_nullable="Regular Season",
        league_id_nullable="00"
    )
    df = finder.get_data_frames()[0]
    all_games.append(df)
    time.sleep(1)

raw = pd.concat(all_games, ignore_index=True)

# separate home and away
home = raw[raw["MATCHUP"].str.contains("vs\.")].copy()
away = raw[raw["MATCHUP"].str.contains("@")].copy()

# rename away columns
away = away.rename(columns={
    "TEAM_ID": "away_id",
    "TEAM_ABBREVIATION": "away_team",
    "PTS": "away_pts",
    "WL": "away_result"
})

home = home.rename(columns={
    "GAME_ID": "game_id",
    "GAME_DATE": "date",
    "TEAM_ID": "home_id",
    "TEAM_ABBREVIATION": "home_team",
    "PTS": "home_pts",
    "WL": "result"
})

# merge home and away on game_id
games = home[["game_id", "date", "home_id", "home_team", "home_pts", "result"]].merge(
    away[["GAME_ID", "away_id", "away_team", "away_pts"]].rename(columns={"GAME_ID": "game_id"}),
    on="game_id",
    how="inner"
)

games.to_parquet("data/games.parquet", index=False)
print(f"Saved {len(games)} games with home and away data")
print(games.head())
print(games.columns.tolist())