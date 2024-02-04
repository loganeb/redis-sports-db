import requests
import redis
from redis.commands.json.path import Path
import time

USERNAME = 'default'
PASSWORD = 'pass123'

def get_redis_db(username, password):
    cred_provider = redis.UsernamePasswordCredentialProvider("default","pass123")
    return redis.Redis(host='localhost', port=6379, decode_responses=True, credential_provider=cred_provider)

def get_teams():
    res = requests.get('https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams')
    return res.json()

def import_teams(teams_list):
    db = get_redis_db(USERNAME, PASSWORD)
    for team in teams_list:
        team = team['team']
        print(f'Importing team: {team["name"]}')
        team_dict = {
            'name': team['name'],
            'displayName': team['displayName'],
            'abbreviation': team['abbreviation'],
            'id': team['id'],
            'location': team['location'],
            'color': team['color']  
        }
        db.hset(f'nba:team:{team["id"]}',mapping=team_dict)

def import_teams_json(teams_list):
    db = get_redis_db(USERNAME, PASSWORD)
    for team in teams_list:
        team = team['team']
        print(f'Importing team: {team["name"]}')
        team_dict = {
            'name': team['name'],
            'displayName': team['displayName'],
            'abbreviation': team['abbreviation'],
            'id': team['id'],
            'location': team['location'],
            'color': team['color']  
        }
        db.json().set(f'nba:team:{team["id"]}', Path.root_path(), team_dict)

def get_roster(team_id):
    res = requests.get(f'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_id}/roster')
    return res.json()

def transform_roster(roster, team_id):
    transformed_roster = []
    for player in roster['athletes']:
        transformed_roster.append({
            'id': player['id'],
            'firstName': player['firstName'],
            'lastName': player['lastName'],
            'displayName': player['displayName'],
            'height': player['height'],
            'weight': player['weight'],
            'age': player['age'],
            'position': player['position']['abbreviation'],
            'teamId': team_id
        })
    return transformed_roster

def import_roster_json(team_id):
    db = get_redis_db(USERNAME, PASSWORD)

    roster = get_roster(team_id)
    transformed_roster = transform_roster(roster, team_id)
    for athlete in transformed_roster:
        db.json().set(f'nba:roster:team:{team_id}:{athlete["id"]}', Path.root_path(), athlete)
    return transformed_roster

def get_player_stats(player_id):
    res = requests.get(f'https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{player_id}/stats')
    return res.json()

def transform_player_stats(raw_stats, player_id):
    transformed_stats = {}
    transformed_stats['playerId'] = player_id
    if not raw_stats.get('code'):
        if raw_stats.get('categories'):
            labels = raw_stats['categories'][0]['labels']
            for i in range(len(labels)):
                transformed_stats[labels[i]] = raw_stats['categories'][0]['totals'][i]
    return transformed_stats

def import_player_stats(player_id):
    raw_stats = get_player_stats(player_id)
    transformed_stats = transform_player_stats(raw_stats, player_id)

    db = get_redis_db(USERNAME,PASSWORD)
    db.json().set(f'nba:stats:averages:player:{player_id}', Path.root_path(), transformed_stats)


teams = get_teams()['sports'][0]['leagues'][0]['teams']

import_teams_json(teams)

for team in teams:
    print(f'Importing roster for {team["team"]["name"]} - ID:{team["team"]["id"]}')
    roster = import_roster_json(team['team']['id'])
    for athlete in roster:
        print(f'\tImporting avg stats for {athlete["displayName"]}')
        import_player_stats(athlete['id'])
        time.sleep(2)

# for team in teams:
#     roster = get_roster(team['team']['id'])
#     print(f'\n\tTeam: {team["team"]["displayName"]}')
#     print(f'\tID: {team["team"]["id"]}')
#     print(f'\tTotal players: {len(roster["athletes"])}')
#     time.sleep(0.2)
