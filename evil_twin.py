# ----- FILE PURPOSE -----

'''
    This file contains the functions used to create the evil twin music profile 
'''

# ----- IMPORTS ------
import math
from lastfm_api import get_genre_top_tracks, get_track_info


# ----- FUNCTIONS -----

def create_evil_user_features(user_features): 
    # reverse the user's model inputs to create an opposing music profile 

    evil_features = {
        "popularity": 100 - user_features["popularity"], #popularity ranges from 0-100
        "acousticness": 1 - user_features["acousticness"], 
        "danceability": 1 - user_features["danceability"], 
        "duration_ms": 480000 - user_features["duration_ms"], #duration ranges between 12000 and 36000 so we add the endpoints
        "energy": 1 - user_features["energy"], 
        "instrumentalness": 1 - user_features["instrumentalness"], 
        "liveness": 1 - user_features["liveness"], 
        "loudness": -30 - user_features["loudness"], #loudness ranges between -30 and 0 
        "speechiness": 1 - user_features["speechiness"], 
        "tempo": 260 - user_features["tempo"], # min (60) plus max (200)
        "valence": 1 - user_features["valence"], 
        "key": user_features["key"],
        "mode": (
            "Minor"
            if user_features["mode"] == "Major"
            else "Major"
        )
    }

    return evil_features


def build_evil_candidate_pool(
    evil_genre_predictions,
    api_key,
    playlist_length
):
    # retrieve a balanced pool of tracks from the three evil-twin genres
    # for example, for a 20 song playlist with genres: classical, jazz and country: 
    # a candidate pool of 20x3 = 60 is created 
    # making 20 of each genre and alternates between the genres: 
    # 1st: classical, 2nd: jazz, 3rd: country
    # 4th: classical, 5th: jazz, 6th: country

    evil_genres = [
        prediction["genre"]
        for prediction in evil_genre_predictions
    ]

    if not evil_genres:
        return []

    # Build a pool around three times larger than the final playlist
    candidate_pool_size = max(playlist_length * 3, 50)

    tracks_per_genre = math.ceil(
        candidate_pool_size / len(evil_genres)
    )

    tracks_per_genre = min(tracks_per_genre, 50)

    genre_track_lists = []

    for genre in evil_genres:
        genre_tracks = get_genre_top_tracks(
            genre_name=genre,
            api_key=api_key,
            limit=tracks_per_genre
        )

        genre_track_lists.append(genre_tracks)

    # Alternate between genres rather than placing one whole genre first
    combined_candidates = []
    longest_genre_list = max(
        (len(tracks) for tracks in genre_track_lists),
        default=0
    )

    for track_position in range(longest_genre_list):
        for genre_tracks in genre_track_lists:
            if track_position < len(genre_tracks):
                combined_candidates.append(
                    genre_tracks[track_position]
                )

    # Remove duplicate track and artist combinations
    unique_candidates = []
    seen_tracks = set()

    for track in combined_candidates:
        track_identity = (
            track["track"].strip().lower(),
            track["artist"].strip().lower()
        )

        if track_identity not in seen_tracks:
            seen_tracks.add(track_identity)
            unique_candidates.append(track)

    return unique_candidates


def create_evil_twin_playlist(
    candidate_pool,
    playlist_length,
    selected_artists,
    normal_playlist
):
    # filter the candidate pool and select the final evil-twin playlist.
    # converts user's selected artists into lowercase values
    # records every song used in normal playlist
    # song only excluded if in normal playlist
    # first pass allows one track per artist - diversity 
    # second pass allows addition tracks from previously used artists until playlist length reached 

    excluded_artists = {
        artist.strip().lower()
        for artist in selected_artists
    }

    normal_track_identities = {
        (
            track["track"].strip().lower(),
            track["artist"].strip().lower()
        )
        for track in normal_playlist
    }

    eligible_candidates = []

    for track in candidate_pool:
        track_artist = track["artist"].strip().lower()

        track_identity = (
            track["track"].strip().lower(),
            track_artist
        )

        # Do not include the user's selected artists
        if track_artist in excluded_artists:
            continue

        # Do not repeat anything from the normal playlist
        if track_identity in normal_track_identities:
            continue

        eligible_candidates.append(track)

    evil_playlist = []
    used_artists = set()
    selected_track_identities = set()

    # First pass: select no more than one track from each artist
    for track in eligible_candidates:
        artist_name = track["artist"].strip().lower()

        if artist_name in used_artists:
            continue

        track_identity = (
            track["track"].strip().lower(),
            artist_name
        )

        evil_playlist.append(track)
        used_artists.add(artist_name)
        selected_track_identities.add(track_identity)

        if len(evil_playlist) == playlist_length:
            return evil_playlist

    # Second pass: allow repeated artists if more tracks are needed
    for track in eligible_candidates:
        track_identity = (
            track["track"].strip().lower(),
            track["artist"].strip().lower()
        )

        if track_identity in selected_track_identities:
            continue

        evil_playlist.append(track)
        selected_track_identities.add(track_identity)

        if len(evil_playlist) == playlist_length:
            break

    return evil_playlist

def add_track_metrics(playlist, api_key):
    # add Last.fm listener and playcount metrics to the final playlist.

    enriched_playlist = []

    for track in playlist:
        track_with_metrics = track.copy()

        metrics = get_track_info(
            track_name=track["track"],
            artist_name=track["artist"],
            api_key=api_key
        )

        track_with_metrics.update(metrics)
        enriched_playlist.append(track_with_metrics)

    return enriched_playlist


