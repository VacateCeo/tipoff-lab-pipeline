import streamlit as st
import pandas as pd
import numpy as np
import pickle
import sys
import os

sys.path.insert(0, "src")
from build_features import get_rolling_team_stats
from predict import predict_today, FEATURE_COLS, PHRASE_TEMPLATES

st.set_page_config(
    page_title="NBA Watchability Score",
    page_icon="🏀",
    layout="centered"
)

@st.cache_resource
def load_model():
    with open("data/model.pkl", "rb") as f:
        return pickle.load(f)

@st.cache_data
def load_games():
    games = pd.read_parquet("data/games.parquet")
    games["date"] = pd.to_datetime(games["date"])
    return games

model = load_model()
games = load_games()

NBA_TEAMS = sorted([
    "ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DAL", "DEN",
    "DET", "GSW", "HOU", "IND", "LAC", "LAL", "MEM", "MIA",
    "MIL", "MIN", "NOP", "NYK", "OKC", "ORL", "PHI", "PHX",
    "POR", "SAC", "SAS", "TOR", "UTA", "WAS"
])

st.title("🏀 NBA Watchability Score")
st.markdown("*Which game should you watch tonight?*")
st.divider()

st.subheader("Add Tonight's Games")

if "matchups" not in st.session_state:
    st.session_state.matchups = []

with st.form("add_game"):
    col1, col2 = st.columns(2)
    with col1:
        home = st.selectbox("Home Team", NBA_TEAMS, index=NBA_TEAMS.index("BOS"))
        spread = st.number_input("Spread (home)", value=5.0, step=0.5)
    with col2:
        away = st.selectbox("Away Team", NBA_TEAMS, index=NBA_TEAMS.index("MIA"))
        total = st.number_input("Vegas Total", value=217.0, step=0.5)

    game_date = st.date_input("Game Date")
    submitted = st.form_submit_button("Add Game")

    if submitted:
        if home == away:
            st.error("Home and away teams must be different.")
        else:
            st.session_state.matchups.append((home, away, spread, total, str(game_date)))
            st.success(f"Added: {away} @ {home}")

if st.session_state.matchups:
    st.divider()
    st.subheader("Tonight's Rankings")

    all_results = []
    for home, away, spread, total, date in st.session_state.matchups:
        result = predict_today(date, [(home, away, spread, total)], games, model)
        if result:
            all_results.extend(result)

    all_results.sort(key=lambda x: x["watchability"], reverse=True)

    for i, r in enumerate(all_results):
        score = r["watchability"]
        if score >= 7:
            color = "🟢"
        elif score >= 5:
            color = "🟡"
        else:
            color = "🔴"

        st.markdown(f"### {color} {score:.1f}/10 — {r['away_team']} @ {r['home_team']}")
        if r["reasons"]:
            st.markdown(f"*{', '.join(r['reasons'])}*")
        st.divider()

    if st.button("Clear All Games"):
        st.session_state.matchups = []
        st.rerun()