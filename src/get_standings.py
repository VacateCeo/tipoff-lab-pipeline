import requests

ESPN_STANDINGS_URL = "https://site.api.espn.com/apis/v2/sports/basketball/nba/standings"

ESPN_TRICODE_FIX = {
    "GS": "GSW", "NO": "NOP", "NY": "NYK",
    "SA": "SAS", "UTAH": "UTA", "WSH": "WAS",
}

def normalize_tricode(code):
    return ESPN_TRICODE_FIX.get(code, code)

def parse_streak(streak_str):
    if not streak_str:
        return 0
    try:
        direction = 1 if streak_str[0] == "W" else -1
        count = int(streak_str[1:])
        return direction * count
    except:
        return 0

def get_standings():
    r = requests.get(ESPN_STANDINGS_URL, timeout=10)
    r.raise_for_status()
    data = r.json()

    standings = {}

    for conference in data.get("children", []):
        conf_name = conference.get("abbreviation", "")
        entries = conference.get("standings", {}).get("entries", [])

        for entry in entries:
            tricode = normalize_tricode(entry["team"]["abbreviation"])
            stats = {s["name"]: s for s in entry.get("stats", [])}

            def val(key, default=0):
                s = stats.get(key, {})
                raw = s.get("value")
                if raw is not None:
                    return raw
                display = s.get("displayValue", "")
                try:
                    return float(display.replace("+", "").replace("-", "0") if display in ["-", ""] else display)
                except:
                    return default

            win_pct = val("winPercent", 0.5)
            if win_pct > 1:
                win_pct = win_pct / 100

            standings[tricode] = {
                "win_pct": round(float(win_pct), 4),
                "conf_rank": int(val("playoffSeed", 15)),
                "wins": int(val("wins", 0)),
                "losses": int(val("losses", 0)),
                "avg_pts": round(float(val("avgPointsFor", 110)), 2),
                "avg_pts_allowed": round(float(val("avgPointsAgainst", 110)), 2),
                "win_streak": parse_streak(stats.get("streak", {}).get("displayValue", "")),
                "conference": conf_name,
            }

    print(f"Loaded standings for {len(standings)} teams.")
    return standings

if __name__ == "__main__":
    import json
    s = get_standings()
    for team, data in sorted(s.items()):
        print(f"{team}: {data}")
