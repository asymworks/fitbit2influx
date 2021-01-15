# Fitbit2Influx Status Page
import shelve

from flask import Blueprint, current_app, render_template

from ..influx import influx
from ..scheduler import scheduler

bp = Blueprint('status', __name__, url_prefix='/', template_folder='templates')


@bp.route('/', methods=['GET'])
def status_index():
    '''Show the Index Status Page'''
    last_time = None
    last_count = None
    token_expires = None
    user_id = None
    with shelve.open(current_app.config['SHELVE_FILENAME'], 'r') as shelf:
        if 'last_point' in shelf:
            last_time = shelf['last_point']
        if 'last_count' in shelf:
            last_count = shelf['last_count']
        if 'expires' in shelf:
            token_expires = shelf['expires']
        if 'user_id' in shelf:
            user_id = shelf['user_id']

    return render_template(
        'status.html.j2',
        last_time=last_time,
        last_count=last_count,
        token_expires=token_expires,
        user_id=user_id,
        scheduler=scheduler,
        influx_uri=influx.client._baseurl,
        influx_db=influx.client._database,
    )


@bp.route('/debug', methods=['GET'])
def oauth_debug():
    '''Print OAuth2 Information'''
    oauth_data = {}
    with shelve.open(current_app.config['SHELVE_FILENAME'], 'r') as shelf:
        oauth_data = {
            'access_token': shelf['access_token'],
            'refresh_token': shelf['refresh_token'],
            'scope': shelf['scope'],
            'expires': shelf['expires'].isoformat(),
            'user_id': shelf['user_id'],
        }

    return oauth_data


@bp.route('/test', methods=['GET'])
def oauth_test():
    '''Print User Profile'''
    from ..service.fitbit import get_user_profile
    return get_user_profile(current_app)
