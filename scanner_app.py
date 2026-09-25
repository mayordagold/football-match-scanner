import streamlit as st
import requests
import pandas as pd

st.set_page_config(
    page_title="Match Intelligence Scanner & Live Standings Console", 
    page_icon="📡",
    layout="wide"
)

st.title("📡 Automated Football Intelligence & Slider Scanner")
st.markdown("Companion tool to scan fixture motivation, live league standings, weather constraints, and squad rotations.")

# --- SIDEBAR CONTROL PANEL CONFIGURATION ---
st.sidebar.title("🔍 Target Matchup Profile")

# Primary Input Matrix Controls
home_team = st.sidebar.text_input("Home Team Name", value="Grazer AK")
away_team = st.sidebar.text_input("Away Team Name", value="Salzburg")

# Expanded Weather & League Database Options
city_options = [
    "Graz", "Salzburg", "Dortmund", "Munich", "Liverpool", "London", 
    "Manchester", "Glasgow", "Paris", "Marseille", "Milano", "Torino", 
    "Rome", "Madrid", "Barcelona", "Lisbon", "Porto", "Amsterdam", "Other Baseline"
]
selected_city = st.sidebar.selectbox("Match City Location (For Weather)", city_options)

# League Standings Selector Engine Tracker (Perfectly mapped to your 10 database components)
league_table_options = {
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 English Premier League": "https://wikipedia.org",
    "🇦🇹 Austria Bundesliga": "https://wikipedia.org",
    "🇩🇪 German Bundesliga": "https://wikipedia.org",
    "🇪🇸 Spanish La Liga": "https://wikipedia.org",
    "🇮🇹 Italy Serie A": "https://wikipedia.org",
    "🇫🇷 France Ligue 1": "https://wikipedia.org",
    "🇵🇹 Portugal Primeira Liga": "https://wikipedia.org",
    "🇳🇱 Netherlands Eredivisie": "https://wikipedia.org"
}
selected_standing_league = st.sidebar.selectbox("Load Live League Standings Display", list(league_table_options.keys()))

st.sidebar.markdown("---")
st.sidebar.subheader("🏆 Motivation & Schedule Priority")

home_europe = st.sidebar.checkbox(f"Does {home_team} (Home) have a European match in 3 days?", value=False)
away_europe = st.sidebar.checkbox(f"Does {away_team} (Away) have a European match in 3 days?", value=True)

is_end_of_season = st.sidebar.checkbox(
    label="Dead Rubber Fixture?", 
    value=False,
    help="Check this if it is the end of the season and standings are already mathematically locked."
)

# --- ADVANCED AUTOMATED WEB-SCRAPER ENGINES ---

def scrape_live_wikipedia_standings(url):
    """
    Automated Web-Scraper Layer.
    Locates and normalises raw HTML tables into standardized DataFrames on the fly.
    """
    try:
        # Request the page content with a generic User-Agent header
        html_tables = pd.read_html(url, attrs={"class": "wikitable"})
        
        # Look for the primary league standings dataframe table
        for table in html_tables:
            columns_lower = [str(c).lower() for c in table.columns]
            # Match standard tables carrying Team/Club, Points, and Matches Played attributes
            if any("team" in c or "club" in c for c in columns_lower) and any("pts" in c or "points" in c for c in columns_lower):
                # Clean up header styling artifacts
                table.columns = [str(c).strip() for c in table.columns]
                
                # Dynamic header normalization mapping matrix
                rename_map = {}
                for col in table.columns:
                    col_l = col.lower()
                    if "pos" in col_l or "rk" in col_l or "rank" in col_l: rename_map[col] = "Rank"
                    elif "team" in col_l or "club" in col_l: rename_map[col] = "Club"
                    elif col_l == "pld" or col_l == "mp" or col_l == "g": rename_map[col] = "MP"
                    elif col_l == "w": rename_map[col] = "W"
                    elif col_l == "d": rename_map[col] = "D"
                    elif col_l == "l": rename_map[col] = "L"
                    elif col_l == "gf" or col_l == "f": rename_map[col] = "GF"
                    elif col_l == "ga" or col_l == "a": rename_map[col] = "GA"
                    elif col_l == "gd" or col_l == "diff": rename_map[col] = "GD"
                    elif "pts" in col_l or "points" in col_l: rename_map[col] = "Pts"
                
                table = table.rename(columns=rename_map)
                
                # Fallback to generate standard ranks if missing from structural markers
                if "Rank" not in table.columns:
                    table.insert(0, "Rank", range(1, len(table) + 1))
                
                required_display = ["Rank", "Club", "MP", "W", "D", "L", "GF", "GA", "GD", "Pts"]
                existing_display = [c for c in required_display if c in table.columns]
                
                return table[existing_display].head(20) # Keep top 20 structural tiers
    except Exception as e:
        pass
    
    # Clean internal backup fallback structure if page structure timeouts execute
    return pd.DataFrame({"Status": ["⚠️ Live Web-Scraper layer timed out or page structural update pending. Audit connection feeds manually."]})


def check_weather_and_pitch_constraints(city_name):
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
                return -5, f"🌧️ Weather Constraints Active: Live heavy downpour verified in {city_name}. Pitch slow/waterlogged risk. Applying -5% modifier safety margin."
            if wind_speed > 40:
                return -5, f"💨 Weather Constraints Active: High wind speeds ({wind_speed} km/h) tracked in {city_name}. Applying -5% volatility margin."
            return 0, f"🟢 Environmental Engine Stable: Clear/Fair conditions confirmed in {city_name}. Pitch texture optimal."
    except Exception:
        pass
    return 0, "📡 Environmental Signals: Weather node busy. Defaulting to standard 0% conditions."


