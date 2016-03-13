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

CACHE = 'cache-melee'
DATE_STR = '%Y-%m-%d'

parser = argparse.ArgumentParser()
parser.add_argument('--html', action='store_true', help='Output MaxPR html file')
parser.add_argument('-v', '--verbose', action='store_true', help='Print debug messages')
args = parser.parse_args()

class Player:
    def clean_up(self, name):
        name = re.sub(r'^.*\s*[\|\.]\s*', '', name)
        return name

    def __init__(self, participant, id):
        self.rating = trueskill.Rating()
        self.previous_rating = None
        self.rank = -1
        self.previous_rank = -1
        self.new = False
        self.last_played = participant['created-at']

        self.name = self.clean_up(participant['name'])
        self.id = id


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
                if 'sf game night' in link.text.lower() and 'hearthstone' not in link.text.lower():
                    if start_url == start_urls[0]:
                        tournaments.append(config.subdomain + '-' + link.url.replace(start_url, ''))

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
])

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

        # Ignore empty results and doubles
        if raw['matches'] and int(tournament_id.replace(config.subdomain+'-SFGameNight', '')) not in [63, 78]:
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
        new_player = Player(p, id)
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

    if n == len(tournaments) - 1 and last_updated is None:
        last_updated = matches[0]['created-at']

if not args.html:
    if args.verbose:
        print
        print '=== Results ==='

    for i, player in enumerate(sorted(players, key=lambda p: players[p].rating, reverse=True)):
        player = players[player]
        print '{}. {} ({}) ({:.2f})'.format(i+1, player.name.encode('utf-8'), player.id, player.rating.mu)
else:
    template = Template(filename='template.html')
    with open('maxpr.html', 'w') as output:
        output.write(template.render(players=players))
