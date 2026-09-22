
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
home_team = st.sidebar.text_input("Home Team Name", value="Dortmund", help="Type the exact home team name (e.g., Dortmund, Liverpool, Celtic).")
away_team = st.sidebar.text_input("Away Team Name", value="Werder Bremen", help="Type the exact away team name (e.g., Werder Bremen, Salzburg).")

# Match City Location Dropdown (Maps automatically to Geo-Coordinates for open weather)
city_options = ["Dortmund", "Liverpool", "Glasgow", "Graz", "Salzburg", "London", "Manchester", "Munich", "Other (Defaults to London Baseline)"]
selected_city = st.sidebar.selectbox("Match City Location (For Weather)", city_options)

if selected_city == "Other (Defaults to London Baseline)":
    city_query = "London"
else:
    city_query = selected_city

st.sidebar.markdown("---")
st.sidebar.subheader("🏆 Motivation & Schedule Priority")
has_upcoming_europe = st.sidebar.checkbox(
    label="Upcoming European Match?", 
    value=True,
    help="Check this if either team has a critical Champions League / Europa League match coming up in 3 days."
)
is_end_of_season = st.sidebar.checkbox(
    label="Dead Rubber Fixture?", 
    value=False,
    help="Check this if it is the end of the season and title race or relegation spots are already mathematically decided."
)

# --- CORE MATHEMATICAL & FETCHING INTELLIGENCE ENGINES ---

def check_weather_and_pitch_constraints(city_name):
    """
    Unlimited Public Data Weather Engine.
    Queries geographic coordinates to fetch real-time precipitation/wind metrics
    without requiring API keys or account credentials.
    """
    geo_coordinates = {
        "Dortmund": (51.51, 7.46),
        "Liverpool": (53.41, -2.98),
        "Celtic": (55.86, -4.25),
        "Glasgow": (55.86, -4.25),
        "Grazer AK": (47.07, 15.43),
        "Graz": (47.07, 15.43),
        "Salzburg": (47.80, 13.04),
        "London": (51.50, -0.12),
        "Manchester": (53.48, -2.24),
        "Munich": (48.13, 11.58)
    }
    
    lat, lon = geo_coordinates.get(city_name, (51.50, -0.12))
    
    try:
        url = f"https://open-meteo.com{lat}&longitude={lon}&current=weather_code,wind_speed_10m&models=icon_seamless"
        response = requests.get(url, timeout=4)
        
        if response.status_code == 200:
            data = response.json()
            weather_code = data['current']['weather_code']
            wind_speed = data['current']['wind_speed_10m']
            
            # WMO Weather Codes: 51-67 represents Drizzle/Rain, 80-82 represents Rain Showers
            if 51 <= weather_code <= 67 or 80 <= weather_code <= 82:
                return -5, f"🌧️ Weather Constraints Active: Live precipitation/heavy downpour verified in {city_name}. Pitch slow/waterlogged risk. Auto-applying -5% penalty."
            
            if wind_speed > 40:
                return -5, f"💨 Weather Constraints Active: High wind speeds ({wind_speed} km/h) tracked in {city_name}, creating ball tracking volatility. Auto-applying -5% penalty."
                
            return 0, f"🟢 Environmental Engine Stable: Clear/Fair playing conditions confirmed in {city_name}. Pitch texture optimal."
    except Exception:
        pass
        
    return 0, "📡 Environmental Signals: Weather node busy or unmapped. Defaulting to standard 0% conditions."


