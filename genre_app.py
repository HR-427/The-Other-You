# ----- FILE PURPOSE -----
'''
    This file is the main Streamlit app
    
    - Last.gm generates the candidate song pool to be used 
    - My CatBoost model predicts the suitable genres based off the slider questions 
    - The familiarity question really defines the playlist i.e. : 
        - The highest familiarity means that the playlist ONLY contains songs from the user's defined artists
        - The lowest familiarity means that the playlist should NOT contain songs from the defined artists, but the similar ones last.fm provides 
    
'''


# ----- IMPORTS -----

import streamlit as st
import joblib 
from catboost import CatBoostClassifier
import pandas as pd
import numpy as np
import requests 
import math

from dotenv import dotenv_values
from streamlit_searchbox import st_searchbox

from lastfm_api import get_artist_top_tracks, get_similar_artists, get_artist_info
from ui_components import (
    add_vertical_space,
    load_theme,
    render_comparison_page,
    render_genre_cards,
    render_personality_card,
    render_playlist,
    scroll_to_top,
    render_welcome_page
)
from evil_twin import (
    create_evil_user_features,
    build_evil_candidate_pool,
    create_evil_twin_playlist, 
    add_track_metrics
)

env_values = dotenv_values("env")
LASTFM_API_KEY = env_values.get("LASTFM_API_KEY") or st.secrets["LASTFM_API_KEY"]


# ----- CATBOOST MODEL -----

model = CatBoostClassifier()
model.load_model("expanded_genre_model.cbm")

# load saved model information from file 
model_info = joblib.load("genre_model_information.pkl")

GENRE_DESCRIPTIONS = {
    "Alternative": "Experimental music that sits outside mainstream styles.",
    "Anime": "Music associated with anime soundtracks and Japanese pop culture.",
    "Blues": "Expressive music built around soulful vocals and blues progressions.",
    "Classical": "Orchestral and instrumental music with rich, structured arrangements.",
    "Country": "Story-driven music featuring acoustic instruments and warm vocals.",
    "Electronic": "Synthesised, production-led music built with electronic sounds.",
    "Hip-Hop": "Rhythm-focused music combining beats, flow and lyrical expression.",
    "Jazz": "Improvisational music known for expressive harmony and rhythm.",
    "Rap": "Lyric-led music centred on rhythmic spoken delivery and beats.",
    "Rock": "Guitar-driven music ranging from melodic to powerful and energetic."
}


def describe_music_personality(features, profile_name="Your"):
    """
    Describe the listening style suggested by a converted music profile.
    """

    energy = features["energy"]
    tempo = features["tempo"]
    valence = features["valence"]
    acousticness = features["acousticness"]
    popularity = features["popularity"]

    if energy >= 0.67 or tempo >= 155:
        pace_description = "craves momentum, intensity and an energetic atmosphere"
    elif energy <= 0.33 or tempo <= 105:
        pace_description = "prefers space, calmness and a slower musical pace"
    else:
        pace_description = "enjoys a balance between relaxed and energetic sounds"

    if valence >= 0.67:
        mood_description = "leans towards bright, uplifting moods"
    elif valence <= 0.33:
        mood_description = "is drawn to darker, reflective moods"
    else:
        mood_description = "likes emotionally balanced music"

    if acousticness >= 0.67:
        texture_description = "favours natural and acoustic textures"
    elif acousticness <= 0.33:
        texture_description = "favours polished and electronic production"
    else:
        texture_description = "appreciates both organic and produced sounds"

    if popularity >= 67:
        discovery_description = "and enjoys recognisable, widely loved tracks"
    elif popularity <= 33:
        discovery_description = "and is happy exploring music beyond the mainstream"
    else:
        discovery_description = "and mixes familiar favourites with new discoveries"

    return (
        f"{profile_name} music profile {pace_description}, "
        f"{mood_description}, {texture_description} "
        f"{discovery_description}."
    )


# ----- PAGE SETUP -----

st.set_page_config(
    page_title="The Other You",
    page_icon="🎵",
    layout="wide"
)

