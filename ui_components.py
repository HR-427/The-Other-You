#----- FILE PURPOSE -----

"""
Reusable Streamlit presentation components for the music recommender.

This file contains the HTML-building code. Application logic remains in
genre_app.py, while colours and layout rules live in styles.css.
"""


# ----- IMPORTS -----

from html import escape
import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from preview_api import get_track_preview


# ----- FUNCTIONS -----

def load_theme(theme_name):
    # load the shared stylesheet and activate the requested page theme

    if theme_name not in {"normal", "evil"}:
        raise ValueError("theme_name must be either 'normal' or 'evil'")

    stylesheet_path = Path(__file__).with_name("styles.css")
    stylesheet = stylesheet_path.read_text(encoding="utf-8")

    # Render the style tag separately and place it at the start of its HTML
    # block. Streamlit may print CSS as page text when a style tag follows
    # another HTML element in the same Markdown string.
    st.markdown(
        f"<style>\n{stylesheet}\n</style>",
        unsafe_allow_html=True
    )

    st.markdown(
        f'<div class="theme-marker {theme_name}-theme"></div>',
        unsafe_allow_html=True
    )


def render_welcome_page():
    # display the introductory content shown before the questionnaire

    st.markdown(
        '<section class="welcome-page">'
        '<div class="welcome-symbols">😇 <span>vs</span> 😈</div>'
        '<h1>The Other You</h1>'
        '<p>Discover the genres and songs that match your music taste, '
        'then uncover the playlist your musical opposite would choose.</p>'
        '</section>',
        unsafe_allow_html=True
    )


def render_personality_card(description):
    # display a music-personality description inside a themed card

    safe_description = escape(str(description))
    st.markdown(
        f'<div class="personality-card">{safe_description}</div>',
        unsafe_allow_html=True
    )


def render_genre_cards(predictions, genre_descriptions, fallback_description):
    """Display the three predicted genres as equally sized cards."""

    genre_columns = st.columns(3)

    for position, (column, prediction) in enumerate(
        zip(genre_columns, predictions),
        start=1
    ):
        genre = str(prediction.get("genre", "Unknown"))
        description = genre_descriptions.get(genre, fallback_description)
        probability = float(prediction.get("probability", 0))

        with column:
            st.markdown(
                '<div class="genre-card">'
                f'<div class="genre-rank">#{position}</div>'
                f'<div class="genre-name">{escape(genre)}</div>'
                '<div class="genre-probability">'
                f'{probability:.2f}% match'
                '</div>'
                f'<div class="genre-description">{escape(description)}</div>'
                '</div>',
                unsafe_allow_html=True
            )


@st.cache_data(ttl=3600, show_spinner=False)
def _get_cached_track_preview(track_name, artist_name):
    # retrieve a preview once, then reuse it for one hour

    return get_track_preview(
        track_name=track_name,
        artist_name=artist_name
    )


def _render_track_card(track, position, include_genre):
    # render one expandable track card with an on-demand preview

    track_name = str(track.get("track", "Unknown track"))
    artist_name = str(track.get("artist", "Unknown artist"))
    track_url = str(track.get("url", ""))
    listeners = int(track.get("listeners", 0) or 0)
    playcount = int(track.get("playcount", 0) or 0)

    card_label = f"{position:02d}    |    {track_name} — {artist_name}"
    safe_key = "".join(
        character if character.isalnum() else "_"
        for character in f"{position}_{track_name}_{artist_name}"
    )
    preview_state_key = f"track_preview_result_{safe_key}"

    with st.expander(card_label):
        stat_columns = st.columns([1, 1, 1.2, 1.2])

        with stat_columns[0]:
            st.caption("LISTENERS")
            st.write(f"**{listeners:,}**")

        with stat_columns[1]:
            st.caption("PLAYS")
            st.write(f"**{playcount:,}**")

        with stat_columns[2]:
            if track_url:
                st.link_button(
                    "Last.fm ↗",
                    track_url,
                    width="stretch"
                )

        with stat_columns[3]:
            preview_clicked = st.button(
                "▶ Preview",
                key=f"track_preview_button_{safe_key}",
                width="stretch"
            )

        if preview_clicked:
            with st.spinner("Finding preview..."):
                st.session_state[preview_state_key] = (
                    _get_cached_track_preview(track_name, artist_name)
                )

        preview = st.session_state.get(preview_state_key)

        if preview:
            st.audio(preview["preview_url"], format="audio/m4a")
            st.caption("30-second preview provided courtesy of iTunes.")

            if preview.get("store_url"):
                st.markdown(
                    f'[View song on Apple Music ↗]({preview["store_url"]})'
                )
        elif preview_clicked:
            st.info("A preview could not be found for this song.")


