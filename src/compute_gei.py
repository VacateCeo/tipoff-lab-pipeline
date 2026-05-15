import pandas as pd
import numpy as np
import os

def win_prob(margin, seconds_left, spread=0):
    """
    Simple logistic win probability.
    margin: home - away score
    seconds_left: seconds remaining in regulation
    spread: pre-game home spread (negative = home favored)
    """
    time_factor = max(seconds_left, 1) / 2880
    adjusted = margin - spread * time_factor
    scale = 4.5 * np.sqrt(time_factor) + 0.5
    return 1 / (1 + np.exp(-adjusted / scale))

def compute_gei_from_pbp(pbp_df, spread=0):
    """
    Given a play-by-play dataframe, compute Game Excitement Index.
    """
# filter to rows that have a score
    pbp = pbp_df[pbp_df["scoreHome"].astype(str).str.strip() != ""].copy()
    pbp = pbp[pbp["scoreAway"].astype(str).str.strip() != ""].copy()
    if len(pbp) < 10:
        return None
    
    pbp["scoreHome"] = pd.to_numeric(pbp["scoreHome"], errors="coerce")
    pbp["scoreAway"] = pd.to_numeric(pbp["scoreAway"], errors="coerce")
    pbp = pbp.dropna(subset=["scoreHome", "scoreAway"])
    
    # compute margin (home - away)
    pbp["margin"] = pbp["scoreHome"] - pbp["scoreAway"]
    
    # compute seconds left
    def parse_seconds_left(row):
        try:
            period = int(row["period"])
            clock = str(row["clock"])
            # format: PT12M00.00S
            clock = clock.replace("PT", "").replace("S", "")
            parts = clock.split("M")
            mins = float(parts[0])
            secs = float(parts[1])
            period_secs_left = mins * 60 + secs
            if period <= 4:
                return (4 - period) * 720 + period_secs_left
            else:
                return period_secs_left
        except:
            return None
    
    pbp["seconds_left"] = pbp.apply(parse_seconds_left, axis=1)
    pbp = pbp.dropna(subset=["seconds_left"])
    
    if len(pbp) < 10:
        return None
    
    # compute win probability at each play
    pbp["wp"] = pbp.apply(
        lambda r: win_prob(r["margin"], r["seconds_left"], spread), axis=1
    )
    
    # GEI = sum of absolute WP changes, normalized to 48 min game
    wp_changes = pbp["wp"].diff().abs().sum()
    max_seconds = pbp["seconds_left"].iloc[0]
    total_seconds = max(max_seconds, 2880)
    gei = (2880 / total_seconds) * wp_changes
    
    return round(gei, 4)

def main():
    pbp_dir = "data/pbp"
    games = pd.read_parquet("data/games.parquet")
    
    game_ids = [f.replace(".parquet", "") for f in os.listdir(pbp_dir) if f.endswith(".parquet")]
    print(f"Computing GEI for {len(game_ids)} games...")
    
    results = []
    errors = 0
    
    for i, game_id in enumerate(game_ids):
        try:
            pbp = pd.read_parquet(f"{pbp_dir}/{game_id}.parquet")
            gei = compute_gei_from_pbp(pbp)
            if gei is not None:
                results.append({"game_id": game_id, "gei": gei})
        except Exception as e:
            errors += 1
        
        if i % 100 == 0:
            print(f"Progress: {i}/{len(game_ids)}, errors: {errors}")
    
    df = pd.DataFrame(results)
    print(f"\nComputed GEI for {len(df)} games")
    print(f"GEI stats:\n{df['gei'].describe()}")
    print(f"\nTop 10 most exciting games:")
    print(df.nlargest(10, 'gei'))
    
    df.to_parquet("data/gei.parquet", index=False)
    print("Saved to data/gei.parquet")

if __name__ == "__main__":
    main()