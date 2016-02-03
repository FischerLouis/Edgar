#!/usr/bin/env python2.7
import soundcloud
import youtube_dl
from gmusicapi import Musicmanager, Webclient
import eyed3
import urllib
import logging
import requests
from logging.handlers import RotatingFileHandler
try: import simplejson as json
except ImportError: import json
import datetime

###################################################
###												###
###					FUNCTIONS					###
###												###
###################################################

### FUNCTION: YOUTUBE-DL DOWNLOAD HOOK ###
#TRACK REPORTING ERROR
def dl_hook_track(d):
	if d['status'] == 'error':
		cur_id = d['filename'].split('/')[1].split('.')[0] #GET ID FROM FILE NAME
		if(cur_id not in reporting_tracks_error):
			reporting_tracks_error.append(cur_id)
	return;
#PLAYLIST REPORTING ERROR
def dl_hook_playlist(d):
	if d['status'] == 'error':
		cur_id = d['filename'].split('/')[1].split('.')[0] #GET ID FROM FILE NAME
		if(cur_id not in reporting_playlists_error):
			reporting_playlists_error.append(cur_id)
	return;

### FUNCTION: YOUTUBE-DL DOWNLOAD ###
def download_upload(id, artist, title, album, url, cover_url, type, parent_id):
	
	#COVER DOWNLOAD
	cover_url = cover_url.replace('https://','http://') #AVOID SSL ISSUES
	cover_file = 'covers/' + str(id) + '.jpg'
	urllib.urlretrieve(cover_url, cover_file)#Save cover for future use

	#AUDIO PARAMS
	audio_extension = u'.mp3'
	
	#YOUTUBE-DL PARAMETERS
	output_tag = 'songs/' + str(id) + audio_extension
	# TRACK PARAMETER
	if (type == 'track'):
		options = {
			'format': 'bestaudio/best', # choice of quality
			'extractaudio' : True,      # only keep the audio
			'audioformat' : "mp3",      # convert to mp3 
			'outtmpl': output_tag,      # name the file the ID of the video
			'noplaylist' : True,       # only download single song, not playlist
			'logger': logger,
			'progress_hooks': [dl_hook_track],
		}
	# PLAYLIST PARAMETER
	elif (type == 'playlist'):
		options = {
			'format': 'bestaudio/best', # choice of quality
			'extractaudio' : True,      # only keep the audio
			'audioformat' : "mp3",      # convert to mp3 
			'outtmpl': output_tag,      # name the file the ID of the video
			'noplaylist' : True,       # only download single song, not playlist
			'logger': logger,
			'progress_hooks': [dl_hook_playlist],
		}
	
	#DOWNLOAD
	with youtube_dl.YoutubeDL(options) as ydl:
		ydl.download([url])
	
	#EDIT TEXT META DATA (COVER NOT WORKING)
	cur_song_file = eyed3.load(output_tag)
	if cur_song_file.tag is None:
		cur_song_file.tag = eyed3.id3.Tag()
		cur_song_file.tag.file_info = eyed3.id3.FileInfo(output_tag)
	cur_song_file.tag.title = unicode(title)
	cur_song_file.tag.artist = unicode(artist)
	cur_song_file.tag.album = unicode(album)
	#SAVE EDIT
	cur_song_file.tag.save(version=(2, 3, 0))
	
	#UPLOAD TO GOOGLE MUSIC + EDIT COVER
	gmusic_feedback = api.upload(output_tag, False)
	if output_tag in gmusic_feedback[0]:# SUCCESS
		#UPDATE COVER
		id_gmusic_song = gmusic_feedback[0][output_tag]#Get Gmusic song ID and update cover through WebClient
		logger.debug('id_gmusic_song: ' + id_gmusic_song + ', cover to be updated.')
		webclient.upload_album_art(id_gmusic_song, cover_file)
		#UPDATE REPORTING AND FAVORITE UPLOADED LIST
		if(type == 'track'):
			if(id not in reporting_tracks_success): #Reporting
				reporting_tracks_success.append(id)
			if(id in reporting_tracks_error): #Reporting: Remove False Neg
				reporting_tracks_error.remove(id)
			if(id not in uploaded_tracks): #Favorite list
				uploaded_tracks.append(id)
		elif(type == 'playlist'):
			if(parent_id not in reporting_playlists_success): #Reporting
				reporting_playlists_success.append(parent_id)
			if(parent_id in reporting_playlists_error): #Reporting: Remove False Neg
				reporting_playlists_error.remove(parent_id)
			if(parent_id not in uploaded_playlists): #Favorite list
				uploaded_playlists.append(parent_id)
	else: # ERROR
		if(type == 'track'):
			if(id not in reporting_tracks_error):
				reporting_tracks_error.append(id)
		elif(type == 'playlist'):
			if(parent_id not in reporting_playlists_error):
				reporting_playlists_error.append(parent_id)
	return;

