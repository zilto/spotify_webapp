# Spotify downloader
![Screenshot](https://raw.githubusercontent.com/zilto/spotify_webapp/main/README.md)

## Motivation
The Spotify recommendation system often impresses me. It is a great service, but I also like to have music stored locally on my device. It allows me to listen to it while keeping my device offline to shield myself from distractions

## Solution
I built a small webapp that allows me to download my favorite Spotify content
**Try it here**: https://zilto-spotify-webapp-streamlit-app-yh7tjd.streamlitapp.com/

### How to use it
0. Create a public playlist on Spotify
1. Input the link to any public Spotify object (playlist, album, or track)
2. The result of the link should appear in the embed widget
3. Press ```Get Tracks``` to start **downloading to your browser** (cache). A progress bar should appear.
4. After this download, the retrieved items should be under ```Stored tracks```
5. Finally, pressing ```Download Stored Tracks``` will zip all stored tracks and download it to your device
6. The button ```Clear Stored Tracks``` to clear the cache in case you want to download another Spotify item.


### How does it work
This whole projects fits in a single file ```spotify_webapp.py``` and relies on 4 packages:

- **Streamlit**: build the webapp and the GUI
- **Spotipy**: access the public Spotify API to retrieve content metadata
- **Pytube**: the Spotify metadata is used to query YouTube to retrieve the audio content using this API
- **ffmpeg**: set the Spotify metadata to the audio file
