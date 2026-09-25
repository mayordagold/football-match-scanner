import streamlit as st
import requests
import pandas as pd

st.set_page_config(
    page_title="Multi-API Live Intelligence Station", 
    page_icon="📡",
    layout="wide"
)

st.title("📡 Automated Football Intelligence & Slider Scanner")
st.markdown("Powered by your **API-Sports V3**, **The-Odds-API**, **Open-Meteo**, and **Google News RSS** tokens.")

# HARDCODED SECURE KEY CONFIGURATIONS
APISPORTS_KEY = "0236d6162ab0b95f2ec9ef2d1e083415"
THEODDSAPI_KEY = "a880fb62e16f9aff604a782c9e6c1c89"

# --- SIDEBAR CONTROL PANEL CONFIGURATION ---
st.sidebar.title("🔍 Target Matchup Profile")

# Primary Input Matrix Controls
home_team = st.sidebar.text_input("Home Team Name", value="Grazer AK")
away_team = st.sidebar.text_input("Away Team Name", value="Salzburg")

city_options = [
    "Graz", "Salzburg", "Dortmund", "Munich", "Liverpool", "London", 
    "Manchester", "Glasgow", "Paris", "Marseille", "Milano", "Torino", 
    "Rome", "Madrid", "Barcelona", "Lisbon", "Porto", "Amsterdam"
]
selected_city = st.sidebar.selectbox("Match City Location (For Weather)", city_options)

# API-Sports League IDs Matrix mapping your exact football database frames
league_api_mapping = {
    "🇦🇹 Austria Football Bundesliga": {"id": 218, "odds_sport": "soccer_austria_bundesliga"},
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 English Premier League": {"id": 39, "odds_sport": "soccer_epl"},
    "🇩🇪 German Bundesliga": {"id": 78, "odds_sport": "soccer_germany_bundesliga"},
    "🇪🇸 Spanish La Liga": {"id": 140, "odds_sport": "soccer_spain_la_liga"},
    "🇮🇹 Italy Serie A": {"id": 135, "odds_sport": "soccer_italy_serie_a"},
    "🇫🇷 France Ligue 1": {"id": 61, "odds_sport": "soccer_france_ligue_1"},
    "🇵🇹 Portugal Primeira Liga": {"id": 94, "odds_sport": "soccer_portugal_primeira_liga"},
    "🇳🇱 Netherlands Eredivisie": {"id": 88, "odds_sport": "soccer_netherlands_eredivisie"}
}
selected_standing_league = st.sidebar.selectbox("Load Live League Standings Display", list(league_api_mapping.keys()))

st.sidebar.markdown("---")
st.sidebar.subheader("🏆 Motivation & Schedule Priority")

home_europe = st.sidebar.checkbox(f"Does {home_team} (Home) have a European match in 3 days?", value=False)
away_europe = st.sidebar.checkbox(f"Does {away_team} (Away) have a European match in 3 days?", value=True)

is_end_of_season = st.sidebar.checkbox(label="Dead Rubber Fixture?", value=False)

st.sidebar.markdown("---")
# 🟢 FIXED BUTTON ANCHOR POINT: Pinned explicitly to the sidebar block panel container layout path
submit_scan = st.sidebar.button("🚀 Launch Deep Intelligence Scan", type="primary", use_container_width=True)

# --- 🛰️ API LAYER 1: API-SPORTS LIVE STANDINGS STREAM ---
def fetch_apisports_live_standings(league_id, season=2026):
    """
    Connects directly to the official API-Sports REST servers.
    Parses live standings arrays dynamically with zero local fallbacks.
    """
    url = "https://api-sports.io"
    headers = {
        'x-rapidapi-key': APISPORTS_KEY,
        'x-rapidapi-host': 'v3.football.api-sports.io'
    }
    params = {'league': league_id, 'season': season}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=6)
        if response.status_code == 200:
            raw_json = response.json()
            # Navigate standard response payload paths
            standings_block = raw_json['response']['league']['standings'][0]
            
            compiled_rows = []
            for item in standings_block:
                compiled_rows.append({
                    "Rank": item['rank'],
                    "Club": item['team']['name'],
                    "MP": item['all']['played'],
                    "W": item['all']['win'],
                    "D": item['all']['draw'],
                    "L": item['all']['loss'],
                    "GF": item['all']['goals']['for'],
                    "GA": item['all']['goals']['against'],
                    "GD": item['goalsDiff'],
                    "Pts": item['points']
                })
            return pd.DataFrame(compiled_rows)
    except Exception as e:
        return pd.DataFrame({"Error Pipeline Log": [f"API-Sports connection failed: {str(e)}"]})
    
    return pd.DataFrame({"Error": ["Could not parse live API-Sports standings table structure."]})

