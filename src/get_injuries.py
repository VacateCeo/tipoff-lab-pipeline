import requests

ESPN_INJURIES_URL = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries'

ESPN_TEAM_ID_TO_TRICODE = {
    '1': 'ATL', '2': 'BOS', '17': 'BKN', '30': 'CHA', '4': 'CHI',
    '5': 'CLE', '6': 'DAL', '7': 'DEN', '8': 'DET', '9': 'GSW',
    '10': 'HOU', '11': 'IND', '12': 'LAC', '13': 'LAL', '29': 'MEM',
    '14': 'MIA', '15': 'MIL', '16': 'MIN', '3': 'NOP', '18': 'NYK',
    '25': 'OKC', '19': 'ORL', '20': 'PHI', '21': 'PHX', '22': 'POR',
    '23': 'SAC', '24': 'SAS', '28': 'TOR', '26': 'UTA', '27': 'WAS',
}

OUT_STATUSES = {'Out'}
DTD_STATUSES = {'Day-To-Day'}


def get_injuries():
    try:
        r = requests.get(ESPN_INJURIES_URL, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f'Warning: Could not fetch injury report: {e}')
        return {}

    injuries = {}
    for team_entry in r.json().get('injuries', []):
        team_id = team_entry.get('id')
        tricode = ESPN_TEAM_ID_TO_TRICODE.get(str(team_id))
        if not tricode:
            continue

        out_players = []
        dtd_players = []

        for player in team_entry.get('injuries', []):
            status = player.get('status', '')
            name = player.get('athlete', {}).get('displayName', 'Unknown')
            if status in OUT_STATUSES:
                out_players.append(name)
            elif status in DTD_STATUSES:
                dtd_players.append(name)

        if out_players or dtd_players:
            injuries[tricode] = {'out': out_players, 'dtd': dtd_players}
            if out_players:
                print(f"  {tricode} OUT: {', '.join(out_players)}")
            if dtd_players:
                print(f"  {tricode} DTD: {', '.join(dtd_players)}")

    return injuries
