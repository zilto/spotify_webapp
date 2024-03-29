from io import BytesIO
import os
import pathlib
import shutil

import streamlit as st
import streamlit.components.v1 as components
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import pytube
from pytube.exceptions import VideoUnavailable
import ffmpeg


BASE_DIR = pathlib.Path.cwd().joinpath("../download")


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


def get_filetree(root: str) -> dict:
    filetree = {}
    for fullpath, subdirectories, files in os.walk(root):
        endpoint = pathlib.Path(fullpath).name
        for s in subdirectories:
            filetree[s] = []
        for f in files:
            filetree[endpoint].append(f)
    return filetree


def query_spotify_api(spotify_url: str) -> tuple:
    spotify_client = spotipy.client.Spotify(auth_manager=get_authenticator())
    url_parts = spotify_url.split("/")

    if url_parts[3] == "playlist":
        response = spotify_client.playlist(spotify_url, fields="(name, tracks(items(track(artists(name), name, album(name)))))")
        tracks = parse_playlist(response)
        subdirectory = response.pop("name")
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

    return tracks, subdirectory


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
    components.iframe(src=embed_url, height=200)


def container_query_api(spotify_url: str) -> None:
    tracks, subdirectory = query_spotify_api(spotify_url=spotify_url)

    track_selection = st.multiselect(
        label="Track Selection",
        options=tracks,
        default=tracks,
        format_func=lambda x: x["title"],
        help="Select tracks to be downloaded"
    )

    if st.button("Get Tracks", help="Tracks are cached in your browser and will appear under `Stored tracks`."):
        download_progress = st.progress(0)
        for idx, track in enumerate(track_selection):
            try:
                download_track(track=track, subdirectory=subdirectory)
            except FileExistsError:
                st.error(f"Error getting: {track['artist']} {track['title']}")
            except VideoUnavailable:
                st.error(f"Video Unavailable: {track['artist']} {track['title']}")
            finally:
                download_progress.progress((idx + 1) / len(track_selection))
        st.success("Done getting tracks")


def container_download_tracks() -> None:
    st.subheader("Stored tracks")
    with st.empty():  # st.empty() allow to update the same container
        st.json(get_filetree(BASE_DIR))

    shutil.make_archive("spotify_download", "zip", BASE_DIR)  # need to create empty .zip to avoid error with the button
    with open("./spotify_download.zip", "rb") as file:
        st.download_button(
            label="Download Stored Tracks",
            data=file,
            file_name="./spotify_download.zip",
            help="Download the files appearing under `Stored tracks`"
        )

    if st.button("Clear Stored Tracks", help="Clear your local cache of `Stored tracks`"):
        shutil.rmtree(BASE_DIR)  # delete the BASE_DIR and all subdirectory
        BASE_DIR.mkdir(exist_ok=True)  # make a new BASE_DIR


def app() -> None:
    """contains the logic for the app layout"""
    st.set_page_config(
        page_title="Spotify Downloader",
        page_icon="https://e7.pngegg.com/pngimages/738/294/png-clipart-spotify-logo-podcast-music-matty-carter-ariel-pink-spotify-icon-logo-preview.png",
        layout="centered",
        menu_items={"Get help": None, "Report a Bug": None}
    )
    # create main download directory
    BASE_DIR.mkdir(exist_ok=True)

    st.title("Spotify Downloader :inbox_tray:")
    spotify_url = st.text_input(
        "Spotify URL",
        value="https://open.spotify.com/album/1WoYIuMY3GbV4JyTzcdKGU",
        help="Paste Spotify URL to playlist, album, or track"
    )

    col1, col2 = st.columns(2)

    with col1:
        container_spotify_iframe(spotify_url)
        container_query_api(spotify_url)

    with col2:
        container_download_tracks()


if __name__ == "__main__":
    app()