if "active_page" not in st.session_state:
    st.session_state["active_page"] = "welcome"


if st.session_state["active_page"] == "welcome":
    load_theme("normal")
    render_welcome_page()

    left_space, button_column, right_space = st.columns([2, 1, 2])

    with button_column:
        if st.button("Let's get started", width="stretch"):
            st.session_state["active_page"] = "normal"
            st.rerun()

    st.stop()


if st.session_state["active_page"] == "comparison":
    load_theme("normal")

    st.title("Which Will You Choose?")
    st.write(
        "Compare both sides of your music personality, then copy your "
        "favourite playlist or combine them."
    )

    normal_playlist = st.session_state.get("recommended_playlist", [])
    evil_playlist = st.session_state.get("evil_twin_playlist", [])

    if normal_playlist and evil_playlist:
        render_comparison_page(normal_playlist, evil_playlist)
    else:
        st.error("Both playlists must be generated before they can be compared.")

    if st.button("Start again"):
        st.session_state.clear()
        st.rerun()

    st.stop()


if st.session_state["active_page"] == "evil":
    scroll_to_top()
    load_theme("evil")

    st.title("Your other you's playlist 😈")
    st.write(
        "A darker detour built from the opposite of your music preferences."
    )

    st.subheader("What this says about your 'other you'")
    evil_features = st.session_state.get("evil_user_features")

    if evil_features:
        evil_personality = describe_music_personality(
            evil_features,
            profile_name="Your other you"
        )
    else:
        evil_personality = "Your other you's music profile is unavailable."

    render_personality_card(evil_personality)

    st.subheader("Your other you's top three genres")

    render_genre_cards(
        st.session_state.get("evil_genre_predictions", []),
        GENRE_DESCRIPTIONS,
        "A genre matched to the opposing music profile."
    )

    add_vertical_space()
    st.subheader("Your other you's recommended tracks")

    evil_twin_playlist = st.session_state.get("evil_twin_playlist", [])

    if len(evil_twin_playlist) < st.session_state.get("playlist_length", 0):
        st.warning(
            "Last.fm did not return enough unique tracks to fill "
            "the requested other you's playlist length."
        )

    if evil_twin_playlist:
        render_playlist(evil_twin_playlist)
    else:
        st.error("No other you tracks could be found for this profile.")

    if st.button("Next →"):
        st.session_state["active_page"] = "comparison"
        st.rerun()

    st.stop()


load_theme("normal")


# temp testing lines to see if model loads correctly
#st.write("Model loaded successfully")
#st.write("Model information:", model_info)
#st.write("Genre classes:", model.classes_)

st.title("Your playlist 😇")

st.write(
    "Answer the questions below and the model will predict "
    "the three genres that best match your music preferences."
)



# ----- FUNCTIONS -----

def convert_to_zero_one(value): 
    # subtract 1 to shift the slider range from 1–10 to 0–9,
    # then divide by 9 to scale the result to the 0–1 range

    return (value-1) / 9


def convert_to_range(value, minimum, maximum): 
    # convert 1-10 slider to another numerical range 
    zero_one_value = convert_to_zero_one(value)

    return minimum + zero_one_value * (maximum - minimum)

@st.cache_data(ttl=3600, show_spinner=False)
def search_artists(search_term, excluded_artists=None):

    if not search_term:
        return []

    if excluded_artists is None:
        excluded_artists = []

    excluded_names = {
        artist.strip().lower()
        for artist in excluded_artists
        if artist
    }

    response = requests.get(
        "https://ws.audioscrobbler.com/2.0/",
        params={
            "method": "artist.search",
            "artist": search_term,
            "api_key": LASTFM_API_KEY,
            "format": "json",
            "limit": 8
        },
        timeout=10
    )

    if response.status_code != 200:
        return []

    data = response.json()

    artists = (
        data.get("results", {})
        .get("artistmatches", {})
        .get("artist", [])
    )

    if isinstance(artists, dict):
        artists = [artists]

    artist_names = [
        artist["name"]
        for artist in artists
        if (
            artist.get("name")
            and artist["name"].strip().lower() not in excluded_names
        )
    ]

    return list(dict.fromkeys(artist_names))


