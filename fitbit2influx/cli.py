# Fitbit2Influx Command Line Interface

import click
import datetime

from flask import current_app
from flask.cli import with_appcontext

from fitbit2influx.service import fitbit


@click.command()
@with_appcontext
def update():
    '''Download new Fitbit data and upload to InfluxDB'''
    current_app.logger.info('Updating Fitbit Data')
    
    # Pull User Profile to get UTC Offset
    user_info = fitbit.get_user_profile(current_app)
    utc_offset = datetime.timedelta(
        milliseconds=user_info['user']['offsetFromUTCMillis']
    )

    current_app.logger.debug(f'UTC Offset: {utc_offset.total_seconds() / 3600} hours')

    s = datetime.datetime(2021, 1, 12, 22, 0, 0)
    e = datetime.datetime(2021, 1, 13, 1, 0, 0)
    fitbit.get_heartrate(current_app, s, e)


def init_app(app):
    '''Initialize the CLI'''
    app.cli.add_command(update)
    app.logger.info('CLI Initialized')