import json
import requests

try:
    import nflreadpy
    print('nflreadpy import ok')
except Exception as exc:
    print('nflreadpy import failed:', exc)
    raise

try:
    df = nflreadpy.load_players()
    print('loaded df type:', type(df))
    print('columns:', getattr(df, 'columns', None))
    if hasattr(df, 'to_dicts'):
        recs = df.to_dicts()
    elif hasattr(df, 'to_dict'):
        recs = df.to_dict(orient='records')
    else:
        recs = [dict(r) for r in df]
    print('records count:', len(recs))
    if recs:
        print('record 0 keys:', list(recs[0].keys()))
        print('record 0 sample:', json.dumps(recs[0], default=str)[:2000])
except Exception as exc:
    print('failed loading nflreadpy data:', exc)
    raise

try:
    url = 'https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/1/roster'
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    data = r.json()
    print('\nESPN roster keys:', list(data.keys()))
    athletes = data.get('athletes', [])
    print('athletes count:', len(athletes))
    for gidx, athlete_group in enumerate(athletes[:2]):
        print('group', gidx, 'keys', list(athlete_group.keys()))
        for item in athlete_group.get('items', [])[:2]:
            print('item keys:', list(item.keys()))
            print('fullName', item.get('fullName'), 'displayName', item.get('displayName'))
            print('displayPosition', item.get('displayPosition'), 'position', item.get('position'))
            print('team', item.get('team'))
            print('headshot field', item.get('headshot'))
            print('athlete headshot', item.get('athlete', {}).get('headshot'))
            print('athlete images', item.get('athlete', {}).get('images'))
            print('row raw sample', json.dumps(item, default=str)[:1000])
            print('---')
except Exception as exc:
    print('failed fetching roster data:', exc)
    raise