@st.cache_data(ttl=3600, show_spinner=False)
def cached_get_artist_top_tracks(artist_name, limit):
    # reuse recent Last.fm results instead of repeating the same API request
    return get_artist_top_tracks(
        artist_name=artist_name,
        api_key=LASTFM_API_KEY,
        limit=limit
    )


@st.cache_data(ttl=3600, show_spinner=False)
def cached_get_similar_artists(artist_name, limit):
    # reuse recent Last.fm results instead of repeating the same API request
    return get_similar_artists(
        artist_name=artist_name,
        api_key=LASTFM_API_KEY,
        limit=limit
    )


@st.cache_data(ttl=3600, show_spinner=False)
def get_cached_artist_info(artist_name, api_key):
    """
    Retrieve artist information and cache it for one hour.

    This prevents the app from repeatedly requesting the same artist
    information whenever Streamlit reruns the page.
    """

    return get_artist_info(
        artist_name=artist_name,
        api_key=api_key
    )


def get_selected_artists(artist_one, artist_two, artist_three):
    # keep completed artist selections and remove duplicates
    selected_artists = []

    for artist in [artist_one, artist_two, artist_three]:
        if artist and artist not in selected_artists:
            selected_artists.append(artist)

    return selected_artists


def create_user_features(
    popularity_answer,
    acousticness_answer,
    danceability_answer,
    duration_answer,
    energy_answer,
    instrumentalness_answer,
    liveness_answer,
    loudness_answer,
    speechiness_answer,
    tempo_answer,
    valence_answer,
    key_answer, 
    mode_answer
):
    # convert the user's answers into the values expected by the model
    return {
        "popularity": convert_to_range(popularity_answer, 0, 100),
        "acousticness": convert_to_zero_one(acousticness_answer),
        "danceability": convert_to_zero_one(danceability_answer),
        "duration_ms": convert_to_range(duration_answer, 120000, 360000),
        "energy": convert_to_zero_one(energy_answer),
        "instrumentalness": convert_to_zero_one(instrumentalness_answer),
        "liveness": convert_to_zero_one(liveness_answer),
        "loudness": convert_to_range(loudness_answer, -30, 0),
        "speechiness": convert_to_zero_one(speechiness_answer),
        "tempo": convert_to_range(tempo_answer, 60, 200),
        "valence": convert_to_zero_one(valence_answer),
        "key": "C" if key_answer == "No preference" else key_answer,
        "mode": mode_answer
    }


def predict_top_genres(user_features, number_of_genres=3):
    # create one correctly ordered row for the CatBoost model
    input_df = pd.DataFrame([user_features])
    input_df = input_df[model_info["feature_columns"]]

    genre_probabilities = model.predict_proba(input_df)[0]
    top_indices = np.argsort(genre_probabilities)[-number_of_genres:][::-1]
    predictions = []

    for genre_index in top_indices:
        predictions.append({
            "genre": model.classes_[genre_index],
            "probability": genre_probabilities[genre_index] * 100
        })

    return predictions


def calculate_playlist_split(playlist_length, familiarity_answer):
    # divide the playlist between chosen and similar artists
    familiarity_ratio = familiarity_answer / 10
    chosen_artist_count = round(playlist_length * familiarity_ratio)
    similar_artist_count = playlist_length - chosen_artist_count

    return chosen_artist_count, similar_artist_count


def remove_duplicate_tracks(tracks):
    # a song is a duplicate only when its track and artist both match
    unique_tracks = []
    seen_tracks = set()

    for track in tracks:
        track_name = track.get("track")
        artist_name = track.get("artist")

        if not track_name or not artist_name:
            continue

        track_identity = (
            track_name.strip().lower(),
            artist_name.strip().lower()
        )

        if track_identity not in seen_tracks:
            seen_tracks.add(track_identity)
            unique_tracks.append(track)

    return unique_tracks


