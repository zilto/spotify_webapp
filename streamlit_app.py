from io import BytesIO
import tempfile
from urllib.error import HTTPError

import streamlit as st
import streamlit.components.v1 as components
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import pytube
import ffmpeg


def download_track(track: dict) -> None:
    # try:
    search = pytube.Search(f"{track['artist']} {track['title']}")
    first_video = search.results[0]
    audio_stream = first_video.streams.get_audio_only(subtype="mp4")
    audio_buffer = BytesIO()
    audio_stream.stream_to_buffer(audio_buffer)
    # except HTTPError as e:
    #     print(e.code)

    metadata = {
        "metadata:g:0": f'title={track["title"]}',
        "metadata:g:1": f'artist={track["artist"]}',
        "metadata:g:2": f'album={track["album"]}',
    }
    #                .output(f"./download/{track['artist']} - {track['title']}.mp4", f="mp4", **metadata)\
    try:
        process = ffmpeg.input("pipe:", f="mp4")\
                        .output(f"{track['artist']} - {track['title']}.mp4", f="mp4", **metadata) \
                        .run_async(pipe_stdin=True, pipe_stdout=True, overwrite_output=True)
        process.communicate(input=audio_buffer.getvalue())
    except ffmpeg.Error as e:
        print('stdout:', e.stdout.decode('utf8'))
        print('stderr:', e.stderr.decode('utf8'))
        raise e


def parse_playlist_items(api_response: dict) -> list[dict]:
    items = []
    for item in api_response["items"]:
        album = item["track"]["album"]["name"]
        artist = item["track"]["artists"][0]["name"]
        title = item["track"]["name"]
        items.append(dict(title=title, artist=artist, album=album))

    return items


def parse_album(api_response: dict) -> list:
    items = []
    album = api_response["name"]
    artist = api_response["artists"][0]["name"]

    for item in api_response["tracks"]["items"]:
        items.append(dict(title=item["name"], artist=artist, album=album))

    return items


def parse_track(api_response: dict) -> list:
    album = api_response["album"]["name"]
    artist = api_response["artists"][0]["name"]
    title = api_response["name"]
    return [dict(title=title, artist=artist, album=album)]


# @st.cache(allow_output_mutation=True)
def get_authenticator():
    auth_manager = SpotifyClientCredentials(
        client_id=st.secrets["spotify_api"]["client_id"],
        client_secret=st.secrets["spotify_api"]["client_secret"],
    )
    return auth_manager


def container_spotify_iframe(spotify_url: str) -> None:
    url_parts = spotify_url.split("/")
    embed_url = f"https://{url_parts[2]}/embed/{url_parts[3]}/{url_parts[4]}?utm_source=generator"
    components.iframe(src=embed_url, height=400)


def container_api_download(spotify_url: str) -> None:
    spotify_client = spotipy.client.Spotify(auth_manager=get_authenticator())
    url_parts = spotify_url.split("/")

    if url_parts[3] == "playlist":
        response = spotify_client.playlist_items(spotify_url,
                                                 fields="items(track(artists(name), name, album(name)))")
        tracks = parse_playlist_items(response)
    elif url_parts[3] == "album":
        response = spotify_client.album(spotify_url)
        tracks = parse_album(response)
    elif url_parts[3] == "track":
        response = spotify_client.track(spotify_url)
        tracks = parse_track(response)
    else:
        tracks = []

    track_selection = st.multiselect(
        label="Track Selection",
        options=tracks,
        default=tracks,
        format_func=lambda x: x["title"],
        help="Select tracks to be downloaded"
    )

    if st.button("Download Tracks"):
        download_progress = st.progress(0)
        logs_expander = st.expander("Logs")
        for idx, track in enumerate(track_selection):
            download_track(track)
            download_progress.progress((idx + 1) / len(track_selection))
            logs_expander.write(f"{idx+1} - Success - {track['artist']} - {track['title']}")


def app() -> None:
    st.set_page_config(
        page_title="Spotify Downloader",
        page_icon="https://e7.pngegg.com/pngimages/738/294/png-clipart-spotify-logo-podcast-music-matty-carter-ariel-pink-spotify-icon-logo-preview.png",
        layout="centered",
        menu_items={"Get help": None, "Report a Bug": None}
    )

    st.title("Spotify Downloader")

    spotify_url = st.text_input(
        "Spotify URL",
        value="https://open.spotify.com/album/4tBF36exZUWUcDwluyHKcV",
        help="Paste Spotify URL to playlist, album, or track"
    )

    col1, col2 = st.columns(2)
    with col1:
        container_spotify_iframe(spotify_url)

    with col2:
        container_api_download(spotify_url)


if __name__ == "__main__":
    app()
