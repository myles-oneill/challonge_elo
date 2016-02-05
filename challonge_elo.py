#!/usr/bin/env python
# -*- coding: utf-8 -*-
import challonge
import config
import mechanize
import re
import trueskill


def clean_up(name):
    name = name.lower()

    # remove the ones that include the classes
    name = re.sub(r'\s*\(.*', '', name)

    return name

br = mechanize.Browser()
start_url = 'http://{}.challonge.com/'.format(config.subdomain)
br.open(start_url)

tournaments = []

print 'Getting all tournament ids'

done = False
while not done:
    done = True

    for link in br.links():
        if 'hearthstone' in link.text.lower():
            tournaments.append(link.url.replace(start_url, ''))

        if link.text == 'Next ›':
            next_button = link
            done = False
            break

    br.follow_link(next_button)

challonge.set_credentials(config.user, config.api_key)

players = {}

for tournament in tournaments:
    print 'Getting matches from tournament: ' + tournament

    tournament_id = config.subdomain + '-' + tournament

    matches = challonge.matches.index(tournament_id)
    participants = challonge.participants.index(tournament_id)

    tag = {}

    for p in participants:
        name = clean_up(p['name'])

        # Gotchas
        if name == 'blo0dninja2':
            name = 'bloodninja'
        elif name == 'justinlaw':
            name = 'justinatlaw'

        tag[p['id']] = name

        if name not in players:
            players[name] = trueskill.Rating()


    for match in matches:
        if not 'winner-id' in match:
            continue

        if not match['winner-id'] in tag:
            continue

        winner = tag[match['winner-id']]
        one = tag[match['player1-id']]
        two = tag[match['player2-id']]

        if winner == one:
            players[one], players[two] = trueskill.rate_1vs1(players[one], players[two])
        else:
            players[two], players[one] = trueskill.rate_1vs1(players[two], players[one])

print
print '=== Results ==='

for i, player in enumerate(sorted(players, key=players.get, reverse=True)):
    print '{}. {} ({:.2f}, {:.2f})'.format(i+1, player, players[player].mu, players[player].sigma)
