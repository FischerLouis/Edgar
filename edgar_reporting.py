#!/usr/bin/env python2.7
from bs4 import BeautifulSoup
try: import simplejson as json
except ImportError: import json
import logging
from logging.handlers import RotatingFileHandler
import datetime
import shutil
import os
import zipfile

###### SETUP: DATE
now = datetime.datetime.now()

###### SETUP: LOGGING
# LOGGER (DEBUG)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
# FORMATTER
formatter = logging.Formatter('%(asctime)s :: %(levelname)s :: %(message)s')
# HANDLER -> reporting.log
file_handler = RotatingFileHandler('logs/reporting.log', 'a', 1000000, 1) #Append, 1Mo, 1 backup
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
# HANDLER -> console
steam_handler = logging.StreamHandler()
steam_handler.setLevel(logging.DEBUG)
logger.addHandler(steam_handler)


###### FUNCTION: BUILD IFRAME SUCCESS LIST ######
def get_iframe_url(id, has_set):
	base_uri = 'https://w.soundcloud.com/player/?url=https%3A//api.soundcloud.com/'
	params_uri = '&amp;auto_play=false&amp;hide_related=false&amp;show_comments=true&amp;show_user=true&amp;show_reposts=false&amp;visual=true'
	if has_set == 'True':
		return base_uri + 'playlists/' + str(id) + params_uri
	else:
		return base_uri + 'tracks/' + str(id) + params_uri

###### FUNCTION: BUILD IFRAME SUCCESS LIST ######
def get_iframe(url):
	iframe_file_location = '/var/www/edgar_reporting/html/iframe.html'
	with open(iframe_file_location) as iframe_file:
		iframe_soup = BeautifulSoup(iframe_file, 'html.parser')
		iframe_html = iframe_soup.find('iframe')
		iframe_html['src'] = url #Updating iframe
		return str(iframe_soup);
		
###### FUNCTION: GET EMPTY SUCCESS HTML ######
def get_empty_success_html():
	empty_success_html_location = '/var/www/edgar_reporting/html/empty_success.html'
	with open(empty_success_html_location) as empty_success_html_file:
		empty_success_html_soup = BeautifulSoup(empty_success_html_file, 'html.parser')
		return str(empty_success_html_soup);

###### FUNCTION: GET EMPTY ERROR HTML ######
def get_empty_error_html():
	empty_error_html_location = '/var/www/edgar_reporting/html/empty_error.html'
	with open(empty_error_html_location) as empty_error_html_file:
		empty_error_html_soup = BeautifulSoup(empty_error_html_file, 'html.parser')
		return str(empty_error_html_soup);		

###### FUNCTION: BUILD ZIP ######		
def zipdir(path, ziph):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file))

###### FUNCTION: CREATE ZIP FOR COVERS/SONGS ######		
def get_clean_push_zip(source):
	#GET AND PUSH ZIP
	output_file = '/var/www/edgar_reporting/downloads/' + source + '.zip'
	path_zip = source + '/'
	path_to_clean = '/usr/edgar/workspace/' + source + '/*'
	zipf = zipfile.ZipFile(output_file, 'w')
	zipdir(path_zip, zipf)
	zipf.close()
	#CLEAN FOLDER
	for the_file in os.listdir(path_zip):
		file_path = os.path.join(path_zip, the_file)
		try:
			if os.path.isfile(file_path):
				os.unlink(file_path)
		except Exception, e:
			print e
			
### GET AND PREPARE IFRAMES TO INSERT
logger.info('Edgar, ready for reporting ...')
#DEFINE IFRAME LIST
iframe_success_html = ''
iframe_error_html = ''
#BUILD IFRAME LISTS (SUCCESS & ERROR)
for offset in range(1, 8): #Loop on week files
	daily_date = now - datetime.timedelta(days=offset)
	cur_file_to_open = 'reports/report_' + daily_date.strftime("%Y-%m-%d") + '.json'
	logger.debug('FILE: ' + cur_file_to_open)
	with open(cur_file_to_open) as cur_file:
		cur_daily_report = json.load(cur_file)
		cur_daily_report = json.loads(cur_daily_report)
		for report in cur_daily_report['output']['reports']: #Loop on reports for id
			cur_id = report['id']
			for song in cur_daily_report['output']['songs']: #Loop on songs for has_set
				if song['id'] == report['id']:
					cur_has_set = song['has_set']
			cur_url = get_iframe_url(cur_id, cur_has_set)
			logger.debug('URL BUILT: ' + cur_url)
			if report['download_status'] == 'Success' and report['upload_status'] == 'Success': # Build success list
				iframe_success_html += get_iframe(cur_url)
			else: # Build error list
				iframe_error_html += get_iframe(cur_url)
	shutil.move(cur_file_to_open,'reports/_old/')# CLEAN FOLDER
logger.debug('SUCCESS IFRAME LIST: ' + iframe_success_html)
logger.debug('ERROR IFRAME LIST: ' + iframe_error_html)

### UPDATE HTML REPORT WITH IFRAMES AND LINKS
#GET REPORT
index_file_location = '/var/www/edgar_reporting/index.html'
#index_file_location = 'index.html'
with open(index_file_location, 'r') as report_file:
	report_soup = BeautifulSoup(report_file, 'html.parser')
	div_success = report_soup.find(id="edgar_success_tracks")
	div_success.clear()
	if iframe_success_html != '':#UPDATE SUCCESS
		logger.info('Edgar is updating the success tracks div...')
		div_success.insert(0,iframe_success_html)
	else:
		logger.info('Edgar does not have success tracks to update...')
		div_success.insert(0,get_empty_success_html())
	div_error = report_soup.find(id="edgar_error_tracks")
	div_error.clear()
	if iframe_error_html != '':#UPDATE ERROR
		logger.info('Edgar is updating the error tracks div...')
		div_error.insert(0,iframe_error_html)
	else:
		logger.info('Edgar does not have error tracks to update...')
		div_error.insert(0, get_empty_error_html())
	report_week_date = report_soup.find(id="week_date")
	report_week_date.string = str(now.strftime("%d/%m/%Y"))
	logger.debug('Date of update: ' + str(now.strftime("%d/%m/%Y")))
#WRITE BACK REPORT
with open(index_file_location, 'w') as report_file:
	report_file.write(report_soup.prettify(formatter=None))
	logger.info('Edgar has updated index.html.')

### CLEAN FOLDERS AND TRANSFER SONGS/COVERS
#CREATE ZIPS, PUSH THEM AND CLEAN FOLDER
get_clean_push_zip('covers')
get_clean_push_zip('songs')