from flask import Flask, render_template, request
import requests
from datetime import datetime, timedelta, timezone
import pytz
import os
from dotenv import load_dotenv

load_dotenv()

# Flask インスタンスの作成時に、テンプレートフォルダと静的ファイルフォルダを正しく指定
app = Flask(__name__, template_folder="../templates", static_folder="../static")

API_TOKEN = os.environ.get('API_TOKEN')

def get_teams_in_league(competition_id):
    url = f"https://api.football-data.org/v4/competitions/{competition_id}/teams"
    headers = {"X-Auth-Token": API_TOKEN}
    response = requests.get(url, headers=headers)
    return response.json().get('teams', [])

def get_team_info(team_id):
    url = f"https://api.football-data.org/v4/teams/{team_id}"
    headers = {"X-Auth-Token": API_TOKEN}
    response = requests.get(url, headers=headers)
    return response.json()

def get_image_from_wikipedia(name):
    url = f"https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": name,
        "prop": "pageimages",
        "format": "json",
        "pithumbsize": 500
    }
    response = requests.get(url, params=params).json()
    pages = response["query"]["pages"]
    for page_id in pages:
        page = pages[page_id]
        if "thumbnail" in page:
            return page["thumbnail"]["source"]
    return None

def get_matches_for_week(competition_id, start_date):
    end_date = (start_date + timedelta(days=6))
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    url = f"https://api.football-data.org/v4/competitions/{competition_id}/matches?dateFrom={start_date_str}&dateTo={end_date_str}"
    headers = {"X-Auth-Token": API_TOKEN}
    response = requests.get(url, headers=headers)
    print(response.json())  # Print the response for debugging
    return response.json().get('matches', []), start_date_str, end_date_str

def convert_to_jst(utc_time_str):
    utc_time = datetime.strptime(utc_time_str, '%Y-%m-%dT%H:%M:%SZ')
    utc_time = utc_time.replace(tzinfo=pytz.UTC)
    jst_time = utc_time.astimezone(pytz.timezone('Asia/Tokyo'))
    return jst_time.strftime('%Y-%m-%d %H:%M')

def has_japanese_player(team_id):
    team_info = get_team_info(team_id)
    for player in team_info.get('squad', []):
        if player['nationality'] == 'Japan':
            return True
    return False

@app.route('/')
def index():
    competition_id = request.args.get('competition_id', '2021')  # Default to Premier League
    teams = get_teams_in_league(competition_id)
    leagues = {
        '2021': 'Premier League',
        '2014': 'La Liga',
        '2002': 'Bundesliga',
        '2019': 'Serie A'
    }
    return render_template('league-info.html', teams=teams, leagues=leagues, selected_competition=competition_id)

@app.route('/team/<int:team_id>')
def team(team_id):
    team_info = get_team_info(team_id)
    for player in team_info.get('squad', []):
        player['image'] = get_image_from_wikipedia(player['name']) or team_info['crest']
    
    coach_image = get_image_from_wikipedia(team_info['coach']['name']) or team_info['crest']
    team_info['coach']['image'] = coach_image
    
    return render_template('team-info.html', team=team_info)

@app.route('/schedule')
def schedule():
    competition_id = request.args.get('competition_id', '2021')  # Default to Premier League
    week_offset = int(request.args.get('week_offset', 0))
    today = datetime.now() + timedelta(weeks=week_offset)
    start_date = today - timedelta(days=today.weekday())  # Start from the beginning of the week (Monday)
    matches, start_date_str, end_date_str = get_matches_for_week(competition_id, start_date)
    for match in matches:
        match['utcDate'] = convert_to_jst(match['utcDate'])
        match['hasJapanesePlayer'] = has_japanese_player(match['homeTeam']['id']) or has_japanese_player(match['awayTeam']['id'])
    return render_template('schedule.html', matches=matches, week_offset=week_offset, competition_id=competition_id, start_date=start_date_str, end_date=end_date_str)

@app.route('/match/<int:match_id>')
def match(match_id):
    # Placeholder match data
    match_data = {
        "id": match_id,
        "homeTeam": "Home Team",
        "awayTeam": "Away Team",
        "score": "3 - 1",
        "time": "45'"
    }
    return render_template('match.html', match=match_data)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)

