# Fitbit2Influx OAuth2 Service

import datetime
import requests
import shelve

from urllib.parse import quote, urlencode, urlunparse

from fitbit2influx.error import ApiError, ConfigError, NeedAuthError


def init_oauth(app):
    '''
    Construct the Fitbit Authorization URL 
    
    Construct the URL for Fitbit OAuth2 Authorization Code grants based on
    application configuration and store the URL back in the application config.
    '''
    cfg_keys = (
        'FITBIT_WEB_HOST',
        'FITBIT_API_HOST',
        'CLIENT_ID',
        'CLIENT_SECRET',
        'CALLBACK_URL',
        'SHELVE_FILENAME',
    )

    for k in cfg_keys:
        if k not in app.config:
            raise ConfigError(
                '{} must be defined in the application configuration'
                .format(k),
                config_key=k
            )

    # Currently this is hard-coded
    grants = ' '.join([
        'activity',
        'heartrate',
        'nutrition',
        'profile',
        'settings',
        'sleep',
    ])

    # Construct the Authorization URL
    auth_url_host = app.config['FITBIT_WEB_HOST']
    auth_url_path = '/oauth2/authorize'
    auth_url_args = urlencode(
        {
            'response_type': 'code',
            'client_id': app.config['CLIENT_ID'],
            'redirect_uri': app.config['CALLBACK_URL'],
            'scope': grants,
            'expires_in': str(app.config.get('TOKEN_VALIDITY', 604800)),
        },
        quote_via=quote
    )

    app.config['OAUTH_AUTH_URL'] = urlunparse(
        ('https', auth_url_host, auth_url_path, None, auth_url_args, None)
    )

    app.logger.info('Fitbit OAuth2 Initialized')


def update_tokens(app, token_data):
    '''Update the ShelveDB with the Token Data'''
    for k in ('access_token', 'refresh_token', 'expires_in', 'scope', 'user_id'):
        if k not in token_data:
            raise ApiError(f'Token request response did not include "{k}"')

    expires = datetime.datetime.utcnow() + datetime.timedelta(
        seconds=token_data['expires_in'],
    )

    with shelve.open(app.config['SHELVE_FILENAME'], 'c') as shelf:
        shelf['access_token'] = token_data['access_token']
        shelf['refresh_token'] = token_data['refresh_token']
        shelf['scope'] = token_data['scope'].split(' ')
        shelf['expires'] = expires
        shelf['user_id'] = token_data['user_id']


def request_tokens(app, code):
    '''Request new OAuth2 Tokens for the Application'''
    app.logger.info('Requesting OAuth2 access and refresh tokens')
    url_host = app.config['FITBIT_API_HOST']
    url_path = '/oauth2/token'
    response = requests.post(
        urlunparse(('https', url_host, url_path, None, None, None)),
        data={
            'clientid': app.config['CLIENT_ID'],
            'grant_type': 'authorization_code',
            'redirect_uri': app.config['CALLBACK_URL'],
            'code': code,
        },
        auth=(app.config['CLIENT_ID'], app.config['CLIENT_SECRET']),
    )

    data = response.json()
    if 'success' in data and not data['success']:
        raise ApiError.from_response(data)

    app.logger.info('Successfully authenticated with Fitbit')
    update_tokens(app, data)


def refresh_tokens(app):
    '''Refresh OAuth2 Tokens for the Application'''
    refresh_token = None
    with shelve.open(app.config['SHELVE_FILENAME'], 'r') as shelf:
        if 'refresh_token' in shelf:
            refresh_token = shelf['refresh_token']
    
    if refresh_token is None:
        raise NeedAuthError('No Refresh Token set')

    app.logger.info('Refreshing OAuth2 access token')
    url_host = app.config['FITBIT_API_HOST']
    url_path = '/oauth2/token'
    response = requests.post(
        urlunparse(('https', url_host, url_path, None, None, None)),
        data={
            'grant_type': 'refresh_token',
            'redirect_uri': app.config['CALLBACK_URL'],
            'refresh_token': refresh_token,
        },
        auth=(app.config['CLIENT_ID'], app.config['CLIENT_SECRET']),
    )

    data = response.json()
    if 'success' in data and not data['success']:
        raise ApiError.from_response(data)

    app.logger.info('Successfully refreshed OAuth2 access token')
    update_tokens(app, data)

    return data['access_token']


def get_api_token(app):
    '''
    Get the current API Bearer Token

    Returns the current token to be sent as a Bearer Token for an authenticated
    API request. If the token is expired, the refresh flow will be called and a
    new token will be provided.
    '''
    access_token = None
    expire_time = None
    with shelve.open(app.config['SHELVE_FILENAME'], 'r') as shelf:
        access_token = shelf.get('access_token', None)
        expire_time = shelf.get('expires', None)

    if access_token is None or expire_time is None:
        raise NeedAuthError('No Access Token set')

    if expire_time - datetime.datetime.utcnow() < datetime.timedelta(seconds=1):
        app.logger.debug('Access token expired - refreshing')
        return refresh_tokens(app)

    app.logger.debug('Using cached access token')
    return access_token
