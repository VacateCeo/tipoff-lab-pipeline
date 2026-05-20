import requests
import os
import numpy as np
from datetime import date, timedelta
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

ESPN_SCOREBOARD_URL = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard'
ESPN_SUMMARY_URL = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary'

ESPN_TRICODE_FIX = {
    'GS': 'GSW', 'NO': 'NOP', 'NY': 'NYK', 'SA': 'SAS', 'UTAH': 'UTA', 'WSH': 'WAS',
}

def normalize_tricode(code):
    return ESPN_TRICODE_FIX.get(code, code)

def compute_excitement(win_probabilities):
    if not win_probabilities:
        return None
    probs = [p['homeWinPercentage'] for p in win_probabilities]

    # detect OT by volume of plays (regulation ~400-450, OT adds ~60-80 per period)
    went_ot = len(probs) > 470
    went_double_ot = len(probs) > 540

    cutoff = int(len(probs) * 0.75)
    crunch = probs[cutoff:]
    if not crunch:
        crunch = probs
    crunch_avg_distance = float(np.mean([abs(p - 0.5) for p in crunch]))
    min_wp = float(min(min(probs), 1 - max(probs)))
    excitement = (1 - crunch_avg_distance) * 7 + (1 - min_wp) * 3

    # OT floors
    if went_double_ot:
        excitement = max(excitement, 9.3)
    elif went_ot:
        excitement = max(excitement, 8.5)

    return round(min(10, max(0, excitement)), 2)

def fetch_game_result(event_id):
    try:
        r = requests.get(ESPN_SUMMARY_URL, params={'event': event_id}, timeout=10)
        r.raise_for_status()
        d = r.json()

        comps = d['header']['competitions'][0]
        home_score = None
        away_score = None
        home_tri = None
        away_tri = None

        for team in comps['competitors']:
            tri = normalize_tricode(team['team']['abbreviation'])
            score = int(team['score']) if team['score'] else None
            if team['homeAway'] == 'home':
                home_score = score
                home_tri = tri
            else:
                away_score = score
                away_tri = tri

        wp = d.get('winprobability', [])
        excitement = compute_excitement(wp)
        final_margin = abs(home_score - away_score) if home_score and away_score else None

        return {
            'home_tri': home_tri,
            'away_tri': away_tri,
            'home_score': home_score,
            'away_score': away_score,
            'final_margin': final_margin,
            'actual_excitement': excitement,
        }
    except Exception as e:
        print(f'Error fetching result for event {event_id}: {e}')
        return None

def fetch_completed_games(game_date):
    params = {'dates': game_date.replace('-', '')}
    r = requests.get(ESPN_SCOREBOARD_URL, params=params, timeout=10)
    r.raise_for_status()
    completed = []
    for event in r.json().get('events', []):
        if event['status']['type']['completed']:
            comp = event['competitions'][0]
            home = normalize_tricode(next(t['team']['abbreviation'] for t in comp['competitors'] if t['homeAway'] == 'home'))
            away = normalize_tricode(next(t['team']['abbreviation'] for t in comp['competitors'] if t['homeAway'] == 'away'))
            completed.append({
                'event_id': event['id'],
                'home': home,
                'away': away,
            })
    return completed

def run_results_update(game_date=None):
    if game_date is None:
        game_date = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    print(f'Fetching results for {game_date}...')

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    existing = supabase.table('predictions').select('id,home_team,away_team,watchability').eq('game_date', game_date).execute()
    if not existing.data:
        print('No predictions found for this date.')
        return

    predictions = {(r['home_team'], r['away_team']): r for r in existing.data}
    completed = fetch_completed_games(game_date)

    for game in completed:
        key = (game['home'], game['away'])
        if key not in predictions:
            print(f'  No prediction found for {game["away"]} @ {game["home"]}')
            continue

        result = fetch_game_result(game['event_id'])
        if not result:
            continue

        pred = predictions[key]
        accuracy_delta = None
        if result['actual_excitement'] is not None:
            accuracy_delta = round(float(pred['watchability']) - result['actual_excitement'], 2)

        print(f'  {game["away"]} @ {game["home"]}: predicted {pred["watchability"]}, actual excitement {result["actual_excitement"]}, delta {accuracy_delta}')

        supabase.table('predictions').update({
            'final_home_score': result['home_score'],
            'final_away_score': result['away_score'],
            'final_margin': result['final_margin'],
            'actual_excitement': result['actual_excitement'],
            'accuracy_delta': accuracy_delta,
        }).eq('id', pred['id']).execute()

    print('Done.')

if __name__ == '__main__':
    import sys
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run_results_update(date_arg)
