# ----- FILE PURPOSE -----
"""
    Functions for retrieving artists and tracks from the Last.fm API.
"""


# ----- IMPORTS -----

import requests


# ----- FUNCTIONS -----

def get_artist_top_tracks(artist_name, api_key, limit=50):
    """
    Retrieve an artist's most popular tracks from Last.fm.
    """

    response = requests.get(
        "https://ws.audioscrobbler.com/2.0/",
        params={
            "method": "artist.getTopTracks",
            "artist": artist_name,
            "api_key": api_key,
            "format": "json",
            "limit": limit,
            "autocorrect": 1
        },
        timeout=10
    )

    if response.status_code != 200:
        return []

    data = response.json()

    tracks = (
        data.get("toptracks", {})
        .get("track", [])
    )

    # Last.fm can return one dictionary instead of a list
    if isinstance(tracks, dict):
        tracks = [tracks]

    cleaned_tracks = []

    for track in tracks:
        cleaned_tracks.append({
            "track": track.get("name"),
            "artist": track.get("artist", {}).get("name", artist_name),
            "listeners": int(track.get("listeners", 0)),
            "playcount": int(track.get("playcount", 0)),
            "url": track.get("url"),
            "source": "chosen_artist"
        })

    return cleaned_tracks


def get_similar_artists(artist_name, api_key, limit=10):
    """
    Retrieve artists that Last.fm considers similar to a selected artist.
    """

    response = requests.get(
        "https://ws.audioscrobbler.com/2.0/",
        params={
            "method": "artist.getSimilar",
            "artist": artist_name,
            "api_key": api_key,
            "format": "json",
            "limit": limit,
            "autocorrect": 1
        },
        timeout=10
    )

    if response.status_code != 200:
        return []

    data = response.json()

    similar_artists = (
        data.get("similarartists", {})
        .get("artist", [])
    )

    if isinstance(similar_artists, dict):
        similar_artists = [similar_artists]

    return [
        artist["name"]
        for artist in similar_artists
        if artist.get("name")
    ]


def get_artist_info(artist_name, api_key):
    """
    Retrieve information about one artist from Last.fm.
    """

    response = requests.get(
        "https://ws.audioscrobbler.com/2.0/",
        params={
            "method": "artist.getInfo",
            "artist": artist_name,
            "api_key": api_key,
            "format": "json",
            "autocorrect": 1
        },
        timeout=10
    )

    if response.status_code != 200:
        return {}

    data = response.json()

    # Last.fm can return an error inside a successful HTTP response
    if data.get("error"):
        return {}

    artist = data.get("artist", {})
    statistics = artist.get("stats", {})

    tags = (
        artist.get("tags", {})
        .get("tag", [])
    )

    # Last.fm may return a single tag dictionary instead of a list
    if isinstance(tags, dict):
        tags = [tags]

    tag_names = [
        tag.get("name")
        for tag in tags
        if tag.get("name")
    ]

    biography = (
        artist.get("bio", {})
        .get("summary", "")
    )

    # Remove Last.fm's HTML "Read more" link from the biography
    biography = biography.split("<a href=")[0].strip()

    return {
        "name": artist.get("name", artist_name),
        "listeners": int(statistics.get("listeners", 0)),
        "playcount": int(statistics.get("playcount", 0)),
        "tags": tag_names,
        "biography": biography,
        "url": artist.get("url", "")
    }


def get_genre_top_tracks(genre_name, api_key, limit=50):
    # retrieve Last.fm's top tracks for a genre tag.

    response = requests.get(
        "https://ws.audioscrobbler.com/2.0/",
        params={
            "method": "tag.getTopTracks",
            "tag": genre_name,
            "api_key": api_key,
            "format": "json",
            "limit": limit
        },
        timeout=10
    )

    if response.status_code != 200:
        return []

    data = response.json()

    # Last.fm can return an error inside a successful HTTP response
    if data.get("error"):
        return []

    tracks = (
        data.get("tracks", {})
        .get("track", [])
    )

    # Ensure one result is still handled as a list
    if isinstance(tracks, dict):
        tracks = [tracks]

    cleaned_tracks = []

    for track in tracks:
        artist_data = track.get("artist", {})

        if isinstance(artist_data, dict):
            artist_name = artist_data.get("name")
        else:
            artist_name = artist_data

        if not track.get("name") or not artist_name:
            continue

        cleaned_tracks.append({
            "track": track.get("name"),
            "artist": artist_name,
            "genre": genre_name,
            "url": track.get("url"),
            "source": "evil_twin"
        })

    return cleaned_tracks

def get_track_info(track_name, artist_name, api_key):
    """
    Retrieve listener and playcount information for one track.
    """

    response = requests.get(
        "https://ws.audioscrobbler.com/2.0/",
        params={
            "method": "track.getInfo",
            "track": track_name,
            "artist": artist_name,
            "api_key": api_key,
            "format": "json",
            "autocorrect": 1
        },
        timeout=10
    )

    if response.status_code != 200:
        return {
            "listeners": 0,
            "playcount": 0
        }

    data = response.json()

    if data.get("error"):
        return {
            "listeners": 0,
            "playcount": 0
        }

    track = data.get("track", {})

    return {
        "listeners": int(track.get("listeners", 0)),
        "playcount": int(track.get("playcount", 0))
    }
