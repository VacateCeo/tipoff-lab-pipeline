import requests
from datetime import datetime, timedelta

ESPN_TEAM_SCHEDULE_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_id}/schedule"

TRICODE_TO_ESPN_ID = {
    "ATL": "1", "BOS": "2", "BKN": "17", "CHA": "30", "CHI": "4",
    "CLE": "5", "DAL": "6", "DEN": "7", "DET": "8", "GSW": "9",
    "HOU": "10", "IND": "11", "LAC": "12", "LAL": "13", "MEM": "29",
    "MIA": "14", "MIL": "15", "MIN": "16", "NOP": "3", "NYK": "18",
    "OKC": "25", "ORL": "19", "PHI": "20", "PHX": "21", "POR": "22",
    "SAC": "23", "SAS": "24", "TOR": "28", "UTA": "26", "WAS": "27",
}

ESPN_TRICODE_FIX = {
    "GS": "GSW", "NO": "NOP", "NY": "NYK",
    "SA": "SAS", "UTAH": "UTA", "WSH": "WAS",
}

def normalize_tricode(code):
    return ESPN_TRICODE_FIX.get(code, code)

def get_team_recent_games(tricode, game_date_str):
    team_id = TRICODE_TO_ESPN_ID.get(tricode)
    if not team_id:
        return []
    try:
        url = ESPN_TEAM_SCHEDULE_URL.format(team_id=team_id)
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        events = r.json().get("events", [])
        game_date = datetime.strptime(game_date_str, "%Y-%m-%d").date()
        past_games = []
        for event in events:
            event_date = datetime.fromisoformat(event["date"].replace("Z", "+00:00")).date()
            if event_date < game_date:
                past_games.append(event_date)
        past_games.sort(reverse=True)
        return past_games
    except Exception as e:
        print(f"Schedule fetch failed for {tricode}: {e}")
        return []

def get_rest_stats(tricode, game_date_str):
    past_games = get_team_recent_games(tricode, game_date_str)
    game_date = datetime.strptime(game_date_str, "%Y-%m-%d").date()

    if not past_games:
        return {"rest_days": 7, "b2b": False, "3in4": False}

    last_game = past_games[0]
    rest_days = (game_date - last_game).days

    b2b = rest_days <= 1

    # 3-in-4: played 2+ games in the last 3 days before today
    recent = [g for g in past_games if (game_date - g).days <= 3]
    three_in_four = len(recent) >= 2

    return {
        "rest_days": min(rest_days, 7),
        "b2b": b2b,
        "3in4": three_in_four,
    }

def get_schedule_stats(home_team, away_team, game_date_str):
    home = get_rest_stats(home_team, game_date_str)
    away = get_rest_stats(away_team, game_date_str)
    print(f"  {home_team} rest: {home['rest_days']}d, b2b: {home['b2b']}, 3in4: {home['3in4']}")
    print(f"  {away_team} rest: {away['rest_days']}d, b2b: {away['b2b']}, 3in4: {away['3in4']}")
    return home, away

if __name__ == "__main__":
    home, away = get_schedule_stats("SAS", "OKC", "2026-05-22")
    print("SAS:", home)
    print("OKC:", away)