###################################################
###												###
###						INIT					###
###												###
###################################################

### SETUP: DATE
now = datetime.datetime.now()

### SETUP: LOGGING
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

logger.info('Edgar, reporting for duty ...')

### SETUP: GOOGLE MUSIC API - MUSICMANAGER
requests.packages.urllib3.disable_warnings()
oauth_file = '/root/.oauthfile'
mac_address = 'XXXX'
api = Musicmanager(True,True,True)
musicmanager_login_status = api.login(oauth_file, mac_address)
logger.debug("Musicmanager login status: " + str(musicmanager_login_status))

### SETUP: GOOGLE MUSIC API - WEBCLIENT
google_login = 'XXXX'
google_passw = 'XXXX'
webclient = Webclient(True, True, True)
webclient_login_status = webclient.login(google_login, google_passw)
logger.debug("Webclient login status: " + str(webclient_login_status))

### SETUP: SOUNDCLOUD API
soundcloud_userid = 'XXXX'
soundcloud_clientid = 'XXXX'
soundcloud_api_baseurl = 'https://api-v2.soundcloud.com/users/'
soundcloud_api_favoriteparam = '/likes?limit=10&offset=0&client_id='
soundcloud_favorites_url = soundcloud_api_baseurl + soundcloud_userid + soundcloud_api_favoriteparam + soundcloud_clientid
soundcloud_client = soundcloud.Client(client_id = soundcloud_clientid)

### SETUP: REPORTING DATA
reporting_tracks_success = []
reporting_tracks_error = []
reporting_playlists_success = []
reporting_playlists_error = []

###################################################
###												###
###						START					###
###												###
###################################################

### DOWNLOAD & UPLOAD NEW TRACKS/PLAYLISTS ######
logger.info('Edgar checks songs list on SoundCloud API v2 ...')

#GET CURRENT FAVORITES (TRACK + PLAYLIST)
uploaded_tracks = []
uploaded_playlists = []
with open('favorites_uploaded.json') as file_favorites_uploaded:
    json_favorites_uploaded = json.load(file_favorites_uploaded)
logger.debug('OUTPUT '+ json.dumps(json_favorites_uploaded))
for uploaded_track in json_favorites_uploaded['favorites_uploaded']['tracks']:
	uploaded_tracks.append(uploaded_track['id'])
for uploaded_playlist in json_favorites_uploaded['favorites_uploaded']['playlists']:
	uploaded_playlists.append(uploaded_playlist['id'])

#GET CURRENT FAVORITES (TRACK + PLAYLIST)
soundcloud_favorites_data = urllib.urlopen(soundcloud_favorites_url)
soundcloud_favorites_json = json.loads(soundcloud_favorites_data.read())

