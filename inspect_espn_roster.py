import json
import requests

url = 'https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/1/roster'
resp = requests.get(url, timeout=20)
resp.raise_for_status()
data = resp.json()
print('top_keys', list(data.keys()))
athletes = data.get('athletes', [])
print('athletes len', len(athletes))
for group_idx, group in enumerate(athletes[:2]):
    print('group', group_idx, 'keys', list(group.keys()))
    for item in group.get('items', [])[:3]:
        print('item keys', list(item.keys()))
        print('fullName', item.get('fullName'))
        print('displayName', item.get('displayName'))
        print('displayPosition', item.get('displayPosition'))
        print('position', item.get('position'))
        print('team', item.get('team'))
        print('headshot top', item.get('headshot'))
        athlete = item.get('athlete', {})
        print('athlete keys', list(athlete.keys()) if isinstance(athlete, dict) else type(athlete))
        print('athlete headshot', athlete.get('headshot') if isinstance(athlete, dict) else None)
        print('athlete images', athlete.get('images') if isinstance(athlete, dict) else None)
        print('---')
print('sample athlete item json')
print(json.dumps(athletes[0]['items'][0], default=str, indent=2)[:4000])
