#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import challonge
import config
from datetime import datetime, timedelta
import json
from mako.template import Template
import mechanize
import os
import re
import trueskill

CACHE = 'cache'
DATE_STR = '%Y-%m-%d'

parser = argparse.ArgumentParser()
parser.add_argument('--html', action='store_true', help='Output to html page')
parser.add_argument('-v', '--verbose', action='store_true', help='Print debug messages')
args = parser.parse_args()

class Player:
    def title(self, name):
        if len(name) == 1:
            return name[0].upper()
        else:
            return name[0].upper() + name[1:]

    def clean_up(self, name):
        name = name.lower()

        # remove the ones that include the classes or #number
        name = re.sub(r'\s*\(.*', '', name)
        name = re.sub(r'#.*', '', name)

        # Gotchas
        corrections = {
            'bloodninja': 'blo0dninja2',
            'justinlaw': 'justinatlaw',
            'swerve': 'djswerve',
            'ravels': 'gravels',
            'ltigre': 'elteegrey',
            'azunin': 'azurin'
        }

        if name in corrections:
            name = corrections[name]

        # Capitalize the first letter in the name
        return self.title(name)

    def old_rating(self):
        if self.previous_rating is not None:
            return self.previous_rating
        else:
            return self.rating

    def __init__(self, participant):
        self.rating = trueskill.Rating()
        self.previous_rating = None
        self.rank = -1
        self.previous_rank = -1
        self.new = False
        self.last_played = participant['created-at']

        self.name = self.clean_up(participant['name'])


def get_all_tournaments(start_urls):
    tournaments = []
    br = mechanize.Browser()

    for start_url in start_urls:
        br.open(start_url)

        if args.verbose:
            print 'Getting all tournament ids for ' + start_url

        done = False
        while not done:
            done = True

            for link in br.links():
                if link.text is not None and 'hearthstone' in link.text.lower():
                    if start_url == start_urls[0]:
                        tournaments.append(config.subdomain + '-' + link.url.replace(start_url, ''))
                    else:
                        tournaments.append(link.url.replace('http://challonge.com/', ''))

                if link.text == 'Next ›':
                    next_button = link
                    done = False
                    break

            if not done:
                br.follow_link(next_button)

    return tournaments


def str2date(s):
    return datetime.strptime(s, DATE_STR)


def json_serial(obj):
    if isinstance(obj, datetime):
        serial = obj.strftime(DATE_STR)
        return serial
    raise TypeError('Type not serializable')

tournament_ids = get_all_tournaments([
    'http://{}.challonge.com/'.format(config.subdomain),
    # 'http://challonge.com/users/' + config.subdomain
])

tournament_ids.append('idnlvvlz')

cached_tournaments = set()

if not os.path.exists(CACHE):
    os.makedirs(CACHE)
else:
    cached_tournaments = set(os.listdir(CACHE))

challonge.set_credentials(config.user, config.api_key)

players = {}
tournaments = {}

for tournament_id in tournament_ids:
    if tournament_id not in cached_tournaments:
        if args.verbose:
            print tournament_id + ': Getting matches'

        matches = challonge.matches.index(tournament_id)
        participants = challonge.participants.index(tournament_id)

        with open(os.path.join(CACHE, tournament_id), 'w') as f:
            json.dump({'matches': matches, 'participants': participants}, f, default=json_serial)
    else:
        if args.verbose:
            print tournament_id + ': in cache, skipping'

    # with open(os.path.join(CACHE, tournament_id)) as f:
    #     raw = json.load(f)

    #     tournaments[tournament_id] = {
    #             'matches': raw['matches'],
    #             'participants': raw['participants']
    #     }

for tournament_id in cached_tournaments:
    with open(os.path.join(CACHE, tournament_id)) as f:
        raw = json.load(f)

        tournaments[tournament_id] = {
            'matches': raw['matches'],
            'participants': raw['participants']
        }

last_updated = None

for n, id in enumerate(sorted(tournaments, key=lambda x: str2date(tournaments[x]['matches'][0]['created-at']))):
    tournament = tournaments[id]
    matches = tournament['matches']
    participants = tournament['participants']

    tag = {}

    for p in participants:
        new_player = Player(p)
        name = new_player.name

        if name not in players:
            players[name] = new_player

            if n == len(tournaments) - 1:
                players[name].new = True
        else:
            players[name].last_played = max(players[name].last_played, new_player.last_played)
            last_updated = new_player.last_played

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

    if n == len(tournaments) - 2:
        for name in players:
            player = players[name]
            player.previous_rating = player.rating

    if n == len(tournaments) - 1 and last_updated is None:
        last_updated = matches[0]['created-at']

active_players = []

i = 1
for player in sorted(players, key=lambda name: players[name].rating, reverse=True):
    player = players[player]

    # Remove inactive players after 6 weeks
    if datetime.today() - str2date(player.last_played) < timedelta(weeks=6):
        player.rank = i
        active_players.append(player)
        i += 1

i = 1
for player in sorted(active_players, key=lambda p: p.old_rating(), reverse=True):
    if not player.new:
        player.previous_rank = i
        i += 1

if not args.html:
    if args.verbose:
        print
        print '=== Results ==='

    for player in active_players:
        print '{}. {} ({:.2f})'.format(player.rank, player.name, player.rating.mu)
else:
    template = Template(filename='template.html')
    print template.render(players=active_players, last_updated=last_updated)
