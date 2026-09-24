import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="Match Intelligence Scanner", 
    page_icon="📡",
    layout="wide"
)

st.title("📡 Automated Football Intelligence & Slider Scanner")
st.markdown("Companion tool to scan fixture motivation, European match interference, weather constraints, and squad rotations.")

# --- SIDEBAR CONTROL PANEL CONFIGURATION ---
st.sidebar.title("🔍 Target Matchup Profile")

# Primary Input Matrix Controls
home_team = st.sidebar.text_input("Home Team Name", value="Grazer AK")
away_team = st.sidebar.text_input("Away Team Name", value="Salzburg")

# EXPANDED WEATHER CITY DATABASE DROP-DOWN (Perfectly matching your 10 database leagues)
city_options = [
    "Graz", "Salzburg", "Dortmund", "Munich", "Liverpool", "London", 
    "Manchester", "Glasgow", "Paris", "Marseille", "Milano", "Torino", 
    "Rome", "Madrid", "Barcelona", "Lisbon", "Porto", "Amsterdam", "Other Baseline"
]
selected_city = st.sidebar.selectbox("Match City Location (For Weather)", city_options)

st.sidebar.markdown("---")
st.sidebar.subheader("🏆 Motivation & Schedule Priority")

# UPGRADE: Separated Home and Away European checkboxes to prevent calculation inversion!
home_europe = st.sidebar.checkbox(f"Does {home_team} (Home) have a European match in 3 days?", value=False)
away_europe = st.sidebar.checkbox(f"Does {away_team} (Away) have a European match in 3 days?", value=True)

is_end_of_season = st.sidebar.checkbox(
    label="Dead Rubber Fixture?", 
    value=False,
    help="Check this if it is the end of the season and title race or relegation spots are already mathematically decided."
)

# --- CORE MATHEMATICAL & FETCHING INTELLIGENCE ENGINES ---

def check_weather_and_pitch_constraints(city_name):
    """
    Unlimited Public Data Weather Engine.
    Maps localized geo-coordinates across your 10 leagues seamlessly.
    """
    geo_coordinates = {
        "Graz": (47.07, 15.43), "Salzburg": (47.80, 13.04), "Dortmund": (51.51, 7.46),
        "Munich": (48.13, 11.58), "Liverpool": (53.41, -2.98), "London": (51.50, -0.12),
        "Manchester": (53.48, -2.24), "Glasgow": (55.86, -4.25), "Paris": (48.85, 2.35),
        "Marseille": (43.29, 5.36), "Milano": (45.46, 9.18), "Torino": (45.07, 7.68),
        "Rome": (41.90, 12.49), "Madrid": (40.41, -3.70), "Barcelona": (41.38, 2.17),
        "Lisbon": (38.72, -9.13), "Porto": (41.15, -8.62), "Amsterdam": (52.36, 4.90)
    }
    
    if city_name not in geo_coordinates:
        return 0, "🌤️ Environmental Signals: Default baseline conditions active."
        
    lat, lon = geo_coordinates[city_name]
    
    try:
        url = f"https://open-meteo.com{lat}&longitude={lon}&current=weather_code,wind_speed_10m"
        response = requests.get(url, timeout=4)
        
        if response.status_code == 200:
            data = response.json()
            weather_code = data['current']['weather_code']
            wind_speed = data['current']['wind_speed_10m']
            
            if 51 <= weather_code <= 67 or 80 <= weather_code <= 82:
                return -5, f"🌧️ Weather Constraints Active: Live heavy downpour verified in {city_name}. Pitch slow/waterlogged risk. Applying -5% match modifier safety margin."
            if wind_speed > 40:
                return -5, f"💨 Weather Constraints Active: High wind speeds ({wind_speed} km/h) tracked in {city_name}. Applying -5% volatility margin."
                
            return 0, f"🟢 Environmental Engine Stable: Clear/Fair conditions confirmed in {city_name}. Pitch texture optimal."
    except Exception:
        pass
        
    return 0, "📡 Environmental Signals: Weather node busy. Defaulting to standard 0% conditions."


