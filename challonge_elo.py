#!/usr/bin/env python
import challonge
import config

challonge.set_credentials(config.user, config.api_key)
tournament_id = config.subdomain+'-SDHS27'

matches = challonge.matches.index(tournament_id)
players = challonge.participants.index(tournament_id)

tag = {player['id']: player['name'] for player in players}

for match in matches:
    winner = tag[match['winner-id']]
    player1 = tag[match['player1-id']]
    player2 = tag[match['player2-id']]

    if winner == player1:
        print '{} beat {}'.format(player1, player2)
    else:
        print '{} beat {}'.format(player2, player1)
