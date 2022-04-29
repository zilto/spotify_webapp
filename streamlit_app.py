from io import BytesIO
import os
import pathlib
import zipfile

import streamlit as st
import streamlit.components.v1 as components
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import pytube
import ffmpeg


BASE_DIR = pathlib.Path(".\\download\\")


def get_track_from_youtube(artist: str, title: str) -> BytesIO:
    search = pytube.Search(f"{artist} {title}")
    first_video = search.results[0]
    audio_stream = first_video.streams.get_audio_only(subtype="mp4")
    audio_buffer = BytesIO()
    audio_stream.stream_to_buffer(audio_buffer)
    return audio_buffer


def create_metadata(track: dict) -> dict:
    metadata_kwargs = {
        "metadata:g:0": f'title={track["title"]}',
        "metadata:g:1": f'artist={track["artist"]}',
        "metadata:g:2": f'album={track["album"]}',
    }
    return metadata_kwargs


def download_track(track: dict, subdirectory: str) -> None:
    audio_buffer = get_track_from_youtube(artist=track["artist"], title=track["title"])
    metadata_kwargs = create_metadata(track=track)

    # create download subdirectory
    output_dir = BASE_DIR.joinpath(subdirectory)
    output_dir.mkdir(exist_ok=True)
    output_fname = f"{track['artist']} - {track['title']}.mp4"
    output_path = output_dir.joinpath(output_fname)

    # try/except necessary to catch ffmpeg errors
    try:
        process = ffmpeg.input("pipe:", f="mp4")\
                        .output(str(output_path), f="mp4", **metadata_kwargs) \
                        .run_async(pipe_stdin=True, pipe_stdout=True, overwrite_output=True)
        process.communicate(input=audio_buffer.getvalue())
    except ffmpeg.Error as e:
        print('stdout:', e.stdout.decode('utf8'))
        print('stderr:', e.stderr.decode('utf8'))
        raise e


def parse_playlist(api_response: dict) -> list[dict]:
    items = []
    for item in api_response["tracks"]["items"]:
        album = item["track"]["album"]["name"]
        artist = item["track"]["artists"][0]["name"]
        title = item["track"]["name"]
        items.append(dict(title=title, artist=artist, album=album))

    return items


def parse_album(api_response: dict) -> list:
    album = api_response["name"]
    artist = api_response["artists"][0]["name"]

    items = []
    for item in api_response["tracks"]["items"]:
        items.append(dict(title=item["name"], artist=artist, album=album))

    return items


def parse_track(api_response: dict) -> list:
    album = api_response["album"]["name"]
    artist = api_response["artists"][0]["name"]
    title = api_response["name"]
    return [dict(title=title, artist=artist, album=album)]  # wrap the single item in a list


def display_file_tree(root: str):
    file_tree = {}
    for path, subdirectories, files in os.walk(root):
        _, _, current_sub = path.partition("\\")
        for s in subdirectories:
            file_tree[s] = []
        for f in files:
            file_tree[current_sub].append(f)
    st.json(file_tree)


@st.experimental_singleton
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
        response = spotify_client.playlist(spotify_url, fields="(name, tracks(items(track(artists(name), name, album(name)))))")
        tracks = parse_playlist(response)
        subdirectory = response["name"]
    elif url_parts[3] == "album":
        response = spotify_client.album(spotify_url)
        tracks = parse_album(response)
        subdirectory = response["name"]
    elif url_parts[3] == "track":
        response = spotify_client.track(spotify_url)
        tracks = parse_track(response)
        subdirectory = response["name"]
    else:
        tracks = []
        subdirectory = None

    track_selection = st.multiselect(
        label="Track Selection",
        options=tracks,
        default=tracks,
        format_func=lambda x: x["title"],
        help="Select tracks to be downloaded"
    )

    # create main download directory
    BASE_DIR.mkdir(exist_ok=True)

    # logic kept here to allow for progress bar without complicated callbacks
    if st.button("Get Tracks"):
        download_progress = st.progress(0)
        # logs_expander = st.expander("Logs")

        for idx, track in enumerate(track_selection):
            try:
                download_track(track=track, subdirectory=subdirectory)
                # logs_expander.write(f"{idx + 1} - Success - {track['artist']} - {track['title']}")
            except FileExistsError:
                pass
                # logs_expander.write(f"{idx + 1} - Failure - {track['artist']} - {track['title']}")
            finally:
                download_progress.progress((idx + 1) / len(track_selection))
                display_file_tree(BASE_DIR)

        with zipfile.ZipFile("spotify_download.zip", "w") as myzip:
            for child in BASE_DIR.iterdir():
                if child.is_file():
                    myzip.write(child)

        with open("spotify_download.zip", "rb") as file:
            st.download_button("Download zip", file, "output.zip", mime="application/octet-stream")


def app() -> None:
    """contains the logic for the app layout"""
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
