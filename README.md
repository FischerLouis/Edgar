# Edgar - The PorcDigy

Edgar provides you the best of SoundCloud directly into your Google Music account for your best pleasure.

Edgar duties consist in:
- Checking everyday (cronjob) your SoundCloud liked songs and playlists,
- Downloading the new entries (songs and metadata),
- Uploading the new entries to your Google Music account,
- Editing the new entries (including song front cover),
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

- SoundCloud does not, at this time, provide the list of liked songs AND playlists deom the official API. As a result, the API v2 (still in Beta) is used.

- Edgar reports his weekly work on a webpage that needs to be setup (script outdated).