for favorite in soundcloud_favorites_json['collection']:
	if(favorite.get('track')):
		if (favorite['track']['id'] not in uploaded_tracks): ###LIVE: in >>> not in ###
			cur_track = favorite['track']
			cur_id = cur_track['id']
			cur_artist = cur_track['user']['username']
			cur_title = cur_track['title']
			cur_album = cur_track['user']['username'] + ' - SoundCloud'
			cur_url =  cur_track['uri']
			cur_cover_url = cur_track['artwork_url'].replace('-large','-t500x500') #Max size image
			logger.debug('COVER_URL TO DOWNLOAD: '+ cur_cover_url)
			cur_type = 'track'
			download_upload(cur_id, cur_artist, cur_title, cur_album, cur_url, cur_cover_url, cur_type, cur_id)
	elif (favorite.get('playlist')):
		if (favorite['playlist']['id'] not in uploaded_playlists): ###LIVE: in >>> not in ###
			cur_playlist = favorite['playlist']
			cur_playlist_id = cur_playlist['id']
			cur_playlist_url = cur_playlist['uri']
			cur_playlist_cover_url = cur_playlist['artwork_url'].replace('-large','-t500x500') #Max size image
			logger.debug('PLAYLIST_COVER_URL TO DOWNLOAD: '+ cur_playlist_cover_url)
			cur_album = cur_playlist['title']
			cur_type = 'playlist'
			cur_playlist_details = soundcloud_client.get('/resolve', url=cur_playlist_url)
			for cur_track in cur_playlist_details.tracks:
				cur_id = cur_track['id']
				cur_artist = cur_track['user']['username']
				cur_title = cur_track['title']
				cur_url =  cur_track['uri']
				cur_cover_url = cur_track['artwork_url'] #Might be NoneType
				if(cur_cover_url is None): # If track with no cover, takes cover from playlist
					cur_cover_url = cur_playlist_cover_url
				else:
					cur_cover_url = cur_cover_url.replace('-large','-t500x500') #Max size image
				logger.debug('PLAYLIST_TRACK_COVER_URL TO DOWNLOAD: '+ cur_cover_url)
				download_upload(cur_id, cur_artist, cur_title, cur_album, cur_url, cur_cover_url, cur_type, cur_playlist_id)

### BUILD REPORTING JSON FILE
reporting_json = u'{"tracks":'
reporting_json = reporting_json + u'{"success":['
for success_track in reporting_tracks_success:
	reporting_json = reporting_json + str(success_track) + ','
if (len(reporting_tracks_success) > 0):
	reporting_json = reporting_json[:-1] #Removes last ","
reporting_json = reporting_json + u'], "error":['
for error_track in reporting_tracks_error:
	reporting_json = reporting_json + str(error_track) + ','
if (len(reporting_tracks_error) > 0):
	reporting_json = reporting_json[:-1] #Removes last ","
reporting_json = reporting_json + u']}, "playlists":'
reporting_json = reporting_json + u'{"success":['
for success_playlist in reporting_playlists_success:
	reporting_json = reporting_json + str(success_playlist) + ','
if (len(reporting_playlists_success) > 0):
	reporting_json = reporting_json[:-1] #Removes last ","
reporting_json = reporting_json + u'], "error":['
for error_playlist in reporting_playlists_error:
	reporting_json = reporting_json + str(error_playlist) + ','
if (len(reporting_playlists_error) > 0):
	reporting_json = reporting_json[:-1] #Removes last ","
reporting_json = reporting_json + u']}}'
logger.debug('REPORTING JSON: ' + str(reporting_json))

reporting_json_filename = 'reports/report_' + now.strftime("%Y-%m-%d") + '.json'
with open(reporting_json_filename, 'w') as output_file:
	output_file.write(reporting_json)

### UPDATE favorites_uploaded JSON
updated_favorites = u'{"favorites_uploaded": {"tracks": ['
for track in uploaded_tracks:
	updated_favorites = updated_favorites + '{"id": ' + str(track) + '},'
if (len(uploaded_tracks) > 0):
	updated_favorites = updated_favorites[:-1] #Removes last ","
updated_favorites = updated_favorites + u'], "playlists": ['
for playlist in uploaded_playlists:
	updated_favorites = updated_favorites + '{"id": ' + str(playlist) + '},'
if (len(uploaded_playlists) > 0):
	updated_favorites = updated_favorites[:-1] #Removes last ","
updated_favorites = updated_favorites + u']}}'

logger.debug('UPDATED UPLOADED FAVORITES: ' + str(updated_favorites))

with open('favorites_uploaded.json', 'w') as outfile:
	outfile.write(updated_favorites)

### LOG OUT
webclient.logout()
logger.info('Done! Edgar out!')