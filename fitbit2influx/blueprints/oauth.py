# Fitbit2Influx OAuth2 Helpers

from flask import Blueprint, current_app, redirect, request

from fitbit2influx.error import NeedAuthError
from fitbit2influx.service import oauth as oauth_service

bp = Blueprint('oauth', __name__, url_prefix='/')


@bp.route('/authorize', methods=['GET'])
def oauth_authorize():
    '''Redirect to the Fitbit Authorization page'''
    if not current_app.config.get('OAUTH_AUTH_URL'):
        oauth_service.init_oauth(current_app)

    return redirect(current_app.config['OAUTH_AUTH_URL'])


@bp.route('/callback', methods=['GET'])
def oauth_callback():
    '''Receive an Authorization Token from Fitbit API'''
    oauth_service.request_tokens(current_app, request.args.get('code'))
    return redirect('/debug')


@bp.route('/refresh', methods=['GET'])
def oauth_refresh():
    '''Refresh OAuth2 Access Token'''
    try:
        oauth_service.refresh_tokens(current_app)
        return redirect('/debug')
    except NeedAuthError:
        return redirect('/authorize')
