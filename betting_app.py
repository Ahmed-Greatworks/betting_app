from datetime import datetime
import streamlit as st
import pandas as pd
import requests
import joblib

st.set_page_config(page_title="⚽ Betting Prediction MVP", layout="wide")

# ----------------------------
# Load trained model
# ----------------------------
@st.cache_resource
def load_model():
    return joblib.load("random_forest_model.joblib")

model = load_model()
API_KEY = "056d14ef7e81f82c5bc90515d2a09128"

def get_team_form_stats(team_id, season=2024, league_id=39):
    url = "https://v3.football.api-sports.io/teams/statistics"
    headers = {"x-apisports-key": API_KEY}
    params = {
        "team": team_id,
        "season": season,
        "league": league_id
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        stats = response.json()['response']
        return {
            "win_rate": stats["fixtures"]["wins"]["total"] / stats["fixtures"]["played"]["total"],
            "draw_rate": stats["fixtures"]["draws"]["total"] / stats["fixtures"]["played"]["total"],
            "loss_rate": stats["fixtures"]["loses"]["total"] / stats["fixtures"]["played"]["total"]
        }
    except Exception as e:
        st.error(f"Failed to fetch team stats for team {team_id}: {e}")
        return {
            "win_rate": 0.0,
            "draw_rate": 0.0,
            "loss_rate": 0.0
        }

# ----------------------------
# Fetch today's upcoming matches
# ----------------------------
def fetch_upcoming_matches():
    today = datetime.today().strftime('%Y-%m-%d')
    url = f"https://v3.football.api-sports.io/fixtures?date={today}"
    headers = {
        "x-apisports-key": API_KEY
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        matches = response.json().get("response", [])
        filtered = []

        for match in matches:
            if match["fixture"]["status"]["short"] == "NS":
                odds = fetch_odds(match["fixture"]["id"])
                if odds:
                    filtered.append({
                        "fixture_id": match["fixture"]["id"],
                        "home_team": match["teams"]["home"]["name"],
                        "away_team": match["teams"]["away"]["name"],
                        "home_odds": odds.get("Home", None),
                        "draw_odds": odds.get("Draw", None),
                        "away_odds": odds.get("Away", None)
                    })
        return pd.DataFrame(filtered)
    except Exception as e:
        st.error(f"Failed to fetch match data: {e}")
        return pd.DataFrame()

# ----------------------------
# Fetch 1X2 odds for a fixture
# ----------------------------
def fetch_odds(fixture_id):
    url = f"https://v3.football.api-sports.io/odds?fixture={fixture_id}"
    headers = {
        "x-apisports-key": API_KEY
    }
    try:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        data = res.json().get("response", [])

        for bookmaker in data[0]["bookmakers"]:
            if bookmaker["name"] == "Bet365":
                for bet in bookmaker["bets"]:
                    if bet["name"] == "Match Winner":
                        return {o["value"]: float(o["odd"]) for o in bet["values"]}
        return None
    except:
        return None

# ----------------------------
# Feature Engineering (simple example)
# ----------------------------
def prepare_features(df):
    feature_rows = []

    for _, row in df.iterrows():
        home_stats = get_team_form_stats(row["teams"]["home"]["id"])
        away_stats = get_team_form_stats(row["teams"]["away"]["id"])

        features = {
            "Norm_H": row.get("bookmakers_odds", {}).get("H", 0),
            "Norm_D": row.get("bookmakers_odds", {}).get("D", 0),
            "Norm_A": row.get("bookmakers_odds", {}).get("A", 0),
            "H_A_ratio": row.get("bookmakers_odds", {}).get("H", 1) / (row.get("bookmakers_odds", {}).get("A", 1) + 1e-5),
            "D_A_ratio": row.get("bookmakers_odds", {}).get("D", 1) / (row.get("bookmakers_odds", {}).get("A", 1) + 1e-5),
            "H_D_ratio": row.get("bookmakers_odds", {}).get("H", 1) / (row.get("bookmakers_odds", {}).get("D", 1) + 1e-5),
            "Odds_Spread": abs(row.get("bookmakers_odds", {}).get("H", 0) - row.get("bookmakers_odds", {}).get("A", 0)),
            "HomeTeamWinRate": home_stats["win_rate"],
            "AwayTeamWinRate": away_stats["win_rate"],
            "RecentForm": home_stats["win_rate"] - away_stats["win_rate"],  # crude difference
            "HomeRecentForm": home_stats["win_rate"],
            "AwayRecentForm": away_stats["win_rate"]
        }

        feature_rows.append(features)

    return pd.DataFrame(feature_rows)


# ----------------------------
# Predict + Recommendation
# ----------------------------
def make_predictions(df):
    X = prepare_features(df)
    preds = model.predict(X)
    df["prediction"] = preds
    df["recommended_bet"] = df["prediction"].map({
        0: "Bet Home",
        1: "Bet Draw",
        2: "Bet Away"
    })
    return df

st.markdown("⚽ Live match predictions with model-backed betting suggestions.")

matches_df = fetch_upcoming_matches()

if matches_df.empty:
    st.warning("No matches available yet.")
else:
    predictions_df = make_predictions(matches_df)
    st.dataframe(predictions_df[[
        "home_team", "away_team", "home_odds", "draw_odds", "away_odds",
        "prediction", "recommended_bet"
    ]])