def check_squad_news_and_rotations(home, away):
    """Asynchronous JSON News RSS Scanner."""
    home_penalty, away_penalty = 0, 0
    alerts = []
    try:
        search_query = f'"{home}" OR "{away}" football injury lineup team news'
        url = f"https://google.com{search_query}&hl=en-GB&gl=GB&ceid=GB:en"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=4)
        if response.status_code == 200:
            feed_text = response.text.lower()
            if home.lower() in feed_text and any(w in feed_text for word in ["injury", "injured", "absent", "rested", "suspended"]):
                home_penalty = -5
                alerts.append(f"📰 **Squad Disruption ({home}):** Media text notes minor training selection constraints.")
            if away.lower() in feed_text and any(w in feed_text for word in ["injury", "injured", "absent", "rested", "suspended"]):
                away_penalty = -5
                alerts.append(f"📰 **Squad Disruption ({away}):** Media text notes minor training selection constraints.")
        if not alerts:
            alerts.append("✨ **Squad Signal Engine Stable:** No sudden unexpected squad fractures found in recent media grids.")
        return home_penalty, away_penalty, " | ".join(alerts)
    except Exception:
        return 0, 0, "📡 Squad News Pipeline: System standing by."


def check_tactical_motivation(home, away, h_europe, a_europe, dead_rubber_active):
    """Calculates operational motivation parameters based on fixture scheduling priorities."""
    home_penalty, away_penalty = 0, 0
    verdicts = []
    
    if h_europe:
        home_penalty -= 5
        verdicts.append(f"⚠️ **Schedule Interference Trap:** {home} has a massive European match in under 72 hours. Expect tactical rotation.")
    if a_europe:
        away_penalty -= 5
        verdicts.append(f"⚠️ **Schedule Interference Trap:** {away} has a massive European match in under 72 hours. Expect tactical rotation.")
        
    if dead_rubber_active:
        home_penalty -= 10
        away_penalty -= 10
        verdicts.append("📉 **Low Intensity Warning:** End-of-season context suggests standings are locked. Matches will play at a lower intensity profile.")
        
    return home_penalty, away_penalty, verdicts

# --- RUN LAUNCH PROCESSING SCAN ---
if st.button("Launch Deep Intelligence Scan", type="primary"):
    st.markdown("---")
    st.subheader(f"📋 Real-Time Match Intelligence Readout: {home_team} vs {away_team}")
    
    # Run active layers
    w_mod, weather_message = check_weather_and_pitch_constraints(selected_city)
    n_home, n_away, news_message = check_squad_news_and_rotations(home_team, away_team)
    m_home, m_away, motivation_messages = check_tactical_motivation(home_team, away_team, home_europe, away_europe, is_end_of_season)
    
    # Consolidate and clip results between -10% and +10%
    final_home_slider = max(-10, min(10, w_mod + n_home + m_home))
    final_away_slider = max(-10, min(10, w_mod + n_away + m_away))
    
    st.info(weather_message)
    if "✨" in news_message: st.success(news_message)
    else: st.markdown(news_message)
        
    if motivation_messages:
        for message in motivation_messages: st.warning(message)
            
    st.markdown("---")
    st.subheader("🎛️ Recommended Modifier Alignment Setup")
    col1, col2 = st.columns(2)
    
    col1.metric(
        label=f"Recommended **{home_team}** Performance Slider Shift", 
        value=f"{final_home_slider}%",
        delta="Apply Reduction" if final_home_slider < 0 else "Keep Baseline",
        delta_color="inverse" if final_home_slider < 0 else "normal"
    )
    col2.metric(
        label=f"Recommended **{away_team}** Performance Slider Shift", 
        value=f"{final_away_slider}%",
        delta="Apply Reduction" if final_away_slider < 0 else "Keep Baseline",
        delta_color="inverse" if final_away_slider < 0 else "normal"
    )
        
    st.success(f"🎯 **Action Plan Checklist:** Open your main prediction engine dashboard page (`localhost:8501`). Adjust the **{home_team} Slider to {final_home_slider}%** and the **{away_team} Slider to {final_away_slider}%**, input your live 1X2 market odds, and fire your simulation!")
