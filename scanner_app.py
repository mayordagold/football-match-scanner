import streamlit as st
import requests
import pandas as pd

st.set_page_config(
    page_title="Matchday Context & Intelligence Center", 
    page_icon="📡",
    layout="wide"
)

st.title("📡 Football Matchday Context & Intelligence Center")
st.markdown("Automated analytical platform to track **Live Standings Pressure**, **Roster Injuries**, and **Tactical Lineup Transitions**.")

# SECURITY API CREDENTIAL FEEDS
ALLSPORTSAPI_KEY = "3e43bc859f75abbb20212db989119e195b915f145d37dab5cb4b109c3f52110b"

# --- SIDEBAR RESEARCH CONFIGURATION PANEL ---
st.sidebar.title("🔍 Matchday Profile Selector")

home_team = st.sidebar.text_input("Home Club", value="Grazer AK")
away_team = st.sidebar.text_input("Away Club", value="Salzburg")

league_api_mapping = {
    "🇦🇹 Austria Football Bundesliga": {"id": 91, "slug": "austrian-bundesliga"},
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 English Premier League": {"id": 152, "slug": "epl"},
    "🇩🇪 German Bundesliga": {"id": 175, "slug": "german-bundesliga"},
    "🇪🇸 Spanish La Liga": {"id": 302, "slug": "la-liga"},
    "🇮🇹 Italy Serie A": {"id": 207, "slug": "serie-a"},
    "🇫🇷 France Ligue 1": {"id": 168, "slug": "ligue-1"},
    "🇵🇹 Portugal Primeira Liga": {"id": 266, "slug": "primeira-liga"},
    "🇳🇱 Netherlands Eredivisie": {"id": 244, "slug": "eredivisie"}
}
selected_league = st.sidebar.selectbox("Active League Division Table", list(league_api_mapping.keys()))

st.sidebar.markdown("---")
st.sidebar.subheader("📋 Manual Tactical Overrides")
st.sidebar.caption("Manually flag tactical variations noticed in recent press conferences.")
home_formation_change = st.sidebar.checkbox(f"Is {home_team} altering standard formation format?", value=False)
away_formation_change = st.sidebar.checkbox(f"Is {away_team} altering standard formation format?", value=False)

st.sidebar.markdown("---")
submit_analysis = st.sidebar.button("🚀 Pull Live Matchday Intelligence", type="primary", use_container_width=True)

# --- 🛰️ CONTEXT ENGINE FETCH CHANNELS ---

def fetch_live_standings_matrix(league_id, fallback_slug):
    """Streams live table metrics safely via AllSportsApi developer servers."""
    url = "https://allsportsapi.com"
    params = {'met': 'Standings', 'leagueId': league_id, 'APIkey': ALLSPORTSAPI_KEY}
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            raw_json = response.json()
            result_node = raw_json.get('result', {})
            standings_block = result_node.get('total', []) if isinstance(result_node, dict) else result_node
            
            compiled_rows = []
            for item in standings_block:
                if not isinstance(item, dict): continue
                compiled_rows.append({
                    "Rank": item.get('standing_place', item.get('position', 0)),
                    "Club": item.get('standing_team', item.get('team_name', 'Unknown')),
                    "MP": item.get('standing_P', 0),
                    "W": item.get('standing_W', 0),
                    "D": item.get('standing_D', 0),
                    "L": item.get('standing_L', 0),
                    "GF": item.get('standing_F', 0),
                    "GA": item.get('standing_A', 0),
                    "GD": item.get('standing_GD', 0),
                    "Pts": item.get('standing_PTS', 0)
                })
            if compiled_rows:
                df = pd.DataFrame(compiled_rows)
                for col in ["Pts", "GD", "Rank"]: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
                return df.sort_values(by=["Pts", "GD"], ascending=False).reset_index(drop=True)
    except Exception: pass
    
    # Secure backup stream routing to guarantee data loads cleanly
    try:
        fallback_url = f"https://fixturedownload.com{fallback_slug}-2026"
        f_resp = requests.get(fallback_url, timeout=5)
        if f_resp.status_code == 200:
            fixtures = f_resp.json()
            table = {}
            for f in fixtures:
                if f.get('HomeTeamScore') is not None:
                    h, a = f['HomeTeam'], f['AwayTeam']
                    hs, as_ = int(f['HomeTeamScore']), int(f['AwayTeamScore'])
                    for t in [h, a]:
                        if t not in table: table[t] = {"MP":0,"W":0,"D":0,"L":0,"GF":0,"GA":0,"Pts":0}
                    table[h]["MP"]+=1; table[a]["MP"]+=1; table[h]["GF"]+=hs; table[h]["GA"]+=as_; table[a]["GF"]+=as_; table[a]["GA"]+=hs
                    if hs > as_: table[h]["W"]+=1; table[h]["Pts"]+=3; table[a]["L"]+=1
                    elif hs == as_: table[h]["D"]+=1; table[h]["Pts"]+=1; table[a]["D"]+=1; table[a]["Pts"]+=1
                    else: table[a]["W"]+=1; table[a]["Pts"]+=3; table[h]["L"]+=1
            df_list = [{"Club":k,"MP":v["MP"],"W":v["W"],"D":v["D"],"L":v["L"],"GF":v["GF"],"GA":v["GA"],"GD":v["GF"]-v["GA"],"Pts":v["Pts"]} for k,v in table.items()]
            res_df = pd.DataFrame(df_list).sort_values(by=["Pts","GD"], ascending=False).reset_index(drop=True)
            res_df.insert(0, "Rank", range(1, len(res_df) + 1))
            return res_df
    except Exception: pass
    return pd.DataFrame()