def interleave_track_lists(track_lists):
    # take one track from each artist at a time so one artist cannot dominate
    interleaved_tracks = []
    longest_list_length = max(
        (len(track_list) for track_list in track_lists),
        default=0
    )

    for track_position in range(longest_list_length):
        for track_list in track_lists:
            if track_position < len(track_list):
                interleaved_tracks.append(track_list[track_position])

    return interleaved_tracks


def build_chosen_artist_candidates(selected_artists, chosen_artist_count):
    # no chosen-artist candidates are needed at familiarity zero
    if chosen_artist_count == 0:
        return []

    tracks_per_artist = math.ceil(
        chosen_artist_count / len(selected_artists)
    )

    # request a small buffer in case Last.fm returns duplicates
    candidate_limit = min(tracks_per_artist + 5, 50)
    artist_track_lists = []

    for artist in selected_artists:
        artist_tracks = cached_get_artist_top_tracks(
            artist_name=artist,
            limit=candidate_limit
        )

        artist_track_lists.append(artist_tracks)

    candidates = interleave_track_lists(artist_track_lists)

    return remove_duplicate_tracks(candidates)


def build_similar_artist_candidates(selected_artists, similar_artist_count):
    # no similar-artist candidates are needed at familiarity ten
    if similar_artist_count == 0:
        return []

    similar_artist_names = []

    target_similar_artist_count = 10

    artists_per_selected_artist = math.ceil(
        target_similar_artist_count / len(selected_artists)
    )
    
    for selected_artist in selected_artists:
        artists = cached_get_similar_artists(
            artist_name=selected_artist,
            limit=artists_per_selected_artist
        )

        for artist in artists:
            if (
                artist not in selected_artists
                and artist not in similar_artist_names
            ):
                similar_artist_names.append(artist)

            if len(similar_artist_names) >= target_similar_artist_count:
                break

        if len(similar_artist_names) >= target_similar_artist_count:
            break

    if not similar_artist_names:
        return []

    # build a pool around three times larger than the required playlist section
    candidate_pool_size = max(similar_artist_count * 3, 50)
    tracks_per_artist = math.ceil(
        candidate_pool_size / len(similar_artist_names)
    )
    candidate_limit = min(tracks_per_artist, 50)
    artist_track_lists = []

    for artist in similar_artist_names:
        artist_tracks = cached_get_artist_top_tracks(
            artist_name=artist,
            limit=candidate_limit
        )

        for track in artist_tracks:
            track["source"] = "similar_artist"

        artist_track_lists.append(artist_tracks)

    candidates = interleave_track_lists(artist_track_lists)

    return remove_duplicate_tracks(candidates)


def create_recommended_playlist(
    chosen_candidates,
    similar_candidates,
    chosen_artist_count,
    similar_artist_count
):
    # take the required number from each pool and combine both sections
    chosen_tracks = chosen_candidates[:chosen_artist_count]
    similar_tracks = similar_candidates[:similar_artist_count]

    return chosen_tracks + similar_tracks




# ----- MUSIC QUESTIONS -----

st.subheader(
    "First off, answer these questions about what kind of music you like"
)

