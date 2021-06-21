from scipy import signal

import numpy as np
import pandas as pd
import pytz
import random
import matplotlib.pyplot as plt


def moving_average(x, w):
    return np.convolve(x, np.ones(w), mode='valid') / w


def round_down_to_odd(f):
    return max(int(np.ceil(f) // 2 * 2 + 1) - 2, 1)


def random_color():
    color = "#" + "%06x" % random.randint(0, 0xFFFFFF)
    return color


def get_cmap(n, name='hsv'):
    '''Returns a function that maps each index in 0, 1, ..., n-1 to a distinct
    RGB color; the keyword argument name must be a standard mpl colormap name.'''
    return plt.cm.get_cmap(name, n)


def sav_filter(xs, window_length):
    window_length = round_down_to_odd(window_length)
    window_length = max(window_length, 5)
    poly_order = min(int(window_length / 35), 3)
    return signal.savgol_filter(xs, round_down_to_odd(len(xs)), poly_order)


def json_to_df(data, timezone):
    df = pd.read_json(data)
    #print(df.head())
    # convert the string time to tz aware datetime
    df['start'] = pd.to_datetime(df['start'])
    # localize for the tz the user selects
    df['start'] = df['start'].dt.tz_convert(pytz.timezone(timezone))

    return df