def render_playlist(tracks, include_genre=False):
    # display expandable track cards in a responsive two-column grid

    for start_position in range(0, len(tracks), 2):
        track_columns = st.columns(2, gap="small")

        for column_offset, column in enumerate(track_columns):
            track_index = start_position + column_offset

            if track_index >= len(tracks):
                continue

            with column:
                _render_track_card(
                    track=tracks[track_index],
                    position=track_index + 1,
                    include_genre=include_genre
                )


def render_artist_cards(artists):
    # display artist information in a grid of expandable profile cards

    artist_cards = []

    for artist in artists:
        raw_artist_name = str(artist.get("name", "Unknown artist"))
        artist_name = escape(raw_artist_name)
        artist_initial = escape(raw_artist_name[:1].upper() or "?")
        listeners = int(artist.get("listeners", 0) or 0)
        playcount = int(artist.get("playcount", 0) or 0)

        biography = str(
            artist.get(
                "biography",
                "No artist biography is available."
            )
        ).strip()

        if not biography:
            biography = "No artist biography is available."

        # Keep expanded cards informative without allowing very long Last.fm
        # biographies to dominate the page.
        if len(biography) > 520:
            biography = biography[:517].rsplit(" ", 1)[0] + "..."

        biography = escape(biography)
        artist_url = escape(str(artist.get("url", "")), quote=True)
        tags = artist.get("tags", [])

        tag_chips = "".join(
            f'<span class="artist-tag">{escape(str(tag))}</span>'
            for tag in tags[:5]
        )

        if not tag_chips:
            tag_chips = '<span class="artist-tag">No tags available</span>'

        if artist_url:
            lastfm_link = (
                f'<a class="artist-link" href="{artist_url}" '
                'target="_blank" rel="noopener noreferrer">'
                'View on Last.fm ↗'
                '</a>'
            )
        else:
            lastfm_link = ""

        artist_cards.append(
            '<details class="artist-card">'
            '<summary class="artist-card-summary">'
            f'<span class="artist-avatar">{artist_initial}</span>'
            '<span class="artist-card-heading">'
            '<span class="artist-card-kicker">Artist profile</span>'
            f'<span class="artist-card-name">{artist_name}</span>'
            '</span>'
            '<span class="artist-card-chevron">⌄</span>'
            '</summary>'
            '<div class="artist-card-content">'
            '<div class="artist-statistics">'
            '<div class="artist-stat">'
            '<span>Listeners</span>'
            f'<strong>{listeners:,}</strong>'
            '</div>'
            '<div class="artist-stat">'
            '<span>Plays</span>'
            f'<strong>{playcount:,}</strong>'
            '</div>'
            '</div>'
            f'<div class="artist-tags">{tag_chips}</div>'
            f'<p class="artist-biography">{biography}</p>'
            f'{lastfm_link}'
            '</div>'
            '</details>'
        )

    # st.html bypasses Markdown parsing, so artist names containing symbols
    # such as the dollar sign in "Travi$ Scott" cannot corrupt the markup.
    st.html(
        '<div class="artist-card-grid">'
        + "".join(artist_cards)
        + '</div>'
    )


def _format_playlist_copy_text(title, tracks):
    # convert a complete playlist into clean text for the clipboard

    lines = [title, ""]

    for position, track in enumerate(tracks, start=1):
        track_name = str(track.get("track", "Unknown track"))
        artist_name = str(track.get("artist", "Unknown artist"))
        lines.append(f"{position}. {track_name} — {artist_name}")

    return "\n".join(lines)


def _combine_playlists(normal_playlist, evil_playlist):
    # alternate normal and evil-twin songs while retaining both labels

    combined_tracks = []
    longest_playlist = max(len(normal_playlist), len(evil_playlist))

    for position in range(longest_playlist):
        if position < len(normal_playlist):
            combined_tracks.append(("You", normal_playlist[position]))

        if position < len(evil_playlist):
            combined_tracks.append(("Evil Twin", evil_playlist[position]))

    return combined_tracks


def _format_combined_copy_text(normal_playlist, evil_playlist):
    # create the alternating combined-playlist clipboard text

    lines = ["YOU VS YOUR OTHER YOU 😇😈", ""]
    combined_tracks = _combine_playlists(normal_playlist, evil_playlist)

    for position, (source, track) in enumerate(combined_tracks, start=1):
        track_name = str(track.get("track", "Unknown track"))
        artist_name = str(track.get("artist", "Unknown artist"))
        lines.append(
            f"{position}. {track_name} — {artist_name} [{source}]"
        )

    return "\n".join(lines)


