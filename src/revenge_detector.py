import os
import requests
from datetime import date
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
ESPN_ROSTER_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_id}/roster"
ESPN_TRANSACTIONS_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/transactions"

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

FULL_NAME_TO_TRICODE = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "Los Angeles Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA", "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP", "New York Knicks": "NYK", "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC", "San Antonio Spurs": "SAS",
    "Toronto Raptors": "TOR", "Utah Jazz": "UTA", "Washington Wizards": "WAS",
}


def normalize_tricode(code):
    return ESPN_TRICODE_FIX.get(code, code)


def get_todays_games(game_date=None):
    params = {}
    if game_date:
        params["dates"] = game_date.replace("-", "")
    r = requests.get(ESPN_SCOREBOARD_URL, params=params, timeout=10)
    r.raise_for_status()
    matchups = []
    for event in r.json().get("events", []):
        comp = event["competitions"][0]
        home = away = None
        for team in comp["competitors"]:
            tri = normalize_tricode(team["team"]["abbreviation"])
            if team["homeAway"] == "home":
                home = tri
            else:
                away = tri
        if home and away:
            matchups.append((home, away))
    return matchups


def get_roster(tricode):
    team_id = TRICODE_TO_ESPN_ID.get(tricode)
    if not team_id:
        return []
    url = ESPN_ROSTER_URL.format(team_id=team_id)
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        players = []
        for athlete in r.json().get("athletes", []):
            for a in (athlete.get("items") or [athlete]):
                name = a.get("fullName") or a.get("displayName")
                if name:
                    players.append(name)
        return players
    except Exception as e:
        print(f"Roster fetch failed for {tricode}: {e}")
        return []


def get_recent_transactions():
    try:
        r = requests.get(ESPN_TRANSACTIONS_URL, timeout=10)
        r.raise_for_status()
        return r.json().get("transactions", [])
    except Exception as e:
        print(f"Transactions fetch failed: {e}")
        return []


def find_revenge_players(home, away, transactions):
    revenge = []
    both_teams = {home, away}
    for tx in transactions:
        player_name = tx.get("athlete", {}).get("displayName") or tx.get("athlete", {}).get("fullName")
        if not player_name:
            continue
        from_team = FULL_NAME_TO_TRICODE.get(tx.get("fromTeam", {}).get("displayName", ""))
        to_team = FULL_NAME_TO_TRICODE.get(tx.get("toTeam", {}).get("displayName", ""))
        if not from_team or not to_team:
            continue
        # Player traded away from one of today's teams, now plays for the other
        if from_team in both_teams and to_team in both_teams and from_team != to_team:
            revenge.append({
                "player": player_name,
                "old_team": from_team,
                "new_team": to_team,
                "type": "traded",
            })
    return revenge


def score_revenge(player_name, old_team, supabase):
    """Look up historical performance vs old team from completed games in Supabase."""
    try:
        # We don't have per-player game logs yet, so return a base score
        # This will be enhanced in a future iteration
        return {
            "games": 0,
            "avg_pts": None,
            "avg_plus_minus": None,
            "score": 5.0,
        }
    except Exception as e:
        print(f"Score lookup failed for {player_name}: {e}")
        return {"games": 0, "avg_pts": None, "avg_plus_minus": None, "score": 5.0}


def run_revenge_detector(game_date=None):
    if game_date is None:
        game_date = date.today().strftime("%Y-%m-%d")
    print(f"Running revenge detector for {game_date}...")

    matchups = get_todays_games(game_date)
    if not matchups:
        print("No games today.")
        return

    print(f"Found {len(matchups)} games.")
    transactions = get_recent_transactions()
    print(f"Fetched {len(transactions)} recent transactions.")

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    supabase.table("revenge_games").delete().eq("game_date", game_date).execute()

    rows = []
    for home, away in matchups:
        revenge_players = find_revenge_players(home, away, transactions)
        if not revenge_players:
            print(f"  {away} @ {home}: no revenge angle")
            continue
        for rp in revenge_players:
            stats = score_revenge(rp["player"], rp["old_team"], supabase)
            rows.append({
                "game_date": game_date,
                "home_team": home,
                "away_team": away,
                "revenge_player": rp["player"],
                "revenge_coach": None,
                "revenge_type": rp["type"],
                "old_team": rp["old_team"],
                "new_team": rp["new_team"],
                "games_vs_old_team": stats["games"],
                "avg_pts_vs_old_team": stats["avg_pts"],
                "avg_plus_minus_vs_old_team": stats["avg_plus_minus"],
                "revenge_score": stats["score"],
            })
            print(f"  REVENGE: {rp['player']} ({rp['new_team']}) vs old team {rp['old_team']}")

    if rows:
        supabase.table("revenge_games").insert(rows).execute()
        print(f"Saved {len(rows)} revenge games to Supabase.")
    else:
        print("No revenge games found today.")


if __name__ == "__main__":
    run_revenge_detector()
