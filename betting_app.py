from datetime import datetime
import streamlit as st
import pandas as pd
import requests
import joblib

# ----------------------------
# Load trained model
# ----------------------------
@st.cache_resource
def load_model():
    return joblib.load("random_forest_model.joblib")

model = load_model()
API_KEY = "056d14ef7e81f82c5bc90515d2a09128"

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
    df["total"] = df["home_odds"] + df["draw_odds"] + df["away_odds"]
    df["Norm_H"] = df["home_odds"] / df["total"]
    df["Norm_D"] = df["draw_odds"] / df["total"]
    df["Norm_A"] = df["away_odds"] / df["total"]
    df["H_D_ratio"] = df["home_odds"] / df["draw_odds"]
    df["H_A_ratio"] = df["home_odds"] / df["away_odds"]
    df["D_A_ratio"] = df["draw_odds"] / df["away_odds"]
    df["Odds_Spread"] = df[["home_odds", "draw_odds", "away_odds"]].max(axis=1) - df[["home_odds", "draw_odds", "away_odds"]].min(axis=1)

    # 🔧 Add mock values for the missing features (you can replace with real data later)
    df["HomeTeamWinRate"] = 0.5
    df["AwayTeamWinRate"] = 0.5
    df["RecentForm"] = 0.5
    df["HomeRecentForm"] = 0.5
    df["AwayRecentForm"] = 0.5

    features = [
        "Norm_H", "Norm_D", "Norm_A",
        "H_A_ratio", "D_A_ratio", "H_D_ratio",
        "Odds_Spread",
        "HomeTeamWinRate", "AwayTeamWinRate",
        "RecentForm", "HomeRecentForm", "AwayRecentForm"
    ]
    return df[features]

# ----------------------------
# Predict + Recommendation
# ----------------------------
def make_predictions(df):
    X = prepare_features(df)
    preds = model.predict(X)
    df["prediction"] = preds
    df["recommended_bet"] = df["prediction"].map({
        "H": "Bet Home",
        "D": "Bet Draw",
        "A": "Bet Away"
    })
    return df

# ----------------------------
# Streamlit Layout
# ----------------------------
st.set_page_config(page_title="Betting Predictor MVP", layout="wide")
st.title("⚽ Betting Prediction MVP")
st.markdown("Live match predictions with model-backed betting suggestions.")

matches_df = fetch_upcoming_matches()

if matches_df.empty:
    st.warning("No matches available yet.")
else:
    predictions_df = make_predictions(matches_df)
    st.dataframe(predictions_df[[
        "home_team", "away_team", "home_odds", "draw_odds", "away_odds",
        "prediction", "recommended_bet"
    ]])
