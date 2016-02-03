# Edgar - The PorcDigy

Edgar provides you the best of SoundCloud directly into your Google Music account for your best pleasure.

Edgar duties consist in:
- Checking everyday (cronjob) your SoundCloud liked songs and playlists ([SoundCloud API](https://developers.soundcloud.com/docs/api/guide)),
- Downloading the new entries, songs and metadata ([youtube-dl](https://github.com/rg3/youtube-dl)),
- Uploading the new entries to your Google Music account ([gmusicapi](https://github.com/simon-weber/gmusicapi)),
- Editing the new entries (including songs front cover),
- Building a weekly web report (cronjob) of its activities (script To Be Updated).

# Remarks

- The following directory structure must be setup:
```
edgar
│   edgar.py
│   edgar_reporting.py  
│   favorites_uploaded.json    
│
└───songs
    │
└───covers
    │
└───logs
    │
└───reports
    │
    ├───_old
    │   │
```
- Edgar keeps track of his work in the favorites_uploaded.json file which can be initialized with and empty json object for instance.

- SoundCloud does not, at this time, provide from the official API the list of liked songs AND playlists. As a result, the API v2 (still in Beta) is used.

- Edgar reports his weekly work on a webpage that needs to be setup (script To Be Updated).
