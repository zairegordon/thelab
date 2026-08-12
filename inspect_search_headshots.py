import os
os.environ['POLARS_SKIP_CPU_CHECK'] = '1'
from app import search_active_players
players = search_active_players('Christian')
print('results:', len(players))
for player in players[:10]:
    print(player.name, player.position, player.team, player.headshot_url)
