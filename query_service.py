from collections import defaultdict

import pandas as pd
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


def get_miner_shares(miner_id, start_date, end_date):
    try:
        params = {
            'start': start_date,
            'end': end_date
        }
        response = requests.get(API_URL + f"/miner/{miner_id}/share", params=params)
        if response.ok:
            # create a dataframe from the share data
            frame = pd.json_normalize(response.json())
            # convert the time strings into a tz aware datetime
            frame['start'] = pd.to_datetime(frame['start']).dt.tz_localize('UTC')
            return frame
        else:
            print(response)

    except requests.exceptions.RequestException as e:
        print(e)


def get_miner_healths(miner_id, start_date, end_date):
    try:
        params = {
            'start': start_date,
            'end': end_date
        }
        response = requests.get(API_URL + f"/miner/{miner_id}/health", params=params)
        if response.ok:
            # create a dataframe from the share share_data
            frame = pd.json_normalize(response.json())
            # convert the time strings into a tz aware datetime
            frame['start'] = pd.to_datetime(frame['start']).dt.tz_localize('UTC')
            frame['fan_speed'] = frame['fan_speed'] / 100
            frame['hashrate'] = frame['hashrate'] / 1000000
            return frame
        else:
            print(response)

    except requests.exceptions.RequestException as e:
        print(e)
