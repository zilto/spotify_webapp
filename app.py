import json
import urllib

import streamlit as st
import streamlit.components.v1 as components
#import spotipy
import pytube
import ffmpeg


def query_youtube_vid(artist: str, track: str):
    search = pytube.Search(f"{artist} {track}")
    first_yt_vid = search.results[0]
    return first_yt_vid


def download_youtube_audio(yt_video, artist: str, track: str) -> str:
    audio_stream = yt_video.streams.filter(only_audio=True, mime_type="audio/mp4", abr="128kbps")[0]
    audio_filepath = audio_stream.download(
        output_path="./download/",
        filename=f"{artist}_{track}.mp4",
        skip_existing=True,
    )
    return audio_filepath


def convert_mp4_to_wav(input_filepath: str) -> None:
    filename = input_filepath.split("\\")[-1].split(".")[0]
    ffmpeg.input(input_filepath).output(f"/convert/{filename}.wav", format="wav").run()


def parse_html(html_string: str) -> dict:
    return json.loads(urllib.parse.unquote(html_string))


def get_artist_and_track(track_json: dict) -> tuple:
    artist = track_json["artists"][0]["name"]
    track = track_json["name"]
    return artist, track


def app() -> None:
    st.title("Spotify Webapp")

    spotify_url = st.text_input("Spotify URL", value="https://open.spotify.com/track/38eKsyxIMyad7T9mil550f")
    url_parts = spotify_url.split("/")
    # TODO conditional structure based on spotify url: album, song, playlist
    embed_url = f"https://{url_parts[2]}/embed/{url_parts[3]}/{url_parts[4]}?utm_source=generator"
    components.iframe(src=embed_url, height=600)
    response_json = parse_html("")

    if url_parts[3] is "track":
        artist, track = get_artist_and_track(track_json=response_json)
    elif url_parts[3] is "album":
        # TODO
        tracks = (get_artist_and_track(track_json=response_json["items"]) for item in response_json["items"])
    # yt_video = query_youtube_vid(artist=artist, track=track)
    # audio_filepath = download_youtube_audio(yt_video=yt_video, artist=artist, track=track)
    # convert_mp4_to_wav(input_filepath=audio_filepath)


if __name__ == "__main__":
    app()
