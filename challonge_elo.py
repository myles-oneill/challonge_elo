#!/usr/bin/env python
# -*- coding: utf-8 -*-
import challonge
import config
from datetime import datetime, timedelta
import mechanize
import pytz
import re
import trueskill


class Player:
    def clean_up(self, name):
        name = name.lower()

        # remove the ones that include the classes or #number
        name = re.sub(r'\s*\(.*', '', name)
        name = re.sub(r'#.*', '', name)

        # Gotchas
        corrections = {
            'blo0dninja2': 'bloodninja',
            'justinlaw': 'justinatlaw',
            'swerve': 'djswerve',
            'ravels': 'gravels',
            'azunin': 'azurin'
        }

        if name in corrections:
            name = corrections[name]

        return name

    def __init__(self, participant):
        self.rating = trueskill.Rating()
        self.last_played = participant['created-at']

        self.name = self.clean_up(participant['name'])


tournaments = []

br = mechanize.Browser()

start_urls = [
    'http://{}.challonge.com/'.format(config.subdomain),
    'http://challonge.com/users/showdowngg'
]

for start_url in start_urls:
    br.open(start_url)

    print 'Getting all tournament ids for ' + start_url

    done = False
    while not done:
        done = True

        for link in br.links():
            if 'hearthstone' in link.text.lower():
                if start_url == start_urls[0]:
                    tournaments.append(config.subdomain + '-' + link.url.replace(start_url, ''))
                else:
                    tournaments.append(link.url.replace('http://challonge.com/', ''))

            if link.text == 'Next ›':
                next_button = link
                done = False
                break

        br.follow_link(next_button)

challonge.set_credentials(config.user, config.api_key)

players = {}

# Try to tests matches in order (approximately)
for tournament in tournaments[::-1]:
    print 'Getting matches from tournament: ' + tournament

    matches = challonge.matches.index(tournament)
    participants = challonge.participants.index(tournament)

    tag = {}

    for p in participants:
        new_player = Player(p)
        name = new_player.name

        if name not in players:
            players[name] = new_player
        else:
            players[name].last_played = max(players[name].last_played, new_player.last_played)

        tag[p['id']] = name

    for match in matches:
        if 'winner-id' not in match:
            continue

        if match['winner-id'] not in tag:
            continue

        winner = tag[match['winner-id']]
        one = tag[match['player1-id']]
        two = tag[match['player2-id']]

        if winner == one:
            players[one].rating, players[two].rating = trueskill.rate_1vs1(players[one].rating, players[two].rating)
        else:
            players[two].rating, players[one].rating = trueskill.rate_1vs1(players[two].rating, players[one].rating)

print
print '=== Results ==='

pacific_time = pytz.timezone('US/Pacific')
today = datetime.now(pacific_time)
SIX_WEEKS = timedelta(days=6*7)

i = 1
for player in sorted(players, key=lambda name: players[name].rating, reverse=True):
    player = players[player]

    if today - player.last_played < SIX_WEEKS:
        print '{}. {} ({:.2f}, {:.2f})'.format(i, player.name, player.rating.mu, player.rating.sigma)
        i += 1
