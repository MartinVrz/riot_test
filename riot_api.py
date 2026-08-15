"""
Copied straight out of learning.ipynb so the Streamlit app can import it.
Nothing in here was rewritten or "fixed" - same functions, same logic.

NOT included because they don't run as-is in the notebook:
- get_ladder()        -> has a syntax error (mismatched brackets on the
                          .rename() call), so it can't even be imported.
- process_match_JSON() -> references a global `game` variable that's never
                          passed in, and builds the dict with {victory}
                          (curly braces = a set) instead of [victory],
                          which is exactly the "'set' type is unordered"
                          error you hit in the notebook.
Fix those in the notebook whenever you want, and the dashboard can pick
them up - just say the word.
"""

from dotenv import load_dotenv
import os
import requests

load_dotenv()

region = "europe"
api_key = os.environ.get("riot_api")
root_url = f"https://{region}.api.riotgames.com/"


def get_puuid(gamename, tagline, api_key):
    link = f"{root_url}riot/account/v1/accounts/by-riot-id/{gamename}/{tagline}?api_key={api_key}"
    response = requests.get(link)

    return response.json()["puuid"]


def get_opgg(puuid):
    link = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-puuid/{puuid}?api_key={api_key}"
    response = requests.get(link)

    return response.json()


def get_mastery(puuid):
    link = f"https://euw1.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/by-champion/121?api_key={api_key}"
    response = requests.get(link)

    return response.json()


def mastery_list(puuid):
    link = f"https://euw1.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}?api_key={api_key}"
    response = requests.get(link)

    return response.json()


def matches(region=None, puuid=None, start=0, count=1):
    query_param = f'?start={start}&count={count}'
    root = f'https://{region}.api.riotgames.com'
    endpoint = f'/lol/match/v5/matches/by-puuid/{puuid}/ids'

    response = requests.get(root + endpoint + query_param + "&api_key=" + api_key)
    return response.json()


def get_match_data(matchId=None, region=None):
    root = f'https://{region}.api.riotgames.com'
    endpoint = f'/lol/match/v5/matches/{matchId}'

    response = requests.get(root + endpoint + "?api_key=" + api_key)

    return response.json()


def json_extract(obj, key):
    arr = []

    def extract(obj, arr, key):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == key:
                    arr.append(v)
                elif isinstance(v, (dict, list)):
                    extract(v, arr, key)
        elif isinstance(obj, list):
            for item in obj:
                extract(item, arr, key)
        return arr

    values = extract(obj, arr, key)
    return values
