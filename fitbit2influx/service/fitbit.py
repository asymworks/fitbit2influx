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


def get_heartrate(app, since='today', detail='1min'):
    '''
    Get Heart Rate Data

    This calls the Fitbit Heart Rate Intraday Time Series endpoint with the
    parameters taken from argument values. The `since` parameter specifies
    the starting date and time for the measurement or can contain the string
    `today`, which will return all points from today.
    
    Note that the Fitbit API only returns intraday data within a single day,
    so this method will send multiple requests for each day of data from the
    `since` parameter until today.  If the `since` parameter is a `datetime`
    object, the time will also be used to filter out points before the time
    given. Note that the `datetime` instances will be interpreted as user-local
    time by Fitbit and no timezone data is passed, so the instances should be 
    naive objects without timezone data.

    The return value is an array of (`dt`, `bpm`) tuples where the `dt` value
    is a naive `datetime` object in the Fitbit-local time zone and `bpm` is the
    heart rate in beats per minute.
    '''
    today = datetime.date.today()
    f_date = datetime.date.today()
    f_time = datetime.datetime.now().replace(
        hour=0, minute=0, second=0, microsecond=0,
    )

    if isinstance(since, datetime.datetime):
        f_date = since.date()
        f_time = since

    elif isinstance(since, datetime.date):
        f_date = since
        f_time = datetime.datetime.combine(since, datetime.time())

    # Fetch day by day through today
    ret_data = []
    while f_date <= today:
        hr_endpoint = f'date/{f_date.strftime("%Y-%m-%d")}/1d/{detail}.json'
        hr_data = api_get(app, f'/1/user/-/activities/heart/{hr_endpoint}')

        if 'activities-heart-intraday' not in hr_data:
            raise ApiError(
                f'Did not receive intraday heart rate data from {hr_endpoint}'
            )

        # Convert Fitbit hh:mm:ss tags to datetime objects
        for pt in hr_data['activities-heart-intraday']['dataset']:
            h, m, s = [int(x) for x in pt['time'].split(':')]
            dt = datetime.datetime.combine(f_date, datetime.time(h, m, s))

            if dt >= f_time:
                ret_data.append((dt, pt['value']))

        # Increment the Fetch Day
        f_date += datetime.timedelta(days=1)

    # Return fetched data
    return ret_data
