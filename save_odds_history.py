import requests
import csv
import os
from datetime import datetime, timedelta

API_KEY = "056d14ef7e81f82c5bc90515d2a09128"
HEADERS = {"x-apisports-key": API_KEY}
BOOKMAKER_NAME = "Bet365"  # Or "1xBet", etc.

def get_yesterday_date():
    return (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")

def fetch_completed_matches(date):
    url = f"https://v3.football.api-sports.io/fixtures?date={date}&status=FT"
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    return res.json().get("response", [])

def fetch_odds_for_fixture(fixture_id):
    url = f"https://v3.football.api-sports.io/odds?fixture={fixture_id}"
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    odds_data = res.json().get("response", [])

    for item in odds_data:
        for bookmaker in item.get("bookmakers", []):
            if bookmaker["name"] == BOOKMAKER_NAME:
                for bet in bookmaker["bets"]:
                    if bet["name"] == "Match Winner":
                        odds = {o["value"]: o["odd"] for o in bet["values"]}
                        return odds
    return {}

def determine_result(goals):
    home, away = goals.get("home"), goals.get("away")
    if home is None or away is None:
        return "Unknown"
    if home > away:
        return "H"
    elif home < away:
        return "A"
    else:
        return "D"

def save_to_csv(row):
    file_exists = os.path.isfile("odds_history.csv")
    with open("odds_history.csv", "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["date", "home_team", "away_team", "home_odds", "draw_odds", "away_odds", "result"])
        writer.writerow([
            row["date"], row["home_team"], row["away_team"],
            row["home_odds"], row["draw_odds"], row["away_odds"], row["result"]
        ])

def run():
    date = get_yesterday_date()
    matches = fetch_completed_matches(date)

    for match in matches:
        fixture = match["fixture"]
        teams = match["teams"]
        goals = match["goals"]
        fixture_id = fixture["id"]

        odds = fetch_odds_for_fixture(fixture_id)
        if not odds:
            continue

        row = {
            "date": fixture["date"].split("T")[0],
            "home_team": teams["home"]["name"],
            "away_team": teams["away"]["name"],
            "home_odds": odds.get("Home", ""),
            "draw_odds": odds.get("Draw", ""),
            "away_odds": odds.get("Away", ""),
            "result": determine_result(goals)
        }
        save_to_csv(row)
        print(f"Saved: {row['home_team']} vs {row['away_team']}")

if __name__ == "__main__":
    run()
