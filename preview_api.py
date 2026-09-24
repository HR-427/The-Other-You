# ----- FILE PURPOSE -----
"""
Retrieve short song previews from the Apple iTunes Search API.
"""


# ----- IMPORTS -----

import re

import requests


# ----- FUNCTIONS -----

def _normalise_text(value):
    # create a simple value that can be used to compare search results

    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def get_track_preview(track_name, artist_name, country="GB"):
    # find a 30-second preview for a track and artist

    try:
        response = requests.get(
            "https://itunes.apple.com/search",
            params={
                "term": f"{track_name} {artist_name}",
                "media": "music",
                "entity": "song",
                "country": country,
                "limit": 5
            },
            timeout=10
        )
    except requests.RequestException:
        return {}

    if response.status_code != 200:
        return {}

    results = response.json().get("results", [])
    results_with_previews = [
        result
        for result in results
        if result.get("previewUrl")
    ]

    if not results_with_previews:
        return {}

    expected_track = _normalise_text(track_name)
    expected_artist = _normalise_text(artist_name)

    # Prefer an exact track-and-artist match. If Apple formats a collaboration
    # differently, use the first result that still has a playable preview.
    best_result = next(
        (
            result
            for result in results_with_previews
            if _normalise_text(result.get("trackName", "")) == expected_track
            and expected_artist in _normalise_text(
                result.get("artistName", "")
            )
        ),
        results_with_previews[0]
    )

    return {
        "preview_url": best_result.get("previewUrl", ""),
        "store_url": best_result.get("trackViewUrl", ""),
        "track": best_result.get("trackName", track_name),
        "artist": best_result.get("artistName", artist_name)
    }
