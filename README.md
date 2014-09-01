Manually save the rankings to rankings.html

Scrape USAU's website for game data for the ranked teams:
- ./download_team_data.py rankings rankings.html data/

Compute rankings, keeping track of unknown team ids:
- ./team_database.py 'data/*TeamId=*' unknown_ids.txt

Scrape data for the new teams:
- ./download_team_data.py unknown unknown_ids.txt data/
