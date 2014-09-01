#!/usr/bin/python

import datetime
import glob
import math
import re
import sys
import time

from lxml import etree

_YEAR = 2014
# Technically, it's June 7. This is the previous Wednesday.
_START_DATE = datetime.date(2014, 6, 4)
# Technically, it's August 31. This is the following Wednesday.
_END_DATE = datetime.date(2014, 9, 3)
_DEFAULT_RATING = 1000.0
_MIN_NON_IGNORED_GAMES = 5

class TeamDatabase:
	def __init__(self, pattern):
		self._teams = {}
		self._unknown_ids = set()
		for filename in glob.glob(pattern):
			m = re.search('TeamId=(.*)$', filename)
			id = m.group(1)
			self._teams[id] = Team(filename, self)
		for team in self._teams.values():
			team.Init()

	@property			
	def teams(self):
		return self._teams.values()
		
	@property
	def unknown_ids(self):
		return self._unknown_ids

	def GetTeam(self, id):
		return self._teams.get(id)

	def AddUnknownId(self, id):
		self._unknown_ids.add(id)

	def Iterate(self):
		max_difference = 0.0
		new_ratings = {}
		for team in self.teams:
			team.ClearIgnoredGames()
		for team in sorted(self.teams, key=lambda x: -x.rating):
			new_ratings[team] = team.GetNextRating()
		for team, rating in new_ratings.iteritems():
			max_difference = max(max_difference, math.fabs(team.rating - rating))
			team.rating = rating
		return max_difference
			
class Team:
	def __init__(self, data_filename, db):
		self._data_filename = data_filename
		self._db = db
		self._name = ''
		self._games = []
		self._rating = _DEFAULT_RATING

	def Init(self):
		file = open(self._data_filename, 'r')
		tree = etree.parse(file, etree.HTMLParser())
		self._name = tree.find(".//span[@id='CT_Right_1_lblHeading']").text.encode('utf-8')
		
		schedule_table = tree.findall(".//table[@class='schedule_table']")[-1]
		tournament = 'Unknown'
		for tr in schedule_table.findall("./tr"):
			tds = tr.findall("./td")
			if len(tds) == 1:
				a = tds[0].find("./span/a")
				if a is None:
					continue
				tournament = a.text.encode('utf-8')
				continue
			# YCC's don't count?
			if tournament == 'Youth Club Championships':
				continue
			
			assert len(tds) == 3
			
			span = tds[0].find("./span")
			if span is None:
				continue
			tm = time.strptime(span.text, "%B %d")
			date = datetime.date(_YEAR, tm.tm_mon, tm.tm_mday)

			a = tds[1].find("./span/a")
			if a is None or a.text is None:
				continue
			match = re.match(r'(\d+) - (\d+)', a.text)
			if not match:
				continue
			points = int(match.group(1))
			opponent_points = int(match.group(2))
			assert points != opponent_points
			if (points < opponent_points):
				continue
			
			a = tds[2].find("./span/a")
			if a is None:
				continue
			match = re.match(".*TeamId=(.*)$", a.get('href'))
			if not match:
				continue
			id = match.group(1)
			opponent = self._db.GetTeam(id)
			if not opponent:
				self._db.AddUnknownId(id)
				continue

			game = Game(tournament, date, self, opponent, points, opponent_points)
			self._games.append(game)
			opponent._games.append(game)

	@property
	def name(self):
		return self._name
		
	@property
	def rating(self):
		return self._rating
		
	@rating.setter
	def rating(self, value):
		self._rating = value
		
	@property
	def games(self):
		return self._games
		
	def ClearIgnoredGames(self):
		for game in self._games:
			game.ignored = False
	
	def GetNextRating(self):
		def may_ignore(game):
			# We can't choose to ignore the game if we're the loser.
			return game.MayIgnore() and game.IsWinner(self)
		def key(game):
			# Put games that we want to ignore at the end. That means if we can't choose
			# whether to ignore the game, it goes at the very beginning.
			if not may_ignore(game):
				return None
			# The impact of the game is proportional to the weight times the rating
			# difference.
			return game.weight * (self.rating - game.GetRating(self))
		total_rating = 0.0
		total_weight = 0.0
		num_games = 0
		for game in sorted(self._games, key=key):
			if num_games >= _MIN_NON_IGNORED_GAMES and may_ignore(game):
				game.ignored = True
			if game.ignored:
				continue
			weight = game.weight
			if weight == 0.0:
				continue
			num_games += 1
			total_weight += weight
			total_rating += weight * game.GetRating(self)
		if num_games == 0:
			return _DEFAULT_RATING
		return total_rating / total_weight
		
class Game:
	def __init__(self, tournament, date, winner, loser, winner_points, loser_points):
		self._tournament = tournament
		self._date = date
		self._winner = winner
		self._loser = loser
		self._winner_points = winner_points
		self._loser_points = loser_points
		self._ignored = False
	
	@property
	def tournament(self):
		return self._tournament

	@property
	def date(self):
		return self._date
		
	@property
	def ignored(self):
		return self._ignored

	@ignored.setter
	def ignored(self, value):
		self._ignored = value
	
	def IsWinner(self, team):
		if team == self._winner:
			return True
		else:
			assert team == self._loser
			return False
	
	def GetOpponent(self, team):
		if self.IsWinner(team):
			return self._loser
		else:
			return self._winner
		
	def GetScore(self, team):
		if self.IsWinner(team):
			return (self._winner_points, self._loser_points)
		else:
			return (self._loser_points, self._winner_points)

	def MayIgnore(self):
		return (self._winner.rating > self._loser.rating + 600.0 and
				self._winner_points > self._loser_points * 2 + 1)
				
	def GetRating(self, team):
		r = self._loser_points / (self._winner_points - 1.0)
		if r >= 0.5:
			s = 2.0 * (1.0 - r)
		else:
			s = 1.0
		difference = 125.0 + 475.0 * math.sin(s * 0.4 * math.pi) / math.sin(0.4 * math.pi)
		if not self.IsWinner(team):
			difference = -difference
		return self.GetOpponent(team).rating + difference

	@property
	def weight(self):
		num_weeks = (_END_DATE - _START_DATE).days / 7
		day = (self._date - _START_DATE).days
		if day < 0:
			return 0.0
		assert day % 7 != 0  # Wednesday games would be ambiguous ...
		week = day / 7
		if week >= num_weeks:
			return 0.0
		# The weight of a game is c * k^w, where c and k are constants and w is the week
		# number. For week 0, we need a weight of 0.5, so c = 0.5. For the last week, we
		# need a weight of 1.0, so 0.5 * k^(num_weeks - 1) = 1.0
		k = 2.0 ** (1.0 / (num_weeks - 1))
		return 0.5 * (k ** week)

def main(args):
	db = TeamDatabase(args[1])
	i = 0
	while True:
		max_difference = db.Iterate()
		i += 1
		print '%d: %f' % (i, max_difference)
		if max_difference < 0.0001:
			break
	for team in sorted(db.teams, key=lambda t: t.rating):
		print team.name, team.rating
	if len(args) > 2:
		ids_file = open(args[2], 'w')
		for id in db.unknown_ids:
			ids_file.write('%s\n' % id)

if __name__ == '__main__':
	main(sys.argv)