import streamlit as st
import numpy as np
import pandas as pd
from config import THEODDSAPI_KEY
from live_data import LIVE_COMPETITIONS, LiveOddsError, fetch_live_fixtures, fixture_bookmakers, prices_for_bookmaker
from prediction_model import estimate_goal_rates, poisson_market_probabilities, standings_as_of, walk_forward_backtest
from team_names import teams_match

st.set_page_config(
    page_title="Poisson Match Probability Model", 
    page_icon="🔮",
    layout="wide"
)

st.title("Poisson Match Probability Model")
st.markdown("Uses recency-weighted team attack and defense rates from earlier match scores, with a chronological backtest for historical performance.")


@st.cache_data(ttl=60, show_spinner=False)
def cached_live_fixtures(sport_key, api_key):
    return fetch_live_fixtures(sport_key, api_key)


@st.cache_data(show_spinner="Evaluating historical matches...")
def cached_backtest(matches):
    return walk_forward_backtest(matches, min_history=30)


# --- 🎮 SIDEBAR CONTROLS panel ---
st.sidebar.title("🎮 Simulation Control Panel")

uploaded_file = st.sidebar.file_uploader("Drag and drop your clean Master Database CSV file to initialize", type=["csv"])

if uploaded_file is not None:
    try:
        df_repo = pd.read_csv(uploaded_file)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as error:
        st.error(f"Could not read this CSV file: {error}")
        st.stop()

    normalized_headers = {
        str(column).lower().strip().replace("_", "").replace(" ", ""): column
        for column in df_repo.columns
    }

    def find_column(candidates):
        return next((normalized_headers[name] for name in candidates if name in normalized_headers), None)

    home_col = find_column(("hometeam", "home"))
    away_col = find_column(("awayteam", "away"))
    league_col = find_column(("league", "competition", "division"))
    date_col = find_column(("date", "matchdate", "datetime", "utcdate"))
    home_goals_col = find_column(("hg", "fthg", "homegoals", "hometeamscore"))
    away_goals_col = find_column(("ag", "ftag", "awaygoals", "awayteamscore"))
    home_corners_col = find_column(("hcft", "hc", "homecorners"))
    away_corners_col = find_column(("acft", "ac", "awaycorners"))

    missing_columns = []
    if home_col is None:
        missing_columns.append("home team (HomeTeam or Home)")
    if away_col is None:
        missing_columns.append("away team (AwayTeam or Away)")
    if league_col is None:
        missing_columns.append("league (League)")
    if date_col is None:
        missing_columns.append("match date (Date), needed for time-ordered evaluation")
    if home_goals_col is None or away_goals_col is None:
        missing_columns.append("home and away xG or goals")
    if home_corners_col is None or away_corners_col is None:
        missing_columns.append("home and away corners")
    if missing_columns:
        st.error("CSV is missing required data: " + "; ".join(missing_columns))
        st.stop()

    if df_repo.empty:
        st.error("The uploaded CSV contains no match rows.")
        st.stop()

    match_data = pd.DataFrame({
        "date": pd.to_datetime(
            df_repo[date_col],
            format="mixed",
            dayfirst=True,
            errors="coerce",
            utc=True,
        ).dt.tz_convert(None),
        "league": df_repo[league_col].astype("string").str.strip(),
        "home_team": df_repo[home_col].astype("string").str.strip(),
        "away_team": df_repo[away_col].astype("string").str.strip(),
        "home_goals": pd.to_numeric(df_repo[home_goals_col], errors="coerce"),
        "away_goals": pd.to_numeric(df_repo[away_goals_col], errors="coerce"),
        "home_corners": pd.to_numeric(df_repo[home_corners_col], errors="coerce"),
        "away_corners": pd.to_numeric(df_repo[away_corners_col], errors="coerce"),
    })
    valid_match_rows = match_data.dropna().copy()
    valid_match_rows = valid_match_rows[
        valid_match_rows["home_team"].ne("")
        & valid_match_rows["away_team"].ne("")
        & valid_match_rows["league"].ne("")
        & valid_match_rows["home_goals"].between(0, 20)
        & valid_match_rows["away_goals"].between(0, 20)
        & valid_match_rows["home_corners"].between(0, 50)
        & valid_match_rows["away_corners"].between(0, 50)
    ]
    dropped_rows = len(df_repo) - len(valid_match_rows)
    if dropped_rows:
        st.warning(f"Excluded {dropped_rows} rows with missing dates, teams, or invalid match statistics.")
    future_match_mask = valid_match_rows["date"] >= pd.Timestamp.now(tz="UTC").tz_localize(None)
    future_match_count = int(future_match_mask.sum())
    valid_match_rows = valid_match_rows.loc[~future_match_mask]
    if future_match_count:
        st.warning(f"Excluded {future_match_count} future-dated rows to avoid using unplayed matches.")
    if valid_match_rows.empty:
        st.error("No valid past match rows remain after validation.")
        st.stop()
    
    available_leagues = sorted(valid_match_rows["league"].unique())
    if not available_leagues:
        st.error("No competition values were found in the League column.")
        st.stop()
    selected_league = st.sidebar.selectbox("Pick Target Competition Division", available_leagues)
    
    df_filtered = valid_match_rows[valid_match_rows["league"] == selected_league].sort_values("date")
    available_teams = sorted(pd.concat([df_filtered["home_team"], df_filtered["away_team"]]).dropna().unique())
    if len(available_teams) < 2:
        st.error("The selected competition must contain at least two distinct teams.")
        st.stop()

    st.sidebar.markdown("---")
    use_live_fixture = st.sidebar.checkbox("Choose an upcoming fixture from live odds API", value=False)
    selected_fixture = None
    selected_bookmaker_key = None
    live_prices = {"Home": None, "Draw": None, "Away": None, "Over 1.5": None}
    live_price_sources = {}
    live_fixture_status = ""

    if use_live_fixture:
        normalized_league = str(selected_league).casefold()
        matching_competitions = [
            name for name, config in LIVE_COMPETITIONS.items()
            if any(alias in normalized_league for alias in config["history_aliases"])
        ]
        api_key = THEODDSAPI_KEY.strip()
        if not matching_competitions:
            st.sidebar.warning("No live API competition matches the selected archive league.")
        elif not api_key:
            st.sidebar.warning("Add your Odds API key to config.py to load live fixtures and odds.")
        else:
            live_competition = st.sidebar.selectbox("Live odds competition", matching_competitions)
            sport_key = LIVE_COMPETITIONS[live_competition]["sport_key"]
            try:
                live_fixtures = cached_live_fixtures(sport_key, api_key)
            except LiveOddsError as error:
                live_fixtures = []
                st.sidebar.error(str(error))

            if live_fixtures:
                fixture_labels = {
                    f"{fixture['commence_time']} | {fixture['home_team']} vs {fixture['away_team']}": fixture
                    for fixture in live_fixtures
                }
                selected_fixture_label = st.sidebar.selectbox("Upcoming fixture", list(fixture_labels))
                selected_fixture = fixture_labels[selected_fixture_label]
                home_club = selected_fixture["home_team"]
                away_club = selected_fixture["away_team"]
                bookmakers = fixture_bookmakers(selected_fixture)
                if bookmakers:
                    bookmaker_labels = {
                        f"{bookmaker.get('title') or bookmaker.get('key')} ({bookmaker.get('key')})": bookmaker.get("key")
                        for bookmaker in bookmakers
                    }
                    selected_bookmaker_label = st.sidebar.selectbox("Bookmaker", list(bookmaker_labels))
                    selected_bookmaker_key = bookmaker_labels[selected_bookmaker_label]
                    live_prices, live_price_sources = prices_for_bookmaker(selected_fixture, selected_bookmaker_key)
                    live_fixture_status = f"Odds loaded for {home_club} vs {away_club} from {selected_bookmaker_label}."
                else:
                    live_fixture_status = "Fixture found, but no bookmaker has a 1X2 market."
                    st.sidebar.warning(live_fixture_status)
            else:
                st.sidebar.info("No upcoming fixtures with odds are currently available for this competition.")
    
    if selected_fixture is None:
        home_club = st.sidebar.selectbox("Pick Home Team Matchup", available_teams, index=0)
        available_away_teams = [team for team in available_teams if team != home_club]
        away_club = st.sidebar.selectbox("Pick Away Team Matchup", available_away_teams)
    else:
        st.sidebar.caption(f"Selected live fixture: {home_club} vs {away_club}")
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Manual Context Adjustments")
    home_modifier = st.sidebar.slider(f"{home_club} Performance Shift (%)", min_value=-10, max_value=10, value=0, step=1)
    away_modifier = st.sidebar.slider(f"{away_club} Performance Shift (%)", min_value=-10, max_value=10, value=0, step=1)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("💰 1X2 Market Comparison")
    has_live_1x2 = all(live_prices[market] is not None for market in ("Home", "Draw", "Away"))
    use_live_1x2 = False
    if selected_fixture is not None and has_live_1x2:
        use_live_1x2 = st.sidebar.checkbox("Use selected bookmaker's live 1X2 prices", value=True)
    if use_live_1x2:
        odds_home, odds_draw, odds_away = (live_prices[key] for key in ("Home", "Draw", "Away"))
        st.sidebar.caption("Prices are from the selected bookmaker for this exact fixture.")
    else:
        odds_home = st.sidebar.number_input("Manual home (1) price", min_value=1.01, max_value=50.0, value=2.10, step=0.01)
        odds_draw = st.sidebar.number_input("Manual draw (X) price", min_value=1.01, max_value=50.0, value=3.40, step=0.01)
        odds_away = st.sidebar.number_input("Manual away (2) price", min_value=1.01, max_value=50.0, value=3.20, step=0.01)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Display Threshold")
    safety_barrier = st.sidebar.slider("Over 1.5 probability threshold (%)", min_value=50, max_value=95, value=80, step=5)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Over 1.5 Market Check")
    use_live_over_1_5 = False
    if selected_fixture is not None and live_prices["Over 1.5"] is not None:
        use_live_over_1_5 = st.sidebar.checkbox("Use selected bookmaker's live Over 1.5 price", value=True)
    if use_live_over_1_5:
        odds_over_1_5 = live_prices["Over 1.5"]
    else:
        odds_over_1_5 = st.sidebar.number_input(
            "Manual Over 1.5 odds (optional)",
            min_value=1.01,
            max_value=50.0,
            value=None,
            step=0.01,
            help="Leave blank if you do not have a current quote.",
        )
    
    st.sidebar.markdown("---")
    execute_sim = st.sidebar.button("Run match simulation", type="primary", use_container_width=True)
    
    forecast_cutoff = (
        pd.Timestamp(selected_fixture["commence_time"])
        if selected_fixture is not None
        else pd.Timestamp.now(tz="UTC")
    )
    try:
        h_goal_base, a_goal_base = estimate_goal_rates(
            df_filtered,
            home_club,
            away_club,
            as_of=forecast_cutoff,
        )
    except ValueError as error:
        st.error(str(error))
        st.stop()
    home_rows = df_filtered[df_filtered["home_team"].map(lambda team: teams_match(team, home_club))]
    away_rows = df_filtered[df_filtered["away_team"].map(lambda team: teams_match(team, away_club))]
    league_home_corners = df_filtered["home_corners"].mean()
    league_away_corners = df_filtered["away_corners"].mean()
    h_corn_base = home_rows["home_corners"].mean()
    a_corn_base = away_rows["away_corners"].mean()
    h_corn_base = h_corn_base if np.isfinite(h_corn_base) else league_home_corners
    a_corn_base = a_corn_base if np.isfinite(a_corn_base) else league_away_corners
    
    calibrated_h_goals = max(0.1, h_goal_base * (1 + (home_modifier / 100)))
    calibrated_a_goals = max(0.1, a_goal_base * (1 + (away_modifier / 100)))
    backtest = cached_backtest(df_filtered)
    home_history_count = int(
        (df_filtered["home_team"].map(lambda team: teams_match(team, home_club))
         | df_filtered["away_team"].map(lambda team: teams_match(team, home_club)))
        .loc[pd.to_datetime(df_filtered["date"], utc=True) < pd.Timestamp(forecast_cutoff)]
        .sum()
    )
    away_history_count = int(
        (df_filtered["home_team"].map(lambda team: teams_match(team, away_club))
         | df_filtered["away_team"].map(lambda team: teams_match(team, away_club)))
        .loc[pd.to_datetime(df_filtered["date"], utc=True) < pd.Timestamp(forecast_cutoff)]
        .sum()
    )
    archived_standings = standings_as_of(df_filtered, forecast_cutoff) if selected_fixture is not None else pd.DataFrame()
    
    # Static Data Monitoring Block
    st.markdown("### 📊 Database Footprint & Integrity Monitor")
    meta_col1, meta_col2, meta_col3, meta_col4 = st.columns(4)
    meta_col1.metric("Total Matches in Repository", f"{len(df_repo):,}")
    meta_col2.metric("Unique Indexed Teams", f"{len(available_teams)}")
    meta_col3.metric("Selected Division Pool", f"{len(df_filtered)}")
    meta_col4.info("Goal rates account for opponent defense and decay older matches.")

    if selected_fixture is not None:
        st.markdown("### Selected bookmaker prices")
        st.info(live_fixture_status)
        quote_columns = st.columns(4)
        quote_labels = (("Home", home_club), ("Draw", "Draw"), ("Away", away_club), ("Over 1.5", "Over 1.5 goals"))
        for column, (market, label) in zip(quote_columns, quote_labels):
            price = live_prices[market]
            column.metric(
                label,
                f"x{price:.2f}" if price is not None else "Unavailable",
                help=live_price_sources.get(market, "This market was not returned for the selected bookmaker."),
            )

        st.markdown("### Archive standings before kickoff")
        kickoff_utc = pd.Timestamp(forecast_cutoff)
        kickoff_utc = kickoff_utc.tz_localize("UTC") if kickoff_utc.tzinfo is None else kickoff_utc.tz_convert("UTC")
        prior_archive = df_filtered.loc[pd.to_datetime(df_filtered["date"], utc=True) < kickoff_utc]
        latest_archive_match = prior_archive["date"].max() if not prior_archive.empty else None
        if archived_standings.empty:
            st.warning("No prior results are available to calculate standings for this fixture.")
        else:
            st.caption(
                f"Calculated from the uploaded archive through {latest_archive_match.date()}; "
                "this is not a live external standings feed."
            )
            archive_age_days = (kickoff_utc - pd.Timestamp(latest_archive_match, tz="UTC")).days
            if archive_age_days > 90:
                st.warning(f"The latest archived result is {archive_age_days} days before kickoff; these standings are stale.")
            fixture_teams = archived_standings[
                archived_standings["Club"].map(
                    lambda team: teams_match(team, home_club) or teams_match(team, away_club)
                )
            ]
            if fixture_teams.empty:
                st.warning("Neither selected club appears in the uploaded archive before kickoff.")
            else:
                st.dataframe(fixture_teams, hide_index=True, width="stretch")
        if min(home_history_count, away_history_count) < 5:
            st.warning(
                f"Limited archive history: {home_club} has {home_history_count} prior matches and "
                f"{away_club} has {away_history_count}. Team rates rely heavily on league averages."
            )


    st.markdown("### Time-ordered historical evaluation")
    if backtest["matches"]:
        eval_col1, eval_col2, eval_col3, eval_col4, eval_col5 = st.columns(5)
        eval_col1.metric("Held-out matches", f"{backtest['matches']:,}")
        eval_col2.metric("1X2 accuracy", f"{backtest['accuracy_1x2']:.1f}%")
        if backtest["over_1_5_high_confidence_count"]:
            high_confidence_value = (
                f"{backtest['over_1_5_high_confidence_hit_rate']:.1f}% "
                f"(n={backtest['over_1_5_high_confidence_count']})"
            )
        else:
            high_confidence_value = "No forecasts at 85%+"
        eval_col3.metric("Over 1.5 hit rate (forecast ≥85%)", high_confidence_value)
        eval_col4.metric(
            "1X2 log loss",
            f"{backtest['log_loss_1x2']:.3f}",
            f"{backtest['log_loss_1x2'] - backtest['log_loss_1x2_baseline']:+.3f} vs league baseline",
            delta_color="inverse",
        )
        eval_col5.metric(
            "Over 1.5 Brier score",
            f"{backtest['brier_over_1_5']:.3f}",
            f"{backtest['brier_over_1_5'] - backtest['brier_over_1_5_baseline']:+.3f} vs league baseline",
            delta_color="inverse",
        )
        st.caption(
            f"Each forecast uses only earlier dates. Lower log loss and Brier scores are better. "
            f"1X2 Brier: {backtest['brier_1x2']:.3f} vs league baseline {backtest['brier_1x2_baseline']:.3f}. "
            "High-threshold hit rate is based only on qualifying picks; these historical scores are not a guarantee of future performance."
        )
    else:
        st.warning("Not enough earlier matches for a meaningful time-ordered evaluation (minimum 30).")
    
    # --- RENDER GATE CONTAINER LAYER ---
    if execute_sim:
        sim = poisson_market_probabilities(calibrated_h_goals, calibrated_a_goals, h_corn_base, a_corn_base)
        
        st.markdown("---")
        st.subheader(f"Simulation estimates: {home_club} vs {away_club}")
        
        st.markdown("#### Model estimate for over 1.5 goals")
        if odds_over_1_5 is None:
            st.info(
                f"**Simulated probability:** {sim['over_1_5']:.1f}%. "
                "No Over 1.5 bookmaker price is available for comparison. This is not a betting recommendation."
            )
        else:
            implied_bookie_prob = (1 / odds_over_1_5) * 100
            threshold_message = (
                f"This estimate clears your {safety_barrier}% threshold."
                if sim["over_1_5"] >= safety_barrier
                else f"This estimate is below your {safety_barrier}% threshold."
            )
            st.info(
                f"**Simulated probability:** {sim['over_1_5']:.1f}%. {threshold_message} "
                f"Odds x{odds_over_1_5:.2f} have a break-even probability of {implied_bookie_prob:.1f}%; "
                "without an opposing quote and historical calibration, this is not a value or safety verdict."
            )

        st.markdown("---")
        st.markdown("#### 1X2 model comparison with no-vig market probabilities")
        total_book = (1/odds_home) + (1/odds_draw) + (1/odds_away)
        market_h_prob = (1 / odds_home) / total_book * 100
        market_d_prob = (1 / odds_draw) / total_book * 100
        market_a_prob = (1 / odds_away) / total_book * 100
        fair_h_odds = round(100 / market_h_prob, 2)
        fair_d_odds = round(100 / market_d_prob, 2)
        fair_a_odds = round(100 / market_a_prob, 2)
        edge_col1, edge_col2, edge_col3 = st.columns(3)
        edge_col1.metric(f"{home_club} win (no-vig market: {market_h_prob:.1f}%, fair x{fair_h_odds})", f"{sim['home_win']:.1f}%", f"{sim['home_win'] - market_h_prob:+.1f} pp vs market")
        edge_col2.metric(f"Draw (no-vig market: {market_d_prob:.1f}%, fair x{fair_d_odds})", f"{sim['draw']:.1f}%", f"{sim['draw'] - market_d_prob:+.1f} pp vs market")
        edge_col3.metric(f"{away_club} win (no-vig market: {market_a_prob:.1f}%, fair x{fair_a_odds})", f"{sim['away_win']:.1f}%", f"{sim['away_win'] - market_a_prob:+.1f} pp vs market")
        st.markdown("---")
        st.markdown("#### ⚽ Primary Match & Goal Lines")
        col1, col2, col3 = st.columns(3)
        col1.metric("Simulated Over 1.5 Probability", f"{sim['over_1_5']:.1f}%")
        col2.metric("Both Teams to Score (BTTS)", f"{sim['btts_yes']:.1f}%")
        col3.metric("Simulated Over 2.5 Probability", f"{sim['over_2_5']:.1f}%")
        st.markdown("---")
        st.markdown("#### 🕒 First Half & Individual Team Scores")
        col4, col5, col6 = st.columns(3)
        col4.metric("First half over 0.5 goals", f"{sim['first_half_over_0_5']:.1f}%")
        col5.metric(f"{home_club} Over 0.5 (Scores)", f"{sim['home_score']:.1f}%")
        col6.metric(f"{away_club} Over 0.5 (Scores)", f"{sim['away_score']:.1f}%")
        st.caption("Half-time estimates assume 44% of goals occur in the first half; this split is not calibrated to this dataset.")
        st.markdown("---")
        st.markdown("#### 🛡️ Double Chance & Corner Matrix Lines")
        dc_col1, dc_col2, dc_col3 = st.columns(3)
        dc_col1.metric("Double Chance 1X (Home/Draw)", f"{sim['home_win']+sim['draw']:.1f}%")
        dc_col2.metric("Double Chance X2 (Away/Draw)", f"{sim['away_win']+sim['draw']:.1f}%")
        dc_col3.metric("Double Chance 12 (Home/Away)", f"{sim['home_win']+sim['away_win']:.1f}%")
        corn_col1, corn_col2, corn_col3 = st.columns(3)
        corn_col1.metric("Total Corners Over 8.5", f"{sim['corners_over_8_5']:.1f}%")
        corn_col2.metric(f"{home_club} Corners Over 4.5", f"{sim['home_corners_over_4_5']:.1f}%")
        corn_col3.metric(f"{away_club} Corners Over 3.5", f"{sim['away_corners_over_3_5']:.1f}%")
        st.caption("Corner estimates use venue-specific team averages and independent Poisson counts; they are not opponent-adjusted or backtested separately.")
        st.markdown("---")
        st.markdown("### Additional Poisson estimates")
        alt_col1, alt_col2, alt_col3 = st.columns(3)
        alt_col1.metric(label="Draw No Bet (DNB 1) Home Advantage", value=f"{sim['dnb_home']:.1f}%")
        alt_col2.metric(label="Goal Bracket: 2-3 Multi-Goals", value=f"{sim['multigoal_2_3']:.1f}%")
        alt_col3.metric(label="Home Team to Win Either Half (WEH)", value=f"{sim['weh_home']:.1f}%")
        st.markdown("---")
        st.markdown("#### 📊 Correct Score Probability Heatmap Grid (%)")
        matrix_index_labels = [f"Home {g}" for g in range(6)]
        matrix_column_labels = [f"Away {g}" for g in range(6)]
        df_heatmap = pd.DataFrame(sim["heatmap"], index=matrix_index_labels, columns=matrix_column_labels)
    # 🟢 THE NEW SYNTAX: Replaced .applymap() with .map() for flawless rendering!
        st.dataframe(df_heatmap.map(lambda x: f"{x:.2f}%"), width="stretch")

    else:
        st.info("Adjust the sidebar inputs and run the simulation to view estimated outcomes. These estimates are not betting advice.")
else:
    st.info("💡 Local Simulation Portal Standby: Please upload your Clean Master Database CSV file via the sidebar to initialize the 10,000-iteration Monte Carlo score matrix layers.")
    
