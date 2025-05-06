import requests
from fastapi import FastAPI
import joblib
import numpy as np
import os

app = FastAPI()

API_KEY = "056d14ef7e81f82c5bc90515d2a09128"
model = joblib.load("random_forest_model.joblib")

def get_upcoming_matches():
    url = "https://v3.football.api-sports.io/fixtures?next=10"  # next 10 matches
    headers = {
        "x-apisports-key": API_KEY
    }
    response = requests.get(url, headers=headers)
    data = response.json()
    return data["response"]

def get_odds(fixture_id):
    url = f"https://v3.football.api-sports.io/odds?fixture={fixture_id}&bookmaker=6"  # Bet365 = ID 6
    headers = {
        "x-apisports-key": API_KEY
    }
    response = requests.get(url, headers=headers)
    odds_data = response.json()
    # Extract home, draw, away odds
    try:
        values = odds_data["response"][0]["bookmakers"][0]["bets"][0]["values"]
        odds = {item["value"]: float(item["odd"]) for item in values}
        return odds["Home"], odds["Draw"], odds["Away"]
    except:
        return None, None, None

@app.get("/predict/live")
def predict_upcoming_matches():
    matches = get_upcoming_matches()
    predictions = []

    for match in matches:
        fixture_id = match["fixture"]["id"]
        home_team = match["teams"]["home"]["name"]
        away_team = match["teams"]["away"]["name"]

        b365h, b365d, b365a = get_odds(fixture_id)
        if not b365h or not b365d or not b365a:
            continue  # skip if odds missing

        # You can enhance these with historical data if available
        home_win_rate = 0.5
        away_win_rate = 0.5
        recent_form = 0.0

        # Features (same logic as before)
        imp_h = 1 / b365h
        imp_d = 1 / b365d
        imp_a = 1 / b365a
        total_imp = imp_h + imp_d + imp_a

        norm_h = imp_h / total_imp
        norm_d = imp_d / total_imp
        norm_a = imp_a / total_imp
        h_a_ratio = b365h / b365a
        d_a_ratio = b365d / b365a
        h_d_ratio = b365h / b365d
        odds_spread = max([b365h, b365d, b365a]) - min([b365h, b365d, b365a])

        X = np.array([[
            norm_h, norm_d, norm_a,
            h_a_ratio, d_a_ratio, h_d_ratio,
            odds_spread,
            home_win_rate, away_win_rate,
            recent_form, home_win_rate, away_win_rate
        ]])

        prob = model.predict_proba(X)[0]
        pred = model.predict(X)[0]
        label = ["Home Win", "Draw", "Away Win"][pred]

        predictions.append({
            "match": f"{home_team} vs {away_team}",
            "prediction": label,
            "confidence": {
                "home_win": round(prob[0], 3),
                "draw": round(prob[1], 3),
                "away_win": round(prob[2], 3)
            }
        })

    return {"predictions": predictions}
