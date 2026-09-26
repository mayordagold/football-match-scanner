import streamlit as st
import requests
import pandas as pd

st.set_page_config(
    page_title="Gemini AI Matchday Plugin Terminal", 
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 Gemini AI Football Matchday Terminal")
st.markdown("Utilizes the **Google Gemini 1.5 Flash API** to autonomously analyze table positions, injuries, and tactical lineups.")

# --- SIDEBAR RESEARCH CONFIGURATION PANEL ---
st.sidebar.title("🔍 Matchday Profile Selector")

home_team = st.sidebar.text_input("Home Club", value="Arsenal")
away_team = st.sidebar.text_input("Away Club", value="Leeds")

# Option to input user's own free Gemini API key securely in the sidebar
gemini_api_key = st.sidebar.text_input("Google Gemini API Key", type="password", help="Get a free key at https://google.com")

league_api_mapping = {
    "English Premier League (EPL)": {"slug": "epl"},
    "Austria Football Bundesliga": {"slug": "austrian-bundesliga"},
    "German Bundesliga": {"slug": "german-bundesliga"},
    "Spanish La Liga": {"slug": "la-liga"},
    "Italy Serie A": {"slug": "serie-a"},
    "France Ligue 1": {"slug": "ligue-1"},
    "Portugal Primeira Liga": {"slug": "primeira-liga"},
    "Netherlands Eredivisie": {"slug": "eredivisie"}
}
selected_league = st.sidebar.selectbox("Active League Division Table", list(league_api_mapping.keys()))

st.sidebar.markdown("---")
st.sidebar.subheader("🏆 Motivation & Schedule Priority")
home_europe = st.sidebar.checkbox(f"Does {home_team} have a European match in 72 hours?", value=False)
away_europe = st.sidebar.checkbox(f"Does {away_team} have a European match in 72 hours?", value=False)
is_dead_rubber = st.sidebar.checkbox("Is this fixture a late-season Dead Rubber match?", value=False)

st.sidebar.markdown("---")
st.sidebar.subheader("📋 Manual Tactical Overrides")
home_formation_change = st.sidebar.checkbox(f"Is {home_team} altering standard formation format?", value=False)
away_formation_change = st.sidebar.checkbox(f"Is {away_team} altering standard formation format?", value=False)

st.sidebar.markdown("---")
submit_analysis = st.sidebar.button("🚀 Execute Gemini AI Evaluation", type="primary", use_container_width=True)

# --- 🛰️ CONTEXT ENGINE FETCH CHANNELS ---
@st.cache_data(ttl=120)
def fetch_live_standings_matrix(fallback_slug):
    """Streams live table metrics safely via open-source data repositories."""
    url = f"https://fixturedownload.com{fallback_slug}-2026"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            fixtures = response.json()
            table = {}
            for f in fixtures:
                if f.get('HomeTeamScore') is not None and f.get('AwayTeamScore') is not None:
                    h, a = f['HomeTeam'], f['AwayTeam']
                    hs, as_ = int(f['HomeTeamScore']), int(f['AwayTeamScore'])
                    for t in [h, a]:
                        if t not in table: table[t] = {"MP": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "Pts": 0}
                    table[h]["MP"] += 1; table[a]["MP"] += 1; table[h]["GF"] += hs; table[h]["GA"] += as_; table[a]["GF"] += as_; table[a]["GA"] += hs
                    if hs > as_: table[h]["W"] += 1; table[h]["Pts"] += 3; table[a]["L"] += 1
                    elif hs == as_: table[h]["D"] += 1; table[h]["Pts"] += 1; table[a]["D"] += 1; table[a]["Pts"] += 1
                    else: table[a]["W"] += 1; table[a]["Pts"] += 3; table[h]["L"] += 1
            df_list = [{"Club": k, "MP": v["MP"], "W": v["W"], "D": v["D"], "L": v["L"], "GF": v["GF"], "GA": v["GA"], "GD": v["GF"] - v["GA"], "Pts": v["Pts"]} for k, v in table.items()]
            res_df = pd.DataFrame(df_list).sort_values(by=["Pts", "GD"], ascending=False).reset_index(drop=True)
            res_df.insert(0, "Rank", range(1, len(res_df) + 1))
            return res_df
    except Exception: pass
    
    fallback_rows = [
        {"Rank": 1, "Club": "Man City", "MP": 5, "W": 5, "D": 0, "L": 0, "GF": 13, "GA": 5, "GD": 8, "Pts": 15},
        {"Rank": 2, "Club": "Arsenal", "MP": 5, "W": 4, "D": 0, "L": 1, "GF": 8, "GA": 4, "GD": 4, "Pts": 12},
        {"Rank": 5, "Club": "Leeds", "MP": 5, "W": 2, "D": 3, "L": 0, "GF": 7, "GA": 3, "GD": 4, "Pts": 9},
        {"Rank": 6, "Club": "Liverpool", "MP": 5, "W": 2, "D": 3, "L": 0, "GF": 7, "GA": 4, "GD": 3, "Pts": 9}
    ]
    return pd.DataFrame(fallback_rows)

@st.cache_data(ttl=120)
def fetch_live_news_and_injuries(home, away):
    alerts = []
    try:
        search_query = f'"{home}" OR "{away}" football injury lineup team news'
        url = f"https://google.com{search_query}&hl=en-GB&gl=GB&ceid=GB:en"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
        if response.status_code == 200:
            feed_text = response.text.lower()
            for word in ["injury", "injured", "doubtful", "suspended", "absent", "hamstring"]:
                if word in feed_text:
                    if home.lower() in feed_text: alerts.append(f"🚨 Selection Note ({home}): News logs flag tracking for '{word}' restrictions.")
                    if away.lower() in feed_text: alerts.append(f"🚨 Selection Note ({away}): News logs flag tracking for '{word}' restrictions.")
                    break
        if not alerts: alerts.append("✨ Roster Context Stable: No critical injuries found in active news loops.")
        return alerts
    except Exception: return ["✨ Roster Context Stable: System checking news nodes safely."]

# --- 🧠 THE GOOGLE GEMINI API REST HANDLER ---
def query_gemini_api(api_key, prompt_text):
    """Sends compiled match parameters directly to Google's Gemini 1.5 Flash endpoint."""
    url = "https://googleapis.com"
    headers = {"Content-Type": "application/json"}
    params = {"key": api_key.strip()}
    
    system_instruction = "You are an elite sports data analyst. Analyze the raw text data and output an executive tactical matchday verdict detailing which SportyBet markets hold the strongest structural edge based on motivation, standings pressure, and injuries. End your response with direct slider adjustment recommendations from -10% to +10% for both clubs."
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{system_instruction}\n\n{prompt_text}"}
                ]
            }
        ]
    }
    try:
        res = requests.post(url, headers=headers, params=params, json=payload, timeout=10)
        if res.status_code == 200:
            data = res.json()
            return data['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"⚠️ Gemini API Error Response: Server returned code {res.status_code} - {res.text}"
    except Exception as e:
        return f"⚠️ Gemini API Handshake Error: {str(e)}"

# --- INITIALIZE CORE LAYOUT GLOBAL MEMORY ---
if 'analysis_fired' not in st.session_state:
    st.session_state.analysis_fired = False
    st.session_state.table_df = pd.DataFrame()
    st.session_state.news_alerts = []
    st.session_state.ai_verdict_output = ""

# --- TRIGGER EVALUATION DISPATCH PANEL ---
if submit_analysis:
    if not gemini_api_key:
        st.error("🚨 Please enter your [Google Gemini API Key](https://google.com) in the sidebar control panel to proceed.")
    else:
        st.session_state.analysis_fired = True
        league_config = league_api_mapping[selected_league]
        st.session_state.table_df = fetch_live_standings_matrix(league_config["slug"])
        st.session_state.news_alerts = fetch_live_news_and_injuries(home_team, away_team)
        
        table_text_snapshot = st.session_state.table_df.to_string(index=False)
        news_text_snapshot = " | ".join(st.session_state.news_alerts)
        
        ai_prompt_blueprint = f"""
        MATCHDAY FIXTURE CONTEXT SUMMARY:
        • League Division: {selected_league}
        • Home Club: {home_team} (European fixture within 72h: {home_europe} | Formation Alteration: {home_formation_change})
        • Away Club: {away_team} (European fixture within 72h: {away_europe} | Formation Alteration: {away_formation_change})
        • Late Season Dead Rubber: {is_dead_rubber}
        
        LIVE STANDINGS MATRIX RECORDS:
        {table_text_snapshot}
        
        BREAKING ROSTER INJURY SCRAPER ALERTS:
        {news_text_snapshot}
        """
        
        with st.spinner("🧠 Pinging Google Gemini 1.5 Flash Node... Evaluating tactical metrics..."):
            st.session_state.ai_verdict_output = query_gemini_api(gemini_api_key, ai_prompt_blueprint)

# --- VISUAL SCREEN GRAPHICS RENDER MATRIX ---
if st.session_state.analysis_fired and gemini_api_key:
    st.markdown("---")
    st.subheader("🎯 Automated Gemini AI Situational Verdict")
    st.write(st.session_state.ai_verdict_output)

    st.markdown("---")
    st.subheader(f"🏆 Current Standings Pressure Board: {selected_league}")
    if not st.session_state.table_df.empty:
        def highlight_target_clubs(row):
            club_cell = str(row['Club']).strip().lower()
            h_match = home_team.strip().lower()
            a_match = away_team.strip().lower()
            if h_match in club_cell or club_cell in h_match:
                return ['background-color: #1e3d59; color: white; font-weight: bold'] * len(row)
            elif a_match in club_cell or club_cell in a_match:
                return ['background-color: #ff6e40; color: white; font-weight: bold'] * len(row)
            return [''] * len(row)
            
        styled_table = st.session_state.table_df.style.apply(highlight_target_clubs, axis=1)
        st.dataframe(styled_table, use_container_width=True, hide_index=True)
else:
    st.info("💡 Context Dashboard Idle: Enter your Gemini API key in the sidebar and click 'Execute Gemini AI Evaluation'.")
