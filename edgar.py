#!/usr/bin/env python2.7
import soundcloud
import youtube_dl
from gmusicapi import Musicmanager, Webclient
import eyed3
import urllib
import logging
import requests
from logging.handlers import RotatingFileHandler
from bs4 import BeautifulSoup
try: import simplejson as json
except ImportError: import json
import datetime

###### FUNCTION: UPDATE RECAP ######
def update_download_reports(status): #CALLED FIRST
	global reports
	if status == 0: #DOWNLOAD SUCCESS
		reports += u'{"download_status":"Success",'
	if status == 1: #DOWNLOAD ERROR
		reports += u'{"download_status":"Error",'
	return;
	
def update_upload_reports(status, id): #CALLED SECOND
	global reports
	if status == 0: #UPLOAD SUCCESS
		reports += u'"id":"' + id + '",'
		reports += u'"upload_status":"Success"' + u'},'
	if status == 1: #UPLOAD ERROR
		reports += u'"id":"' + id + '",'
		reports += u'"upload_status":"Error"' + u'},'
	return;

###### FUNCTION: YOUTUBE-DL DOWNLOAD HOOK ######
def dl_hook(d):
	if d['status'] == 'finished':
		update_download_reports(0)
	if d['status'] == 'error':
		update_download_reports(1)
	return;

###### FUNCTION: YOUTUBE-DL DOWNLOAD ######
def download_and_edit_song( id, artist, title, album, url, cover_url, cover_file ):
	audio_extension = u'.mp3'
	
	#YOUTUBE-DL PARAMETERS
	output_tag = 'songs/' + artist + ' - ' + title + audio_extension
	options = {
		'format': 'bestaudio/best', # choice of quality
		'extractaudio' : True,      # only keep the audio
		'audioformat' : "mp3",      # convert to mp3 
		'outtmpl': output_tag,      # name the file the ID of the video
		'noplaylist' : True,       # only download single song, not playlist
		'logger': logger,
		'progress_hooks': [dl_hook],
	}
	
	#DOWNLOAD
	with youtube_dl.YoutubeDL(options) as ydl:
		ydl.download([url])
		
	#EDIT TEXT META DATA
	cur_song_file = eyed3.load(output_tag)
	if cur_song_file.tag is None:
		cur_song_file.tag = eyed3.id3.Tag()
		cur_song_file.tag.file_info = eyed3.id3.FileInfo(output_tag)
	cur_song_file.tag.title = title
	cur_song_file.tag.artist = artist
	cur_song_file.tag.album = album
	#EDIT FRONT COVER META DATA
	cover_data = urllib.urlopen(cover_url).read()
	cur_song_file.tag.images.set(3,cover_data,"image/jpeg",u"Front cover")
	#SAVE EDIT
	cur_song_file.tag.save(version=(2, 3, 0))
	
	#UPLOAD TO GOOGLE MUSIC
	gmusic_feedback = api.upload(output_tag, False)
	if output_tag in gmusic_feedback[0]:# CHECK IF SUCCESS
		update_upload_reports(0, id)
		#Get Gmusic song ID and update cover through WebClient
		id_gmusic_song = gmusic_feedback[0][output_tag]
		logger.debug('id_gmusic_song: ' + id_gmusic_song + ', cover to be updated.')
		webclient.upload_album_art(id_gmusic_song, cover_file)
	else:
		update_upload_reports(1, id)
	return;
	
###### SETUP: DATE
now = datetime.datetime.now()

###### SETUP: LOGGING
# LOGGER (DEBUG)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
# FORMATTER
formatter = logging.Formatter('%(asctime)s :: %(levelname)s :: %(message)s')
# HANDLER -> activity.log
file_handler = RotatingFileHandler('logs/activity.log', 'a', 1000000, 1) #Append, 1Mo, 1 backup
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
# HANDLER -> console
#steam_handler = logging.StreamHandler()
#steam_handler.setLevel(logging.DEBUG)
#logger.addHandler(steam_handler)