with st.container():

    popularity_answer = st.slider(
        "Do you prefer hidden gems or very popular songs?",
        min_value=1,
        max_value=10,
        value=5,
        help="1 means hidden gems, while 10 means very popular songs."
    )

    acousticness_answer = st.slider(
        "How much do you enjoy acoustic instruments?",
        min_value=1,
        max_value=10,
        value=5,
        help="1 means mostly electronic sounds, while 10 means very acoustic."
    )

    danceability_answer = st.slider(
        "How easy should your music be to dance to?",
        min_value=1,
        max_value=10,
        value=5
    )

    duration_answer = st.slider(
        "Do you prefer shorter or longer songs?",
        min_value=1,
        max_value=10,
        value=5,
        help="1 means shorter songs, while 10 means longer songs."
    )

    energy_answer = st.slider(
        "How energetic do you prefer your music?",
        min_value=1,
        max_value=10,
        value=5
    )

    instrumentalness_answer = st.slider(
        "How much do you prefer music without vocals?",
        min_value=1,
        max_value=10,
        value=5,
        help="1 means vocal-focused, while 10 means mostly instrumental."
    )

    liveness_answer = st.slider(
        "How much do you enjoy a live-performance feeling?",
        min_value=1,
        max_value=10,
        value=5
    )

    loudness_answer = st.slider(
        "How soft or powerful should your music sound?",
        min_value=1,
        max_value=10,
        value=5,
        help="1 means soft and quiet, while 10 means loud and powerful."
    )

    speechiness_answer = st.slider(
        "How much spoken or rapped content do you prefer?",
        min_value=1,
        max_value=10,
        value=5
    )

    tempo_answer = st.slider(
        "How slow or fast do you prefer your songs?",
        min_value=1,
        max_value=10,
        value=5,
        help="1 means very slow, while 10 means very fast."
    )

    valence_answer = st.slider(
        "How sad or positive should your music sound?",
        min_value=1,
        max_value=10,
        value=5,
        help="1 means darker or sadder, while 10 means happier and more positive."
    )

    mode_answer = st.radio(
        "Which overall sound do you usually prefer?",
        options=["Major", "Minor"],
        help="Major often sounds brighter, while Minor often sounds moodier."
    )

    key_answer = st.selectbox(
        "Which musical key do you prefer? (optional)",
        options=[
            "No preference",
            "C",
            "C#",
            "D",
            "D#",
            "E",
            "F",
            "F#",
            "G",
            "G#",
            "A",
            "A#",
            "B"
        ],
        index=0,
        help=(
            "Leave this as 'No preference' if you do not know "
            "which musical key you prefer."
        )
    )

if "preferences_completed" not in st.session_state:
    st.session_state["preferences_completed"] = False

if not st.session_state["preferences_completed"]:
    if st.button("Continue to artist selection"):
        st.session_state["preferences_completed"] = True
        st.rerun()

    # Keep every later section hidden until the first section is completed
    st.stop()


st.subheader("Choose three artists you like")

st.write(
    "Start typing an artist's name and select the correct artist "
    "from the suggestions."
)

# streamlit-searchbox renders inside its own component, so page CSS cannot
# reliably reach these fields. Style them through the component's API.
ARTIST_SEARCH_STYLE = {
    "searchbox": {
        "control": {
            "backgroundColor": "#FFF9F6",
            "border": "1px solid #BF8759",
            "boxShadow": "none",
            "&:hover": {"border": "1px solid #BF8759"},
        },
        "input": {"color": "#382B2B"},
        "singleValue": {"color": "#382B2B"},
        "placeholder": {"color": "#765F53"},
        "menuList": {"backgroundColor": "#FFF9F6"},
        "option": {"color": "#382B2B"},
    },
}

artist_one = st_searchbox(
    lambda search_term: search_artists(search_term, []),
    key="artist_one_search",
    placeholder="Search for your first artist...",
    style_overrides=ARTIST_SEARCH_STYLE,
)

artist_two = st_searchbox(
    lambda search_term: search_artists(search_term, [artist_one]),
    key="artist_two_search",
    placeholder="Search for your second artist...",
    style_overrides=ARTIST_SEARCH_STYLE,
)

artist_three = st_searchbox(
    lambda search_term: search_artists(
        search_term,
        [artist_one, artist_two]
    ),
    key="artist_three_search",
    placeholder="Search for your third artist...",
    style_overrides=ARTIST_SEARCH_STYLE,
)

predict_genres_button = st.button("Predict my genres")


