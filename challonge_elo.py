#!/usr/bin/env python
import challonge
import config
import pprint
import trueskill

# pp = pprint.PrettyPrinter()

challonge.set_credentials(config.user, config.api_key)

players = {}

tournaments = ['SDHS27', 'SDHS26', 'SDHS25', 'SDHS24', 'SDHS']

for tournament in tournaments:
    tournament_id = config.subdomain + '-' + tournament

    matches = challonge.matches.index(tournament_id)
    participants = challonge.participants.index(tournament_id)

    tag = {}

    for p in participants:
        name = p['name']
        tag[p['id']] = name

        if name not in players:
            players[name] = trueskill.Rating()


    for match in matches:
        winner = tag[match['winner-id']]
        one = tag[match['player1-id']]
        two = tag[match['player2-id']]

        if winner == one:
            players[one], players[two] = trueskill.rate_1vs1(players[one], players[two])
        else:
            players[two], players[one] = trueskill.rate_1vs1(players[two], players[one])

for player in sorted(players, key=players.get, reverse=True):
    print '{}: {}'.format(player, players[player].mu)
