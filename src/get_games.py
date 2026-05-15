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

games = pd.concat(all_games, ignore_index=True)

games = games[games["MATCHUP"].str.contains("vs\.")].copy()

games = games[[
    "GAME_ID", "GAME_DATE", "TEAM_ID", "TEAM_ABBREVIATION",
    "MATCHUP", "WL", "PTS"
]].rename(columns={
    "GAME_ID": "game_id",
    "GAME_DATE": "date",
    "TEAM_ID": "home_id",
    "TEAM_ABBREVIATION": "home_team",
    "MATCHUP": "matchup",
    "WL": "result",
    "PTS": "home_pts"
})

games.to_parquet("data/games.parquet", index=False)
print(f"Saved {len(games)} games to data/games.parquet")