if predict_genres_button:

    entered_artists = [artist_one, artist_two, artist_three]

    if any(not artist or not artist.strip() for artist in entered_artists):
        st.error("Please select all three artists before predicting your genres.")
        st.stop()
    
    normalised_artists = [
        artist.strip().lower()
        for artist in entered_artists
    ]
    
    if len(normalised_artists) != len(set(normalised_artists)):
        st.error("Please select each artist only once.")
        st.stop()
    
    selected_artists = get_selected_artists(
        artist_one,
        artist_two,
        artist_three
    )
    
    if len(selected_artists) != 3:
        st.error("Please select three different artists.")
        st.stop()

    user_features = create_user_features(
        popularity_answer,
        acousticness_answer,
        danceability_answer,
        duration_answer,
        energy_answer,
        instrumentalness_answer,
        liveness_answer,
        loudness_answer,
        speechiness_answer,
        tempo_answer,
        valence_answer,
        key_answer, 
        mode_answer
    )

    genre_predictions = predict_top_genres(user_features)
    evil_user_features = create_evil_user_features(user_features)
    evil_genre_predictions = predict_top_genres(evil_user_features)

    st.session_state["user_features"] = user_features
    st.session_state["evil_user_features"] = evil_user_features
    st.session_state["selected_artists"] = selected_artists
    st.session_state["genre_predictions"] = genre_predictions
    st.session_state["evil_genre_predictions"] = evil_genre_predictions

    # Remove an older playlist when the user predicts a new profile
    st.session_state.pop("recommended_playlist", None)
    st.session_state.pop("evil_twin_playlist", None)


if "genre_predictions" in st.session_state:
    st.subheader("Your top three genres")

    render_genre_cards(
        st.session_state["genre_predictions"],
        GENRE_DESCRIPTIONS,
        "A genre matched to your music preferences."
    )

    st.subheader("What this says about your music personality")
    user_personality = describe_music_personality(
        st.session_state["user_features"]
    )
    render_personality_card(user_personality)

    st.subheader("Let's add some extra controls")

    playlist_length = st.slider(
        "How many songs should your playlist contain?",
        min_value=15,
        max_value=40,
        value=20,
        step=1,
        key="playlist_length"
    )

    familiarity_answer = st.slider(
        "How much of your playlist should feature your chosen artists?",
        min_value=0,
        max_value=10,
        value=5,
        key="familiarity_answer",
        help=(
            "0 means NO songs from your artists. "
            "10 means tracks ONLY from the artists you selected. "
            "This does NOT affect your predicted genres."
        )
    )

    generate_playlist_button = st.button("Generate my playlist")

    if generate_playlist_button:
        selected_artists = st.session_state["selected_artists"]

        chosen_artist_count, similar_artist_count = calculate_playlist_split(
            playlist_length,
            familiarity_answer
        )

        unique_chosen_candidates = build_chosen_artist_candidates(
            selected_artists,
            chosen_artist_count
        )

        unique_similar_candidates = build_similar_artist_candidates(
            selected_artists,
            similar_artist_count
        )

        recommended_playlist = create_recommended_playlist(
            unique_chosen_candidates,
            unique_similar_candidates,
            chosen_artist_count,
            similar_artist_count
        )

        st.session_state["recommended_playlist"] = recommended_playlist
        st.session_state.pop("evil_twin_playlist", None)


if "recommended_playlist" in st.session_state:
    recommended_playlist = st.session_state["recommended_playlist"]

    if len(recommended_playlist) < st.session_state["playlist_length"]:
        st.warning(
            "Last.fm did not return enough unique tracks to fill the "
            "requested playlist length."
        )

    if recommended_playlist:
        st.subheader("Your recommended playlist")

        render_playlist(recommended_playlist)

        if st.button("But what would your 'other you' listen to? 😈"):
            with st.spinner("Summoning the opposing playlist..."):
                evil_candidate_pool = build_evil_candidate_pool(
                    evil_genre_predictions=st.session_state[
                        "evil_genre_predictions"
                    ],
                    api_key=LASTFM_API_KEY,
                    playlist_length=st.session_state["playlist_length"]
                )

                evil_twin_playlist = create_evil_twin_playlist(
                    candidate_pool=evil_candidate_pool,
                    playlist_length=st.session_state["playlist_length"],
                    selected_artists=st.session_state["selected_artists"],
                    normal_playlist=recommended_playlist
                )

                evil_twin_playlist = add_track_metrics(
                    playlist=evil_twin_playlist,
                    api_key=LASTFM_API_KEY
                )

                st.session_state["evil_twin_playlist"] = (
                    evil_twin_playlist
                )
                st.session_state["active_page"] = "evil"

            st.rerun()
