import tweepy
from nba_api.stats.endpoints import boxscoretraditionalv2, scoreboardv2
from nba_api.stats.library.http import NBAStatsHTTP
from datetime import datetime, timedelta, timezone
import time
import os
import requests

# ======================= #
# TWITTER AUTHENTICATION  #
# ======================= #
bearer_token = os.getenv("BEARER_TOKEN")
api_key = os.getenv("API_KEY")
api_secret = os.getenv("API_SECRET")
access_token = os.getenv("ACCESS_TOKEN")
access_token_secret = os.getenv("ACCESS_TOKEN_SECRET")

client = tweepy.Client(
    bearer_token=bearer_token,
    consumer_key=api_key,
    consumer_secret=api_secret,
    access_token=access_token,
    access_token_secret=access_token_secret
)

# ======================= #
#   NBA API HEADER FIX    #
# ======================= #
NBAStatsHTTP.headers = {
    'User-Agent': 'Mozilla/5.0',
    'x-nba-stats-origin': 'stats',
    'x-nba-stats-token': 'true',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en',
    'Origin': 'https://www.nba.com',
    'Referer': 'https://www.nba.com/'
}

# ======================= #
#     NBA STATS LOGIC     #
# ======================= #

def get_nba_game_date_str():
    # Automatically use yesterday's date (adjusted for EST)
    est_now = datetime.now(timezone.utc) - timedelta(hours=5)
    nba_date = est_now - timedelta(days=1)
    return nba_date.strftime("%m/%d/%Y")

def get_game_ids_for_date(date_str):
    retries = 3
    for i in range(retries):
        try:
            scoreboard = scoreboardv2.ScoreboardV2(game_date=date_str)
            games = scoreboard.get_normalized_dict()["GameHeader"]
            return [game["GAME_ID"] for game in games]
        except (requests.exceptions.ReadTimeout, Exception) as e:
            print(f"Attempt {i+1}/{retries} failed: {e}")
            time.sleep(2)
    raise Exception("Failed to fetch game IDs after multiple attempts.")

def get_stat_leaders(game_ids):
    top_points = {"name": "", "stat": 0}
    top_assists = {"name": "", "stat": 0}
    top_rebounds = {"name": "", "stat": 0}
    top_threes = {"name": "", "stat": 0}
    top_minutes = {"name": "", "stat": 0.0}

    for game_id in game_ids:
        time.sleep(0.6)
        boxscore = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game_id)
        players = boxscore.get_normalized_dict()["PlayerStats"]

        for p in players:
            if p["PTS"] is not None and p["PTS"] > top_points["stat"]:
                top_points = {"name": p["PLAYER_NAME"], "stat": p["PTS"]}
            if p["AST"] is not None and p["AST"] > top_assists["stat"]:
                top_assists = {"name": p["PLAYER_NAME"], "stat": p["AST"]}
            if p["REB"] is not None and p["REB"] > top_rebounds["stat"]:
                top_rebounds = {"name": p["PLAYER_NAME"], "stat": p["REB"]}
            if p["FG3M"] is not None and p["FG3M"] > top_threes["stat"]:
                top_threes = {"name": p["PLAYER_NAME"], "stat": p["FG3M"]}
            if p["MIN"]:
                try:
                    min_val = p["MIN"]
                    if ":" in min_val:
                        minutes_part = min_val.split(":")[0]
                        total_minutes = float(minutes_part)
                    else:
                        total_minutes = float(min_val)
                    if total_minutes > top_minutes["stat"]:
                        top_minutes = {"name": p["PLAYER_NAME"], "stat": round(total_minutes, 1)}
                except:
                    pass

    return top_points, top_assists, top_rebounds, top_threes, top_minutes

def compose_tweet(date_str, points, assists, rebounds, threes, minutes):
    tweet = f"""🏀 Stat Kings – {date_str}

🔥 Points Leader
{points['name']}: {points['stat']} PTS

🎯 Assists Leader
{assists['name']}: {assists['stat']} AST

💪 Rebounds Leader
{rebounds['name']}: {rebounds['stat']} REB

🏹 3PT Leader
{threes['name']}: {threes['stat']} 3PM

#NBA #NBATwitter #NBAStats #StatKingsHQ\n"""
    return tweet

# ======================= #
#        MAIN BOT         #
# ======================= #

def run_bot():
    date_str = get_nba_game_date_str()
    game_ids = get_game_ids_for_date(date_str)
    if not game_ids:
        print("No games found for", date_str)
        return

    points, assists, rebounds, threes, minutes = get_stat_leaders(game_ids)
    tweet = compose_tweet(date_str, points, assists, rebounds, threes, minutes)
    print("Tweeting:\n", tweet)
    client.create_tweet(text=tweet)

if __name__ == "__main__":
    run_bot()
