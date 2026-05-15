import time
import os
import pandas as pd
from nba_api.stats.endpoints import playbyplayv3

games = pd.read_parquet("data/games.parquet")
game_ids = games["game_id"].unique()

os.makedirs("data/pbp", exist_ok=True)

already_done = set(f.replace(".parquet", "") for f in os.listdir("data/pbp"))
remaining = [g for g in game_ids if g not in already_done]

print(f"Total games: {len(game_ids)}")
print(f"Already done: {len(already_done)}")
print(f"Remaining: {len(remaining)}")

for i, game_id in enumerate(remaining):
    try:
        pbp = playbyplayv3.PlayByPlayV3(game_id=game_id).get_data_frames()[0]
        pbp.to_parquet(f"data/pbp/{game_id}.parquet", index=False)
        if i % 50 == 0:
            print(f"Progress: {i}/{len(remaining)}")
        time.sleep(0.6)
    except Exception as e:
        print(f"Failed {game_id}: {e}")
        time.sleep(2)

print("Done.")