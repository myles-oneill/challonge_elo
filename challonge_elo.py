#!/usr/bin/env python
# -*- coding: utf-8 -*-
import challonge
import config
from datetime import datetime, timedelta
import json
import mechanize
import os
import re
import time
import trueskill

CACHE = 'cache'
DATE_STR = '%Y-%m-%d'

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


def get_all_tournaments(start_urls):
    tournaments = []

    br = mechanize.Browser()

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

    return tournaments


def json_serial(obj):
    if isinstance(obj, datetime):
        serial = obj.strftime(DATE_STR)
        return serial
    raise TypeError('Type not serializable')

tournaments = get_all_tournaments([
    'http://{}.challonge.com/'.format(config.subdomain),
    'http://challonge.com/users/' + config.subdomain
])

cached_tournaments = set()

if not os.path.exists(CACHE):
    os.makedirs(CACHE)
else:
    cached_tournaments = set(os.listdir(CACHE))

challonge.set_credentials(config.user, config.api_key)

players = {}

# Try to tests matches in order (approximately)
for tournament in tournaments[::-1]:

    if tournament not in cached_tournaments:
        print tournament + ': Getting matches'

        matches = challonge.matches.index(tournament)
        participants = challonge.participants.index(tournament)

        with open(os.path.join(CACHE, tournament), 'w') as f:
            json.dump({'matches': matches, 'participants': participants}, f, default=json_serial)
    else:
        print tournament + ': in cache, skipping'

    with open(os.path.join(CACHE, tournament)) as f:
        raw = json.load(f)
        matches = raw['matches']
        participants = raw['participants']

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

today = datetime.today()
SIX_WEEKS = timedelta(days=6*7)

i = 1
for player in sorted(players, key=lambda name: players[name].rating, reverse=True):
    player = players[player]

    last_played = datetime.strptime(player.last_played, DATE_STR)

    if today - last_played < SIX_WEEKS:
        print '{}. {} ({:.2f}, {:.2f})'.format(i, player.name, player.rating.mu, player.rating.sigma)
        i += 1