###### SETUP: GOOGLE MUSIC API - MUSICMANAGER
requests.packages.urllib3.disable_warnings()
oauth_file = 'XXX'
mac_address = 'XXX'
api = Musicmanager(True,True,True)
musicmanager_login_status = api.login(oauth_file, mac_address)
logger.debug("Musicmanager login status: " + str(musicmanager_login_status))

###### SETUP: GOOGLE MUSIC API - WEBCLIENT
google_login = 'XXX'
google_passw = 'XXX'
webclient = Webclient(True, True, True)
webclient_login_status = webclient.login(google_login, google_passw)
logger.debug("Webclient login status: " + str(webclient_login_status))

###### BUILD CURRENT SOUNDS LIST AND INFO ######
#GET LIKES PAGE
logger.info('Edgar, reporting for duty ...')
logger.info('Edgar checks songs list on SoundCloud ...')
soundcloud_baseuri = 'https://soundcloud.com'
url_likes = 'https://soundcloud.com/bobytox/likes'
sock = urllib.urlopen(url_likes)
htmlLikesPage = sock.read()
sock.close()
htmlLikesPageSoup = BeautifulSoup(htmlLikesPage, 'html.parser')
##BUILD CURRENT SONGS LIST
soundcloud_client = soundcloud.Client(client_id='118b44c6478d97c39871dedbe7d78ca2')
current_songs_list = u'{"songs":['
for article in htmlLikesPageSoup.findAll('article'):#Get all articles in likes page
	if article.parent.name == 'section':#Get only those with parent "section" = Tracks
		content_url = soundcloud_baseuri + article.a['href']
		logger.debug('Url received: ' + content_url)
		id = u'N/A'
		title = u'N/A'
		artist = u'N/A'
		album = u'N/A'
		cover_url = u'N/A'
		has_set = u'False'
		sets_json = u'N/A'
		#GET DATA
		if 'sets' in content_url:#Playlist: EP, Album...
			has_set = u'True'
			sets_json = u'"sets":['
			sets = soundcloud_client.get('/resolve', url=content_url)
			id = sets.id
			album = sets.title.replace('/','_')
			for track in sets.tracks:
				#GET DATA
				cur_id = track['id']
				cur_title = track['title'].replace('/','_')
				cur_artist = track['user']['username'].replace('/','_')
				cur_album = album
				cur_url = track['permalink_url']
				cur_cover_url = track['artwork_url'].replace('https', 'http', 1).replace('large','t500x500',1)#Cover from HTTP in 't500x500' format
				#BUILD JSON OBJECT
				sets_json += u'{"id":"' + str(cur_id) + u'",'
				sets_json += u'"title":"' + cur_title + u'",'
				sets_json += u'"artist":"' + cur_artist + u'",'
				sets_json += u'"album":"' + cur_album + u'",'
				sets_json += u'"url":"' + cur_url + u'",'
				sets_json += u'"cover_url":"' + cur_cover_url + u'"},'
			sets_json = sets_json[:-1] #Removes last ","
			sets_json += u']'
		else:#Unique track
			has_set = u'False'
			track = soundcloud_client.get('/resolve', url=content_url)
			id = track.id
			title = track.title.replace('/','_')
			artist = track.user['username'].replace('/','_')
			album = artist + ' - SoundCloud' #Default album if track alone
			cover_url = track.artwork_url.replace('https', 'http', 1).replace('large','t500x500',1)#Cover from HTTP in 't500x500' format
		#BUILD JSON OBJECT
		current_songs_list += u'{"id":"' + str(id) + u'",'
		current_songs_list += u'"album":"' + album + u'",'
		if has_set == 'False':
			current_songs_list += u'"title":"' + title + u'",'
			current_songs_list += u'"artist":"' + artist + u'",'
			current_songs_list += u'"cover_url":"' + cover_url + u'",'
		current_songs_list += u'"url":"' + content_url + u'",'
		current_songs_list += u'"has_set":"' + has_set + u'"'
		if has_set == 'True':
			current_songs_list += u',' + sets_json
		current_songs_list += u'},'
