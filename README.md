SDHS Elo Ranking
================

This takes all the Hearthstone tournaments from http://showdowngg.challonge.com and takes all the matches and uses [Trueskill](http://trueskill.org/) to calculate an Elo for each player.

With some tweaking it should be able to be used with other tournaments as well.

## Dependencies
- [pychallonge](https://github.com/russ-/pychallonge)
- [TrueSkill](http://trueskill.org)
- [mechanize](https://pypi.python.org/pypi/mechanize/)

## Config

You'll need to create a file called `config.py` in order to use this. A sample one is below. You'll need to get an API key from [here](http://api.challonge.com/v1).

    user: '<challonge username>'
    api_key: '<API key>'
    subdomain: '<challonge subdomain. I used showdowngg for this>'
