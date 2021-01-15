# Fitbit2Influx Scheduler Support

import datetime
import shelve

from apscheduler.schedulers.background import BackgroundScheduler
from flask import current_app
from functools import wraps

from fitbit2influx.influx import influx
from fitbit2influx.service.fitbit import get_heartrate, get_user_profile


class APScheduler(object):
    '''Flask Integration for APScheduler'''
    def __init__(self, scheduler=None, app=None):
        self._scheduler = scheduler or BackgroundScheduler()
        self.app = None
        if app:
            self.init_app(app)

    def init_app(self, app):
        '''Register the extension with the application'''
        self.app = app
        self.app.apscheduler = self
        self.app.logger.debug(f'Registering APScheduler with {self._scheduler.__class__.__name__} worker')

    @property
    def running(self):
        '''Return the Scheduler State'''
        return self._scheduler.state

    @property
    def scheduler(self):
        '''Get the currently active Scheduler'''
        return self._scheduler

    @property
    def task(self):
        '''Return a Task Decorator for the Scheduler'''
        return self._scheduler.scheduled_job

    @property
    def with_appcontext(self):
        '''
        Decorator to add a Flask Application Context to a Job

        Use this in conjunction with `APScheduler.task` as follows:

        ```
        from flask import current_app

        scheduler = APScheduler(app)

        @scheduler.task('cron', minutes='*')
        @scheduler.with_appcontext
        def run_every_minute():
            current_app.logger.info('Called run_every_minute()')
        
        ```
        '''
        def wrapper(func):
            @wraps(func)
            def inner(*args, **kwargs):
                with self.app.app_context():
                    func(*args, **kwargs)

            return inner

        return wrapper

    def start(self, paused=False):
        '''Start the scheduler, optionally in a paused state'''
        self.app.logger.info('Starting Scheduler')
        self._scheduler.start(paused=paused)

# TODO: Evaluate replacing with gevent Scheduler when deployed with gunicorn
#       using a gevent worker.

#: Fitbit2Influx Import Scheduler
scheduler = APScheduler()


# TODO: Make cron setup configurable
@scheduler.task('cron', minute='*/15')
@scheduler.with_appcontext
def import_data():
    current_app.logger.info('Downloading new Fitbit data')

    # Get the User Profile
    profile = get_user_profile(current_app)
    utc_offset = datetime.timedelta(milliseconds=profile['user']['offsetFromUTCMillis'])

    # Try and look up the last inserted timestamp
    last_pt = None
    with shelve.open(current_app.config['SHELVE_FILENAME'], 'r') as shelf:
        if 'last_point' in shelf:
            last_pt = shelf['last_point']

    # Load today's heart rate data
    hr_data = get_heartrate(current_app)

    # Filter for new data points
    if last_pt:
        new_pts = [pt for pt in hr_data if pt[0] > last_pt]
        if not len(new_pts):
            current_app.logger.info('No new heart rate points to send to InfluxDB')
            return

    else:
        new_pts = hr_data

    # Insert new data points
    json_pts = [
        {
            'measurement': 'heartRate',
            'time': (pt[0] - utc_offset).isoformat(),
            'fields': {
                'bpm': pt[1],
            },
        }
        for pt in new_pts
    ]

    ret = influx.client.write_points(
        json_pts,
        protocol='json',
        time_precision='s',
        tags={
            'userId': profile['user']['encodedId'],
        },
    )

    if not ret:
        current_app.logger.error('Failed to write data to Influx')

    # Save last retrieved data point
    current_app.logger.info(f'Inserting {len(new_pts)} new heart rate points')
    with shelve.open(current_app.config['SHELVE_FILENAME'], 'c') as shelf:
        shelf['last_point'] = new_pts[-1][0]


def init_app(app):
    '''Register the Scheduler with the Flask Application'''
    scheduler.init_app(app)