current_songs_list = current_songs_list[:-1] #Removes last ","
current_songs_list += u']}'
logger.debug('Current songs list: ' + current_songs_list)

###### COMPARE SONGS LIST TO DOWNLOADED SONGS LIST ######
logger.info('Edgar is checking which songs need to be downloaded ... ')
current_songs_list = json.loads(current_songs_list)

#OPEN ALREADY DOWNLOADED SONGS LIST
with open('downloaded_songs_list.json') as json_file:
    downloaded_songs_list = json.load(json_file)
logger.debug('Downloaded songs list: ' + json.dumps(downloaded_songs_list))
#COMPARE LISTS AND BUILD SONGS TO DOWNLOAD LIST
songs_to_download_list = u'{"songs":['
download_counter = 0
for cur_song in current_songs_list['songs']:
	downloaded = False
	for downloaded_song in downloaded_songs_list['songs']:
		if cur_song['id'] == downloaded_song['id']:
			downloaded = True
	if downloaded == False:
		songs_to_download_list += json.dumps(cur_song)
		songs_to_download_list += u','
		download_counter += 1
if download_counter == 0:
	logger.debug('No new songs.')
	logger.info('Edgar is afraid his work here is done...')
	output = u'{"output":{"reports":[],"songs":[]}}'
else:
	songs_to_download_list = songs_to_download_list[:-1] #Removes last ","	
	songs_to_download_list += u']}'
	logger.debug('Songs to download: ' + songs_to_download_list)

	###### DOWNLOAD, EDIT & UPLOAD SONGS ######
	logger.info('Edgar is starting to download ... ')
	songs_to_download_list = json.loads(songs_to_download_list)
	#PREPARE RECAP
	reports = u'"reports":['
	#PROCESS SONGS
	for songs_to_download in songs_to_download_list['songs']:
		#CHECK IF SET
		dl_has_sets = songs_to_download['has_set']
		if dl_has_sets == u'False':
			#SONG INFO
			dl_id = songs_to_download['id']
			dl_artist = songs_to_download['artist']
			dl_title = songs_to_download['title']
			dl_album = songs_to_download['album']
			dl_url = songs_to_download['url']
			dl_cover_url = songs_to_download['cover_url']
			dl_cover_file = 'covers/' + str(dl_id) + '_' + dl_artist + ' - ' + dl_title + '.jpg'
			urllib.urlretrieve(dl_cover_url, dl_cover_file)#Save cover for future use
			download_and_edit_song(dl_id, dl_artist, dl_title, dl_album, dl_url, dl_cover_url, dl_cover_file)
		else:
			for songs_from_set_to_download in songs_to_download[u'sets']:
				#SONG INFO
				dl_id = songs_from_set_to_download['id']
				dl_artist = songs_from_set_to_download['artist']
				dl_title = songs_from_set_to_download['title']
				dl_album = songs_from_set_to_download['album']
				dl_url = songs_from_set_to_download['url']
				dl_cover_url = songs_from_set_to_download['cover_url']
				dl_cover_file = 'covers/' + str(dl_id) + '_' + dl_artist + ' - ' + dl_title + '.jpg'
				urllib.urlretrieve(dl_cover_url, dl_cover_file)#Save cover for future use
				download_and_edit_song(dl_id, dl_artist, dl_title, dl_album, dl_url, dl_cover_url, dl_cover_file)
	#GENERATE OUTPUT FOR REPORTING
	reports = reports[:-1] #Removes last ","
	reports += u']'
	output = u'{"output":{' + reports + ',' + json.dumps(songs_to_download_list)[1:][:-1] + '}}'
output_filename = 'reports/report_' + now.strftime("%Y-%m-%d") + '.json'
with open(output_filename, 'w') as output_file:
	json.dump(output, output_file)
#REPLACE OLD LIST WITH NEW ONE (downloaded_songs_list = current_songs_list)
with open('downloaded_songs_list.json', 'w') as outfile:
	json.dump(current_songs_list, outfile)
#LOG OUT
webclient.logout()
logger.info('Done! Edgar out!')