def fetch_live_news_and_injuries(home, away):
    """Pulls breaking news alerts from RSS pipelines to track injuries and suspensions."""
    alerts = []
    try:
        search_query = f'"{home}" OR "{away}" football injury lineup team news'
        url = f"https://google.com{search_query}&hl=en-GB&gl=GB&ceid=GB:en"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=4)
        if response.status_code == 200:
            feed_text = response.text.lower()
            # Scan text arrays for prominent risk indicators
            for word in ["injury", "injured", "broken", "acl", "hamstring", "doubtful", "suspended", "absence"]:
                if f" {word}" in feed_text:
                    if home.lower() in feed_text: alerts.append(f"🚨 **Roster Vulnerability ({home}):** Media articles mention tracking parameters for '{word}' constraints.")
                    if away.lower() in feed_text: alerts.append(f"🚨 **Roster Vulnerability ({away}):** Media articles mention tracking parameters for '{word}' constraints.")
                    break
        if not alerts:
            alerts.append("✨ **Roster Intelligence Stable:** No critical new player absences or tactical disruptions found in recent media grids.")
        return list(set(alerts))
    except Exception:
        return ["📡 Intelligence Pipeline: RSS feed standing by for active lookup queries."]

# --- INITIALIZE CORE LAYOUT MEMORY ---
if 'analysis_fired' not in st.session_state:
    st.session_state.analysis_fired = False
    st.session_state.table_df = pd.DataFrame()
    st.session_state.news_alerts = []

# --- TRIGGER EVALUATION DISPATCH PANEL ---
if submit_analysis:
    st.session_state.analysis_fired = True
    league_config = league_api_mapping[selected_league]
    st.session_state.table_df = fetch_live_standings_matrix(league_config["id"], league_config["slug"])
    st.session_state.news_alerts = fetch_live_news_and_injuries(home_team, away_team)

# --- VISUAL RESEARCH COMPONENT INTERFACE ---
if st.session_state.analysis_fired:
    st.markdown("---")
    
    # SECTION 1: Dynamic League Table Standings Pressure Matrix
    st.subheader(f"🏆 Current Standings Pressure Board: {selected_league}")
    if not st.session_state.table_df.empty:
        st.dataframe(st.session_state.table_df, use_container_width=True, hide_index=True)
    else:
        st.error("Connection Interrupted: Standings matrix server busy. Re-fire query panel.")
        
    # SECTION 2: Squad News, Injuries & Tactical Overrides Feed
    st.markdown("---")
    st.subheader(f"📋 Live Matchday Context Readout: {home_team} vs {away_team}")
    
    col_layout1, col_layout2 = st.columns(2)
    
    with col_layout1:
        st.markdown("##### 🩺 Injury & Selection News Feed")
        for alert in st.session_state.news_alerts:
            if "🚨" in alert: st.error(alert)
            else: st.success(alert)
            
    with col_layout2:
        st.markdown("##### 🛠️ Tactical Formation Modifications")
        if home_formation_change:
            st.warning(f"🔄 **{home_team} Override:** Technical squad notes indicate a structural formation alteration. Expect early instability or alternative pacing.")
        if away_formation_change:
            st.warning(f"🔄 **{away_team} Override:** Technical squad notes indicate a structural formation alteration. Expect early instability or alternative pacing.")
        if not home_formation_change and not away_formation_change:
            st.success("📐 **Tactical Balance Stable:** Both clubs are projected to maintain their standard baseline layout profiles.")
            
    st.markdown("---")
    st.info("💡 **How to Apply This Context:** Review the table points and injury weights above to determine team motivation. Use these insights to adjust the modifier performance shift sliders inside your main local terminal (`app.py`) before running math simulations!")
else:
    st.info("💡 Context Dashboard Idle: Select your target league division and matchup clubs in the sidebar control panel, then click 'Pull Live Matchday Intelligence' to analyze current variables.")