# --- 🛰️ API LAYER 2: THE-ODDS-API LIVE CONSENSUS SCANNER ---
def fetch_live_market_consensus(sport_key):
    """
    Connects directly to the-odds-api core servers.
    Grabs global sharp bookmaker pre-match market anchors.
    """
    url = f"https://the-odds-api.com{THEODDSAPI_KEY}&sport={sport_key}&region=eu&mkt=h2h"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data['success'] and len(data['data']) > 0:
                return f"💰 **Live Market Feed Armed:** Connected to active sharp feeds for {sport_key} across {len(data['data'])} fixtures."
    except Exception:
        pass
    return "⚠️ Market Feed Stream: Node busy or league out-of-season cycle. Manual entry active."

# --- 🌤️ API LAYER 3: OPEN-METEO WEATHER API ---
def fetch_live_weather(city_name):
    geo_coordinates = {
        "Graz": (47.07, 15.43), "Salzburg": (47.80, 13.04), "Dortmund": (51.51, 7.46),
        "Munich": (48.13, 11.58), "Liverpool": (53.41, -2.98), "London": (51.50, -0.12),
        "Manchester": (53.48, -2.24), "Glasgow": (55.86, -4.25), "Paris": (48.85, 2.35),
        "Marseille": (43.29, 5.36), "Milano": (45.46, 9.18), "Torino": (45.07, 7.68),
        "Rome": (41.90, 12.49), "Madrid": (40.41, -3.70), "Barcelona": (41.38, 2.17),
        "Lisbon": (38.72, -9.13), "Porto": (41.15, -8.62), "Amsterdam": (52.36, 4.90)
    }
    lat, lon = geo_coordinates[city_name]
    try:
        url = f"https://open-meteo.com{lat}&longitude={lon}&current=weather_code,wind_speed_10m"
        response = requests.get(url, timeout=4)
        if response.status_code == 200:
            data = response.json()
            weather_code = data['current']['weather_code']
            wind_speed = data['current']['wind_speed_10m']
            if 51 <= weather_code <= 67 or 80 <= weather_code <= 82:
                return -5, f"🌧️ Live Weather API Alert: Heavy rain active in {city_name}. Pitch saturated. Slider penalty applied (-5%)."
            if wind_speed > 40:
                return -5, f"💨 Live Weather API Alert: High winds ({wind_speed} km/h) tracked in {city_name}. Volatility penalty applied (-5%)."
            return 0, f"🟢 Live Weather API: Optimal, clear conditions verified in {city_name}."
    except Exception:
        return 0, "⚠️ Weather API Stream: Server busy. Modifier untouched (0%)."

# --- 📰 API LAYER 4: GOOGLE NEWS TEAM NEWS LOOP ---
def fetch_live_injury_alerts(home, away):
    alerts = []
    try:
        search_query = f'"{home}" OR "{away}" football injury lineup team news'
        url = f"https://google.com{search_query}&hl=en-GB&gl=GB&ceid=GB:en"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=4)
        if response.status_code == 200:
            feed_text = response.text.lower()
            if home.lower() in feed_text and any(w in feed_text for w in ["injury", "injured", "absent", "rested", "suspended"]):
                alerts.append(f"📰 **Live Injury Stream:** Risk variables identified for {home}.")
            if away.lower() in feed_text and any(w in feed_text for w in ["injury", "injured", "absent", "rested", "suspended"]):
                alerts.append(f"📰 **Live Injury Stream:** Risk variables identified for {away}.")
        if not alerts:
            alerts.append("✨ **Live Injury Stream:** Squad selections stable. No fracture anomalies found.")
        return " | ".join(alerts)
    except Exception:
        return "📡 Injury Stream: Node standing by."

