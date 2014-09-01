#!/usr/bin/python

import math
import re
import sys

from lxml import etree

from team_database import TeamDatabase

def main(argv):
	db = TeamDatabase(argv[2])

	file = open(argv[1], 'r')
	tree = etree.parse(file, etree.HTMLParser())
	old_ratings = {}
	for tr in tree.find(".//table[@class='global_table']").findall('./tr'):
		tds = tr.findall('./td')
		if len(tds) != 11:
			continue
		id = re.match('.*TeamId=(.*)$', tds[1].find('./a').get('href')).group(1)
		team = db.GetTeam(id)
		rating = int(tds[2].text.strip())
		old_ratings[team] = rating

	# Get a decent rating for the teams that don't have enough games to be included.
	for _ in range(100):
		for team, rating in old_ratings.iteritems():
			team.rating = rating
		db.Iterate()
	
	for team in sorted(old_ratings.keys(), key=lambda t: math.fabs(old_ratings[t] - t.rating)):
		print '%s: %d -> %d' % (team.name, old_ratings[team], team.rating)
	
if __name__ == '__main__':
	main(sys.argv)