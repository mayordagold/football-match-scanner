import streamlit as st
import requests
import pandas as pd
import re
import unicodedata
from config import THEODDSAPI_KEY

st.set_page_config(
    page_title="Football Data & Live Market Scanner", 
    page_icon="📡",
    layout="wide"
)

st.title("📡 Football Data & Live Market Intelligence Center")
st.markdown("Fetches bookmaker prices from The Odds API. Standings and roster information are shown only when a verified source is available.")

# --- SIDEBAR RESEARCH CONFIGURATION PANEL ---
st.sidebar.title("🔍 Matchday Profile Selector")

home_team = st.sidebar.text_input("Home Club", value="Arsenal")
away_team = st.sidebar.text_input("Away Club", value="Leeds")

league_api_mapping = {
    "English Premier League (EPL)": {"slug": "epl", "odds_key": "soccer_epl"},
    "English Championship (EFL)": {"slug": "championship", "odds_key": "soccer_efl_champ"},
    "Austria Football Bundesliga": {"slug": "austrian-bundesliga", "odds_key": "soccer_austria_bundesliga"},
    "German Bundesliga": {"slug": "german-bundesliga", "odds_key": "soccer_germany_bundesliga"},
    "Spanish La Liga": {"slug": "la-liga", "odds_key": "soccer_spain_la_liga"},
    "Italy Serie A": {"slug": "serie-a", "odds_key": "soccer_italy_serie_a"},
    "France Ligue 1": {"slug": "ligue-1", "odds_key": "soccer_france_ligue_one"},
    "Portugal Primeira Liga": {"slug": "primeira-liga", "odds_key": "soccer_portugal_primeira_liga"},
    "Netherlands Eredivisie": {"slug": "eredivisie", "odds_key": "soccer_netherlands_eredivisie"}
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
submit_analysis = st.sidebar.button("🚀 Pull Live Football & Market Analytics", type="primary", use_container_width=True)

# --- 🛰️ CONTEXT ENGINE FETCH CHANNELS ---
@st.cache_data(ttl=120)
def fetch_live_standings_matrix(_league_slug):
    """Return no standings until a verified standings provider is configured."""
    return pd.DataFrame()

@st.cache_data(ttl=120)
def fetch_live_news_and_injuries(home, away):
    return [f"Roster information for {home} vs {away} is unavailable; no verified injury feed is configured."], False, False

def normalize_team_name(team):
    text = unicodedata.normalize("NFKD", str(team)).encode("ascii", "ignore").decode("ascii").casefold()
    words = re.findall(r"[a-z0-9]+", text)
    while words and words[-1] in {"fc", "afc", "cf", "sc"}:
        words.pop()
    return " ".join(words)


def teams_match(requested, listed):
    requested_name = normalize_team_name(requested)
    listed_name = normalize_team_name(listed)
    return bool(
        requested_name
        and listed_name
        and (
            requested_name == listed_name
            or (len(requested_name) >= 5 and requested_name in listed_name)
            or (len(listed_name) >= 5 and listed_name in requested_name)
        )
    )


def fetch_live_odds_market(sport_key, home, away):
    """Fetch current odds and return prices, per-market sources, and a status message."""
    prices = {"Home": None, "Draw": None, "Away": None, "Over 1.5": None}
    sources = {}
    api_key = THEODDSAPI_KEY.strip()
    if not api_key:
        return prices, sources, "Add your Odds API key to config.py to fetch live odds."

    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"
    params = {
        "apiKey": api_key,
        "regions": "eu",
        "markets": "h2h,totals",
        "oddsFormat": "decimal",
    }

    try:
        response = requests.get(url, params=params, timeout=10)
    except requests.RequestException as error:
        return prices, sources, f"Odds API network error: {error}"

    if response.status_code != 200:
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        details = payload.get("message") or payload.get("error") if isinstance(payload, dict) else ""
        details = details or response.text[:200] or "No error details returned."
        return prices, sources, f"Odds API returned HTTP {response.status_code}: {details}"

    try:
        fixtures = response.json()
    except ValueError:
        return prices, sources, "Odds API returned invalid JSON."
    if not isinstance(fixtures, list):
        return prices, sources, "Odds API returned an unexpected response format."

    fixture = next(
        (
            item for item in fixtures
            if teams_match(home, item.get("home_team", ""))
            and teams_match(away, item.get("away_team", ""))
        ),
        None,
    )
    if fixture is None:
        return prices, sources, f"No live/upcoming odds found for {home} vs {away} in this league."

    for bookmaker in fixture.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            market_key = market.get("key")
            for outcome in market.get("outcomes", []):
                outcome_name = str(outcome.get("name", "")).strip()
                label = None
                if market_key == "h2h":
                    if outcome_name.casefold() == "draw":
                        label = "Draw"
                    elif teams_match(fixture.get("home_team", ""), outcome_name):
                        label = "Home"
                    elif teams_match(fixture.get("away_team", ""), outcome_name):
                        label = "Away"
                elif market_key == "totals" and outcome_name.casefold() == "over":
                    try:
                        if float(outcome.get("point")) == 1.5:
                            label = "Over 1.5"
                    except (TypeError, ValueError):
                        continue

                if label is None:
                    continue
                try:
                    price = float(outcome.get("price"))
                except (TypeError, ValueError):
                    continue
                if not 1 < price < float("inf"):
                    continue
                if prices[label] is None or price > prices[label]:
                    prices[label] = price
                    source = bookmaker.get("title") or bookmaker.get("key") or "Bookmaker"
                    if market.get("last_update"):
                        source += f"; updated {market['last_update']}"
                    sources[label] = source

    if not any(price is not None for price in prices.values()):
        return prices, sources, "The fixture was found, but the API returned no requested prices."
    missing = [label for label, price in prices.items() if price is None]
    status = f"Live API prices found for {home} vs {away}."
    if missing:
        status += " Unavailable markets: " + ", ".join(missing) + "."
    return prices, sources, status



# --- INITIALIZE CORE LAYOUT GLOBAL MEMORY ---
if 'analysis_fired' not in st.session_state:
    st.session_state.analysis_fired = False
    st.session_state.table_df = pd.DataFrame()
    st.session_state.news_alerts = []
    st.session_state.live_odds = {"Home": None, "Draw": None, "Away": None, "Over 1.5": None}
    st.session_state.odds_sources = {}
    st.session_state.odds_status = "Live odds have not been requested."
    st.session_state.h_inj = False
    st.session_state.a_inj = False

if "odds_status" not in st.session_state:
    st.session_state.live_odds = {"Home": None, "Draw": None, "Away": None, "Over 1.5": None}
    st.session_state.odds_sources = {}
    st.session_state.odds_status = "Live odds have not been requested."

# --- TRIGGER EVALUATION DISPATCH PANEL ---
if submit_analysis:
    st.session_state.analysis_fired = True
    league_config = league_api_mapping[selected_league]
    
    (
        st.session_state.live_odds,
        st.session_state.odds_sources,
        st.session_state.odds_status,
    ) = fetch_live_odds_market(league_config["odds_key"], home_team, away_team)
    st.session_state.table_df = fetch_live_standings_matrix(league_config["slug"])
    st.session_state.news_alerts, st.session_state.h_inj, st.session_state.a_inj = fetch_live_news_and_injuries(home_team, away_team)

# --- VISUAL SCREEN GRAPHICS RENDER MATRIX ---
if st.session_state.analysis_fired:
    st.markdown("---")
    
    # SECTION 1: LIVE BOOKMAKER MARKET TRACKER
    st.subheader("💰 Tracked Live Matchday Market Odds Lines")
    o_col1, o_col2, o_col3, o_col4 = st.columns(4)
    def display_price(label):
        price = st.session_state.live_odds.get(label)
        return f"x{price:.2f}" if price is not None else "Unavailable"

    o_col1.metric(
        f"API {home_team} win price",
        display_price("Home"),
        help=st.session_state.odds_sources.get("Home", "No live price returned."),
    )
    o_col2.metric(
        "API match draw price",
        display_price("Draw"),
        help=st.session_state.odds_sources.get("Draw", "No live price returned."),
    )
    o_col3.metric(
        f"API {away_team} win price",
        display_price("Away"),
        help=st.session_state.odds_sources.get("Away", "No live price returned."),
    )
    o_col4.metric(
        "API over 1.5 goals price",
        display_price("Over 1.5"),
        help=st.session_state.odds_sources.get("Over 1.5", "This exact total line was not returned."),
    )
    if any(price is not None for price in st.session_state.live_odds.values()):
        st.info(st.session_state.odds_status)
    else:
        st.warning(st.session_state.odds_status)
    
    st.markdown("---")
    
    # SECTION 2: MANUAL SCENARIO ADJUSTMENTS
    st.subheader("Manual scenario adjustments")
    st.caption("These user-selected shifts are assumptions, not verified or model-calibrated effects.")
    home_modifier = -5 * home_europe - 3 * home_formation_change - 5 * is_dead_rubber
    away_modifier = -5 * away_europe - 3 * away_formation_change - 5 * is_dead_rubber
    if st.session_state.table_df.empty:
        st.warning("Standings are unavailable. No rank or points have been inferred.")
    st.info(
        f"Selected scenario shifts: {home_team} {home_modifier:+d}% | "
        f"{away_team} {away_modifier:+d}%. These are not automatically applied to the odds or prediction model."
    )
# SECTION 3: HIGHLIGHTED LEAGUE TABLE GRAPHICS
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
    st.warning("Standings are unavailable because no verified standings provider is configured.")
# SECTION 4: WEB-SCRAPED BREAKING NEWS AND OVERRIDES FEED
st.markdown("---")
st.subheader(f"📋 Live Matchday Context Readout: {home_team} vs {away_team}")
col_layout1, col_layout2 = st.columns(2)
with col_layout1:
    st.markdown("##### 🩺 Injury & Selection News Feed")
    for alert in st.session_state.news_alerts:
        st.warning(alert)
with col_layout2:
    st.markdown("##### 🛠️ Tactical Formation Modifications")
    if home_formation_change:
        st.warning(f"🔄 {home_team} Override: Structural formation alteration reported.")
    if away_formation_change:
        st.warning(f"🔄 {away_team} Override: Structural formation alteration reported.")
    if not home_formation_change and not away_formation_change:
        st.caption("No manual formation changes selected.")