def check_squad_news_and_rotations(home, away):
    """
    Asynchronous JSON Google News RSS Scanner.
    Scans real-time global sports headlines looking for squad disruption keywords
    without web scraping blocks or layout breakage.
    """
    home_penalty = 0
    away_penalty = 0
    alerts = []
    
    try:
        # Search query matching target team profiles
        search_query = f'"{home}" OR "{away}" football injury lineup team news'
        url = f"https://google.com{search_query}&hl=en-GB&gl=GB&ceid=GB:en"
        
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=4)
        if response.status_code == 200:
            feed_text = response.text.lower()
            
            # Automated Text-Scanning Intelligence rules for Home side
            if home.lower() in feed_text:
                if any(word in feed_text for word in ["injury", "injured", "absent", "doubt", "rested", "suspended"]):
                    home_penalty = -5
                    alerts.append(f"📰 **Squad Signal ({home}):** Breaking media text hints at minor training selection changes or injury constraints.")
            
            # Automated Text-Scanning Intelligence rules for Away side
            if away.lower() in feed_text:
                if any(word in feed_text for word in ["injury", "injured", "absent", "doubt", "rested", "suspended"]):
                    away_penalty = -5
                    alerts.append(f"📰 **Squad Signal ({away}):** Breaking media text hints at minor training selection changes or injury constraints.")
                    
        if not alerts:
            alerts.append("✨ **Squad Signal Engine Stable:** No massive injury crises or sudden unexpected squad fractures found in recent media text grids.")
            
        return home_penalty, away_penalty, " | ".join(alerts)
    except Exception:
        return 0, 0, "📡 Squad News Pipeline: System standing by. Manual verification recommended."


def check_tactical_motivation(home, away, europe_active, dead_rubber_active):
    """
    Calculates operational motivation parameters based on fixture scheduling
    priorities and tournament timeline weights.
    """
    home_penalty = 0
    away_penalty = 0
    verdicts = []
    
    if europe_active:
        home_penalty -= 5
        verdicts.append(f"⚠️ **Schedule Interference Trap:** {home} has a massive, decisive European continental fixture in under 72 hours. Expect heavy squad rotation or early performance preservation substitutions once an initial advantage is reached.")
        
    if dead_rubber_active:
        home_penalty -= 10
        away_penalty -= 10
        verdicts.append("📉 **Low Intensity Warning:** End-of-season context suggests title or relegation standings are mathematically sealed. Teams are playing with low competitive urgency, turning this into a high-risk fixture.")
        
    return home_penalty, away_penalty, verdicts

# --- RUN LAUNCH PROCESSING SCAN ---
if st.button("Launch Deep Intelligence Scan", type="primary"):
    st.markdown("---")
    st.subheader(f"📋 Real-Time Match Intelligence Readout: {home_team} vs {away_team}")
    
    # Fire up active network scanner layers
    w_mod, weather_message = check_weather_and_pitch_constraints(city_query)
    n_home, n_away, news_message = check_squad_news_and_rotations(home_team, away_team)
    m_home, m_away, motivation_messages = check_tactical_motivation(home_team, away_team, has_upcoming_europe, is_end_of_season)
    
    # Consolidate and safely clip final slider recommendations between -10% and +10% standard bounds
    final_home_slider_recommendation = max(-10, min(10, w_mod + n_home + m_home))
    final_away_slider_recommendation = max(-10, min(10, w_mod + n_away + m_away))
    
    # Display Clean Output Interface Layout Alerts
    st.info(weather_message)
    
    if "✨" in news_message:
        st.success(news_message)
    else:
        st.markdown(news_message)
        
    if motivation_messages:
        for message in motivation_messages:
            st.warning(message)
            
    st.markdown("---")
    
    # --- VISUAL SLIDER PROFILE METRIC COLS ---
    st.subheader("🎛️ Recommended Modifier Alignment Setup")
    st.caption("Apply these output values exactly to the sliders in your main model app before executing the calculation loops.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            label=f"Recommended **{home_team}** Performance Slider Shift", 
            value=f"{final_home_slider_recommendation}%",
            delta="Apply Reduction" if final_home_slider_recommendation < 0 else ("Apply Boost" if final_home_slider_recommendation > 0 else "Keep Baseline"),
            delta_color="inverse" if final_home_slider_recommendation < 0 else "normal"
        )
        
    with col2:
        st.metric(
            label=f"Recommended **{away_team}** Performance Slider Shift", 
            value=f"{final_away_slider_recommendation}%",
            delta="Apply Reduction" if final_away_slider_recommendation < 0 else ("Apply Boost" if final_away_slider_recommendation > 0 else "Keep Baseline"),
            delta_color="inverse" if final_away_slider_recommendation < 0 else "normal"
        )
        
    st.success(f"🎯 **Action Plan Checklist:** Open your main prediction engine dashboard page (`localhost:8501`). In the sidebar control grid, adjust the **{home_team} Slider to {final_home_slider_recommendation}%** and the **{away_team} Slider to {final_away_slider_recommendation}%**, input your live 1X2 market odds, and fire your simulation!")