def _render_preview_tracks(tracks):
    # build the HTML for the first ten tracks of a playlist

    preview_rows = []

    for position, track in enumerate(tracks[:10], start=1):
        track_name = escape(str(track.get("track", "Unknown track")))
        artist_name = escape(str(track.get("artist", "Unknown artist")))

        preview_rows.append(
            '<div class="comparison-track">'
            f'<span class="comparison-number">{position:02d}</span>'
            '<span class="comparison-track-details">'
            f'<strong>{track_name}</strong>'
            f'<small>{artist_name}</small>'
            '</span>'
            '</div>'
        )

    return "".join(preview_rows)


def render_comparison_page(normal_playlist, evil_playlist):
    # show both previews and provide clipboard buttons for full playlists

    stylesheet_path = Path(__file__).with_name("styles.css")
    stylesheet = stylesheet_path.read_text(encoding="utf-8")

    normal_text = _format_playlist_copy_text(
        "MY PLAYLIST 😇",
        normal_playlist
    )
    evil_text = _format_playlist_copy_text(
        "MY OTHER YOU'S PLAYLIST 😈",
        evil_playlist
    )
    combined_text = _format_combined_copy_text(
        normal_playlist,
        evil_playlist
    )

    # Encoding the strings as JSON protects quotes and line breaks when they
    # are passed into the clipboard JavaScript.
    clipboard_data = json.dumps(
        {
            "normal": normal_text,
            "evil": evil_text,
            "combined": combined_text
        },
        ensure_ascii=False
    ).replace("<", "\\u003c")

    comparison_html = (
        '<!doctype html><html><head><meta charset="utf-8">'
        f'<style>{stylesheet}</style></head><body class="comparison-body">'
        '<main class="comparison-root">'
        '<div class="comparison-grid">'
        '<section class="comparison-panel normal-panel">'
        '<div class="comparison-panel-heading"><span>😇</span>'
        '<div><p>Your sound</p><h2>Your playlist</h2></div></div>'
        '<p class="comparison-caption">A preview of your first ten songs.</p>'
        '<div class="comparison-tracks">'
        f'{_render_preview_tracks(normal_playlist)}'
        '</div>'
        '<button class="copy-button normal-copy" '
        'onclick="copyPlaylist(\'normal\', this)">Copy full playlist</button>'
        '</section>'
        '<section class="comparison-panel evil-panel">'
        '<div class="comparison-panel-heading"><span>😈</span>'
        '<div><p>Your opposite</p><h2>Other You playlist</h2></div></div>'
        '<p class="comparison-caption">A preview of their first ten songs.</p>'
        '<div class="comparison-tracks">'
        f'{_render_preview_tracks(evil_playlist)}'
        '</div>'
        '<button class="copy-button evil-copy" '
        'onclick="copyPlaylist(\'evil\', this)">Copy full playlist</button>'
        '</section>'
        '</div>'
        '<section class="combined-choice">'
        '<div><p>Cannot choose a side?</p>'
        '<h3>Combine both worlds</h3>'
        '<span>The songs will alternate between you and your other you.</span>'
        '</div>'
        '<button class="copy-button combined-copy" '
        'onclick="copyPlaylist(\'combined\', this)">Copy combined playlist</button>'
        '</section>'
        '</main>'
        f'<script>const playlistTexts = {clipboard_data};'
        'async function copyPlaylist(key, button) {'
        'const originalText = button.textContent;'
        'try {'
        'if (navigator.clipboard && window.isSecureContext) {'
        'await navigator.clipboard.writeText(playlistTexts[key]);'
        '} else {'
        'const area = document.createElement("textarea");'
        'area.value = playlistTexts[key];'
        'area.style.position = "fixed"; area.style.opacity = "0";'
        'document.body.appendChild(area); area.select();'
        'document.execCommand("copy"); area.remove();'
        '}'
        'button.textContent = "Copied! ✓"; button.classList.add("copied");'
        'setTimeout(() => { button.textContent = originalText; '
        'button.classList.remove("copied"); }, 1800);'
        '} catch (error) {'
        'button.textContent = "Copy failed";'
        'setTimeout(() => { button.textContent = originalText; }, 1800);'
        '}}'
        '</script></body></html>'
    )

    components.html(comparison_html, height=1040, scrolling=False)


def add_vertical_space(height_rem=1.25):
    # keep a clear gap before each playlist section heading

    st.markdown(
        f'<div style="height: {max(float(height_rem), 4):g}rem;"></div>',
        unsafe_allow_html=True
    )


def scroll_to_top():
    """
    Scroll to the top of the page while accounting for Streamlit's header.
    """

    components.html(
        """
        <script>
            setTimeout(function () {
                window.frameElement.scrollIntoView({
                    behavior: "instant",
                    block: "start"
                });

                setTimeout(function () {
                    window.parent.scrollBy({
                        top: -100,
                        left: 0,
                        behavior: "instant"
                    });
                }, 50);
            }, 100);
        </script>
        """,
        height=0
    )
