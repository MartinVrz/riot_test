"""
Streamlit frontend for learning.ipynb's Riot API functions.

This file is new - it doesn't change anything from the notebook. It just
calls the functions from riot_api.py (an unmodified copy of your working
notebook code) and displays the results nicely.

Run with:
    streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import datetime as dt

import riot_api as api

st.set_page_config(page_title="LoL Stats Dashboard", page_icon="🎮", layout="wide")

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .main { background-color: #0a1428; }
    h1, h2, h3 { color: #c8aa6e; }
    .stMetric { background-color: #1e2328; border-radius: 8px; padding: 10px; }
    .champ-card {
        background-color: #1e2328;
        border: 1px solid #3c3c41;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 10px;
    }
    .match-win { border-left: 5px solid #0ac8b9; }
    .match-loss { border-left: 5px solid #e84057; }
</style>
""", unsafe_allow_html=True)

st.title("🎮 League of Legends Stats Dashboard")

# ---------------------------------------------------------------------------
# Champion id -> name / icon lookup (Data Dragon), cached
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def load_champion_map():
    import requests
    versions = requests.get("https://ddragon.leagueoflegends.com/api/versions.json").json()
    latest = versions[0]
    data = requests.get(
        f"https://ddragon.leagueoflegends.com/cdn/{latest}/data/en_US/champion.json"
    ).json()["data"]
    id_to_name = {}
    id_to_icon = {}
    for champ in data.values():
        cid = int(champ["key"])
        id_to_name[cid] = champ["name"]
        id_to_icon[cid] = (
            f"https://ddragon.leagueoflegends.com/cdn/{latest}/img/champion/{champ['image']['full']}"
        )
    return id_to_name, id_to_icon, latest


try:
    CHAMP_NAME, CHAMP_ICON, DDRAGON_VERSION = load_champion_map()
except Exception:
    CHAMP_NAME, CHAMP_ICON, DDRAGON_VERSION = {}, {}, None

# ---------------------------------------------------------------------------
# Sidebar - lookup
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Look up a player")
    gamename = st.text_input("Game name", value="iliketojump")
    tagline = st.text_input("Tag line", value="LEAP")
    match_count = st.slider("Matches to load", min_value=1, max_value=20, value=5)
    search = st.button("Search", type="primary", use_container_width=True)

if not api.api_key:
    st.error(
        "No `riot_api` key found in the environment. Make sure your `.env` "
        "file (the one `load_dotenv()` reads) sits next to this script and "
        "contains `riot_api=YOUR_KEY`."
    )
    st.stop()

if "puuid" not in st.session_state:
    st.session_state.puuid = None
    st.session_state.account = None

if search:
    with st.spinner("Looking up player..."):
        try:
            puuid = api.get_puuid(gamename, tagline, api.api_key)
            account = api.get_opgg(puuid)
            st.session_state.puuid = puuid
            st.session_state.account = account
        except Exception as e:
            st.session_state.puuid = None
            st.error(f"Couldn't find that player: {e}")

puuid = st.session_state.puuid

if not puuid:
    st.info("Enter a game name and tag line in the sidebar, then hit **Search**.")
    st.stop()

account = st.session_state.account
st.subheader(f"{account.get('gameName', gamename)} #{account.get('tagLine', tagline)}")
st.caption(f"puuid: `{puuid}`")

tab_mastery, tab_matches = st.tabs(["🏆 Champion Mastery", "⚔️ Match History"])

# ---------------------------------------------------------------------------
# Mastery tab
# ---------------------------------------------------------------------------
with tab_mastery:
    with st.spinner("Loading mastery..."):
        try:
            mastery_data = api.mastery_list(puuid)
        except Exception as e:
            mastery_data = None
            st.error(f"Couldn't load mastery: {e}")

    if mastery_data:
        df = pd.DataFrame(mastery_data).sort_values("championPoints", ascending=False)
        max_points = df["championPoints"].max()

        for _, row in df.head(15).iterrows():
            cid = row["championId"]
            name = CHAMP_NAME.get(cid, f"Champion {cid}")
            icon = CHAMP_ICON.get(cid)
            last_played = dt.datetime.fromtimestamp(row["lastPlayTime"] / 1000).strftime("%Y-%m-%d")

            col_icon, col_info = st.columns([1, 8])
            with col_icon:
                if icon:
                    st.image(icon, width=56)
            with col_info:
                st.markdown(f"**{name}** — Level {row['championLevel']}")
                st.progress(min(row["championPoints"] / max_points, 1.0))
                st.caption(f"{row['championPoints']:,} pts · last played {last_played}")
        st.divider()
        st.dataframe(
            df[["championId", "championLevel", "championPoints"]].reset_index(drop=True),
            use_container_width=True,
        )

# ---------------------------------------------------------------------------
# Match history tab
# ---------------------------------------------------------------------------
with tab_matches:
    with st.spinner("Loading matches..."):
        try:
            match_ids = api.matches(region=api.region, puuid=puuid, start=0, count=match_count)
        except Exception as e:
            match_ids = None
            st.error(f"Couldn't load match list: {e}")

    if match_ids:
        for match_id in match_ids:
            try:
                game = api.get_match_data(matchId=match_id, region=api.region)
                info = game["info"]
                metadata = game["metadata"]
                p_index = metadata["participants"].index(puuid)
                player = info["participants"][p_index]
            except Exception as e:
                st.warning(f"Skipped {match_id}: {e}")
                continue

            win = player["win"]
            css_class = "match-win" if win else "match-loss"
            champ_name = player.get("championName", "Unknown")
            duration_min = info["gameDuration"] // 60
            duration_sec = info["gameDuration"] % 60

            st.markdown(f'<div class="champ-card {css_class}">', unsafe_allow_html=True)
            c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
            with c1:
                st.markdown(f"**{champ_name}**")
                st.caption("Victory" if win else "Defeat")
            with c2:
                st.metric(
                    "KDA",
                    f"{player['kills']}/{player['deaths']}/{player['assists']}",
                )
            with c3:
                st.metric("CS", player["totalMinionsKilled"] + player["neutralMinionsKilled"])
            with c4:
                st.metric("Duration", f"{duration_min}m {duration_sec}s")
            st.markdown("</div>", unsafe_allow_html=True)
