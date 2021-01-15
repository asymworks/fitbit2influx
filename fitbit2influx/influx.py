# Fitbit2InfluxDB Influx Connection

import influxdb


class InfluxDB(object):
    '''InfluxDB Helper for Flask'''
    def __init__(self, app=None):
        self._client = None
        self.app = app
        if app:
            self.init_app(app)

    def init_app(self, app):
        '''Setup the InfluxDB Connection'''
        client_args = {
            'host': app.config.get('INFLUX_HOST', 'localhost'),
            'port': app.config.get('INFLUX_PORT', 8086),
            'database': app.config.get('INFLUX_DATABASE', None),
            'username': app.config.get('INFLUX_USERNAME', None),
            'password': app.config.get('INFLUX_PASSWORD', None),
            'ssl': app.config.get('INFLUX_SSL', False),
            'verify_ssl': app.config.get('INFLUX_VERIFY_SSL', False),
        }

        self._client = influxdb.InfluxDBClient(**client_args)

        self.app = app
        self.app.influx = self

    @property
    def client(self):
        return self._client


#: InfluxDB Client
influx = InfluxDB()


def init_app(app):
    '''Initialize the InfluxDB Connection'''
    influx.init_app(app)
    app.logger.info('Initialized InfluxDB')
