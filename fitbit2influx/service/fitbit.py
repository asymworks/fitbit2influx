# Fitbit2Influx Fitbit Service

import datetime
from typing import Type
import requests

from urllib.parse import quote, urlencode, urlunparse

from fitbit2influx.error import ApiError

from .oauth import get_api_token

def api_get(app, url_endpoint, query=None, headers={}, **kwargs):
    '''Perform a GET request to the Fitbit API'''
    token = get_api_token(app)
    url_host = app.config['FITBIT_API_HOST']
    url_params = None
    if query is not None:
        url_params = urlencode(query, quote_via=quote)

    url = urlunparse(('https', url_host, url_endpoint, None, url_params, None))
    headers['Authorization'] = f'Bearer {token}'

    app.logger.debug(f'Sending GET to {url_endpoint}')
    response = requests.get(url, headers=headers, **kwargs)
    if response.status_code != 200:
        raise ApiError.from_response(response.json())

    return response.json()


def get_user_profile(app):
    '''Get the User Profile Data'''
    return api_get(app, '/1/user/-/profile.json')


def get_heartrate(app, start='today', end='1d', detail='1min'):
    '''
    Get Heart Rate Data

    This calls the Fitbit Heart Rate Intraday Time Series endpoint with the
    parameters taken from argument values. The `start` parameter specifies
    the start date for the measurement or can contain the string `today`, and
    the `end` parameter specifies the end date for the measurement or the
    string `1d`, which will retreive the whole day of data.
    
    If the `start` and `end` parameters are both `datetime.datetime` instances,
    the time values will be used to further constrain the data. Note that the
    `datetime.datetime` instances will be interpreted as user-local time by 
    Fitbit and no timezone data is passed, so the instances should be naive 
    objects without timezone data.

    The return value is an array of (`dt`, `bpm`) tuples where the `dt` value
    is a `datetime.datetime` object in the Fitbit-local time zone and `bpm` is
    the heart rate in beats per minute.
    '''
    s_date = start
    e_date = end
    i_time = None
    if isinstance(start, datetime.datetime) and isinstance(end, datetime.datetime):
        s_date = start.strftime('%Y-%m-%d')
        e_date = end.strftime('%Y-%m-%d')
        i_time = (
            start.strftime('%H:%M'),
            end.strftime('%H:%M')
        )

    if isinstance(s_date, datetime.date):
        s_date = start.strftime('%Y-%m-%d')
    if isinstance(e_date, datetime.date):
        e_date = end.strftime('%Y-%m-%d')

    if not isinstance(s_date, str):
        raise TypeError('Start date must be a string, date, or datetime object')
    if not isinstance(e_date, str):
        raise TypeError('End date must be a string, date, or datetime object')

    time_spec = f'date/{s_date}/{e_date}/{detail}'
    if i_time is not None:
        time_spec += f'/time/{i_time[0]}/{i_time[1]}'

    endpoint = f'/1/user/-/activities/heart/{time_spec}.json'
    hr_data = api_get(app, endpoint)

    # Determine the start date of the data
    start_date = datetime.datetime.strptime(hr_data['activities-heart'][0]['dateTime'], '%Y-%m-%d')

    # Process returned intra-day data and set UTC timestamps
    ret_data = []
    last_secs = 0
    offset_days = 0
    for pt in hr_data['activities-heart-intraday']['dataset']:
        h, m, s = [int(x) for x in pt['time'].split(':')]
        secs = h * 3600 + m * 60 + s

        # Detect a rollover to the next day
        if secs < last_secs:
            offset_days += 1

        # Save the point with a Python datetime
        offset = datetime.timedelta(days=offset_days, seconds=secs)
        ret_data.append((start_date + offset, pt['value']))

    return ret_data