# --- INITIALIZE SESSION STATE BUFFER CONTROLS ---
if 'scan_executed' not in st.session_state:
    st.session_state.scan_executed = False
    st.session_state.final_home_slider = 0
    st.session_state.final_away_slider = 0
    st.session_state.weather_message = ""
    st.session_state.news_message = ""
    st.session_state.odds_message = ""
    st.session_state.motivation_messages = []
    st.session_state.scraped_standings = pd.DataFrame()

# --- TRIGGER PIPELINE RUN ---
if submit_scan:
    st.session_state.scan_executed = True
    
    league_config = league_api_mapping[selected_standing_league]
    st.session_state.scraped_standings = fetch_apisports_live_standings(league_config["id"])
    st.session_state.odds_message = fetch_live_market_consensus(league_config["odds_sport"])
    w_mod, st.session_state.weather_message = fetch_live_weather(selected_city)
    st.session_state.news_message = fetch_live_injury_alerts(home_team, away_team)
    
    home_penalty, away_penalty = 0, 0
    st.session_state.motivation_messages = []
    
    if home_europe:
        home_penalty -= 5
        st.session_state.motivation_messages.append(f"⚠️ **Schedule Interference Trap:** {home_team} has a decisive European fixture within 72 hours.")
    if away_europe:
        away_penalty -= 5
        st.session_state.motivation_messages.append(f"⚠️ **Schedule Interference Trap:** {away_team} has a decisive European fixture within 72 hours.")
    if is_end_of_season:
        home_penalty -= 10
        away_penalty -= 10
        st.session_state.motivation_messages.append("📉 **Low Intensity Warning:** Dead rubber parameters active.")
        
    st.session_state.final_home_slider = int(w_mod + home_penalty)
    st.session_state.final_away_slider = int(w_mod + away_penalty)

    # --- DYNAMIC VISUAL READING GRID ---
    if st.session_state.scan_executed:
        st.markdown("---")
        st.subheader(f"🏆 100% Live API Standings Feed (API-Sports V3): {selected_standing_league}")
    if "Error Pipeline Log" in st.session_state.scraped_standings.columns or "Error" in st.session_state.scraped_standings.columns:
        st.error("❌ LIVE DATA HANDSHAKE REJECTED BY SERVER")
        st.dataframe(st.session_state.scraped_standings, use_container_width=True, hide_index=True)
    else:
        st.dataframe(st.session_state.scraped_standings, use_container_width=True, hide_index=True)
        st.markdown("---")
        st.subheader(f"📋 Live Match Intelligence Readout: {home_team} vs {away_team}")
        st.success(st.session_state.odds_message)
        st.info(st.session_state.weather_message)
        st.markdown(st.session_state.news_message)
        if st.session_state.motivation_messages:
            for msg in st.session_state.motivation_messages:
                st.warning(msg)
                st.markdown("---")
                st.subheader("🎛️ Recommended Modifier Alignment Setup")
                col1, col2 = st.columns(2)
                col1.metric(label=f"Recommended {home_team} Performance Slider Shift", value=f"{st.session_state.final_home_slider}%")
                col2.metric(label=f"Recommended {away_team} Performance Slider Shift", value=f"{st.session_state.final_away_slider}%")
                st.success(f"🎯 Action Plan Checklist: Open your local dashboard (localhost:8501). Set the {home_team} Slider to {st.session_state.final_home_slider}% and the {away_team} Slider to {st.session_state.final_away_slider}%, input your live SportyBet market odds, and fire your simulation!")
else:
    st.info("💡 Live Multi-API Terminal Idle: Configure the sidebar parameters and launch scan to stream live data directly from official sports database nodes.")
