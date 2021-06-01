from collections import defaultdict

import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_URL = os.getenv('API_URL')


def get_users():
    try:
        users = []
        response = requests.get(API_URL + '/user/')
        if response.status_code == 200:
            for user in response.json().get('data'):
                users.append(
                    {
                        'label': user['username'],
                        'value': user['id']
                    }
                )
            return users

    except requests.exceptions.RequestException as e:
        print(e)


def get_miners(user_id):
    try:
        miners = []
        response = requests.get(API_URL + f"/miner/{user_id}")
        if response.status_code == 200 and response.json().get('data') is not None:
            for miner in response.json().get('data'):
                miners.append(
                    {
                        'label': miner['name'],
                        'value': miner['id']
                    }
                )
            return miners


    except requests.exceptions.RequestException as e:
        print(e)
        return None


def get_miner_shares(miner_id):
    try:
        response = requests.get(API_URL + f"/miner/{miner_id}/share")
        if response.status_code == 200 and response.json() is not None:
            return response.json()

    except requests.exceptions.RequestException as e:
        print(e)

    return None

