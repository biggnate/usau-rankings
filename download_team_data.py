#!/usr/bin/python

import re
import shutil
import sys
import time
import urllib2

def DownloadData(id, output_prefix):
	print 'Downloading data for id: ' + id
	url = 'http://play.usaultimate.org/teams/events/Eventteam/?TeamId=%s' % id
	output_filename = output_prefix + id

	shutil.copyfileobj(urllib2.urlopen(url), open(output_filename, 'w'))
	time.sleep(5)

def main(args):
	output_dir = args[3]
	if args[1] == 'rankings':
		output_prefix = output_dir + 'TeamId='
	elif args[1] == 'unknown':
		output_prefix = output_dir + 'UnknownTeamId='
	for line in open(args[2], 'r'):
		if args[1] == 'rankings':
			match = re.search(R'href="/teams/events/Eventteam/\?TeamId=([^"]*)">', line)
			if not match:
				continue
			DownloadData(match.group(1), output_prefix)
		elif args[1] == 'unknown':
			DownloadData(line.strip(), output_prefix)
	
main(sys.argv)