def check_squad_news_and_rotations(home, away):
    alerts = []
    try:
        search_query = f'"{home}" OR "{away}" football injury lineup team news'
        url = f"https://google.com{search_query}&hl=en-GB&gl=GB&ceid=GB:en"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=4)
        if response.status_code == 200:
            feed_text = response.text.lower()
            if home.lower() in feed_text and any(w in feed_text for w in ["injury", "injured", "absent", "rested", "suspended"]):
                alerts.append(f"📰 **Squad Disruption ({home}):** Media text notes minor selection constraints.")
            if away.lower() in feed_text and any(w in feed_text for w in ["injury", "injured", "absent", "rested", "suspended"]):
                alerts.append(f"📰 **Squad Disruption ({away}):** Media text notes minor selection constraints.")
        if not alerts:
            alerts.append("✨ **Squad Signal Engine Stable:** No unexpected squad fractures found in recent media grids.")
        return 0, 0, " | ".join(alerts)
    except Exception:
        return 0, 0, "📡 Squad News Pipeline: System standing by."

# --- PRE-INITIALIZE MEMORY STATE VARIABLES TO PREVENT PAGE LOAD CRASHES ---
if 'scan_executed' not in st.session_state:
    st.session_state.scan_executed = False
    st.session_state.final_home_slider = 0
    st.session_state.final_away_slider = 0
    st.session_state.weather_message = "🌤️ Environmental Engine Standing By."
    st.session_state.news_message = "📡 Squad News Pipeline: System standing by."
    st.session_state.motivation_messages = []
    st.session_state.scraped_standings = pd.DataFrame()

# --- TRIGGER PROCESSING RUN ---
if st.button("Launch Deep Intelligence Scan", type="primary"):
    st.session_state.scan_executed = True
    
    # Target wiki scraping url allocation mapping
    target_url = league_table_options[selected_standing_league]
    st.session_state.scraped_standings = scrape_live_wikipedia_standings(target_url)
    
    w_mod, st.session_state.weather_message = check_weather_and_pitch_constraints(selected_city)
    _, _, st.session_state.news_message = check_squad_news_and_rotations(home_team, away_team)
    
    home_penalty, away_penalty = 0, 0
    st.session_state.motivation_messages = []
    if home_europe:
        home_penalty -= 5
        st.session_state.motivation_messages.append(f"⚠️ **Schedule Interference Trap:** {home_team} has a massive European match in 72 hours. Expect rotation.")
    if away_europe:
        away_penalty -= 5
        st.session_state.motivation_messages.append(f"⚠️ **Schedule Interference Trap:** {away_team} has a massive European match in 72 hours. Expect tactical rotation.")
    if is_end_of_season:
        home_penalty -= 10
        away_penalty -= 10
    st.session_state.motivation_messages.append("📉 Low Intensity Warning: End-of-season dead rubber context active.")
    
    # LOCKED INTERNAL MEMORY VALUE CORRECTION DEFINITION
    st.session_state.final_home_slider = max(-10, min(10, w_mod + home_penalty))
    st.session_state.final_away_slider = max(-10, min(10, w_mod + away_penalty))
    
    #---DYNAMIC SCREEN GRAPHICS RENDER MATRIX---
    if st.session_state.scan_executed:
        st.markdown("---")
    # 📊 LAYOUT ELEMENT 1: Live Web-Scraped Standings Output Display Panel
    st.subheader(f"🏆 Live Dynamic Standings Table: {selected_standing_league}")
    if not st.session_state.scraped_standings.empty:
        st.dataframe(st.session_state.scraped_standings, use_container_width=True, hide_index=True)
    else:
        st.info("🔄 Re-routing pipeline feeds. Refreshing standings core data grid.")
    st.markdown("##### 💡 Standings Motivation Clue Decoder:")
    st.caption("Review live points, matches played (MP), and Goal Differentials (GD) above to verify match motivation context (relegation threat points cushion vs top-four positioning protection).")
    st.markdown("---")
    st.subheader(f"📋 Real-Time Match Intelligence Readout: {home_team} vs {away_team}")
    st.info(st.session_state.weather_message)
    if "✨" in st.session_state.news_message:
        st.success(st.session_state.news_message)
    else:
        st.markdown(st.session_state.news_message)
    if st.session_state.motivation_messages:
        for message in st.session_state.motivation_messages:
            st.warning(message)
    st.markdown("---")
    st.subheader("🎛️ Recommended Modifier Alignment Setup")
    col1, col2 = st.columns(2)
    col1.metric(label=f"Recommended {home_team} Performance Slider Shift", value=f"{st.session_state.final_home_slider}%", delta="Apply Reduction" if st.session_state.final_home_slider < 0 else "Keep Baseline", delta_color="inverse" if st.session_state.final_home_slider < 0 else "normal")
    col2.metric(label=f"Recommended {away_team} Performance Slider Shift", value=f"{st.session_state.final_away_slider}%", delta="Apply Reduction" if st.session_state.final_away_slider < 0 else "Keep Baseline", delta_color="inverse" if st.session_state.final_away_slider < 0 else "normal")
    st.success(f"🎯 Action Plan Checklist: Open your local prediction engine dashboard page (localhost:8501). In your sidebar, move the {home_team} Slider to {st.session_state.final_home_slider}% and the {away_team} Slider to {st.session_state.final_away_slider}%, enter your live SportyBet market odds, and fire your simulation!")
else:
    st.info("💡 Scanner Dashboard Idle: Configure the sidebar profile controls and click 'Launch Deep Intelligence Scan' to extract live matchday parameters.")
