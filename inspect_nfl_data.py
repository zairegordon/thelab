import nfl_data_py as nfl
import inspect

print('MODULE', nfl.__file__)
for name in dir(nfl):
    lname = name.lower()
    if 'player' in lname or 'headshot' in lname or 'photo' in lname or 'roster' in lname:
        print(name)

print('\nSIGNATURES:')
for name in ['get_player_ids', 'load_players', 'load_rosters', 'player_stats', 'player_info', 'player_urls']:
    if hasattr(nfl, name):
        print(name, inspect.signature(getattr(nfl, name)))
