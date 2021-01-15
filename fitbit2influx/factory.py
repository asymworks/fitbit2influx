# Fitbit2Influx Applicatin Factory

import configparser
import pathlib
import os

from flask import Flask


def read_version():
    '''Read the Name and Version String from pyproject.toml'''
    # Search for pyproject.toml
    d = pathlib.Path(__file__)
    name = None
    version = None
    while d.parent != d:
        d = d.parent
        path = d / 'pyproject.toml'
        if path.exists():
            # Use configparser to parse toml like INI to avoid dependency on
            # tomlkit or similar
            config = configparser.ConfigParser()
            config.read(str(path))
            if 'tool.poetry' in config:
                name = config['tool.poetry'].get('name').strip('"\'')
                version = config['tool.poetry'].get('version').strip('"\'')
                return (name, version)

    return (None, None)

def create_app(app_config=None, app_name=None):
    '''
    Create and Configure the Application with the Flask `Application Factory`_
    pattern. The `app_config` dictionary will override configuration keys set
    via other methods, and is intended primarily for use in test frameworks to
    provide a predictable configuration for testing.

    :param app_config: configuration override values
    :type app_config: dict or None
    :param app_name: application name override
    :type app_name: str
    :returns: Flask application instance
    :rtype: :class:`Flask`
    '''
    app = Flask(
        'jadetree',
        static_folder='frontend/static',
        template_folder='frontend/templates'
    )

    # Load Application Name and Version from pyproject.toml
    pkg_name, pkg_version = read_version()
    app.config['APP_NAME'] = pkg_name
    app.config['APP_VERSION'] = pkg_version

    # Load Default Settings
    app.config.from_object('fitbit2influx.settings')

    # Load Configuration File from Environment
    if 'FB2I_CONFIG' in os.environ:
        app.config.from_envvar('FB2I_CONFIG')

    # Load Configuration Variables from Environment
    for k, v in os.environ.items():
        if k.startswith('FB2I_') and k != 'FB2I_CONFIG':
            app.config[k[5:]] = v

    # Load Factory Configuration
    if app_config is not None:
        if isinstance(app_config, dict):
            app.config.update(app_config)
        elif app_config.endswith('.py'):
            app.config.from_pyfile(app_config)

    # Override Application Name
    if app_name is not None:
        app.name = app_name

    try:
        
        # Initialize OAuth2
        from .service import oauth as oauth_service
        oauth_service.init_oauth(app)

        # Initialize InfluxDB
        from . import influx
        influx.init_app(app)

        # Register Blueprints
        from .blueprints import oauth
        app.register_blueprint(oauth.bp)

        # Initialize Import Scheduler and start. Note that Flask Debug mode
        # causes this to run twice, so the check ensures that the scheduler
        # is only set up in the Werkzeug main worker thread.
        is_dev = app.debug or os.environ.get('FLASK_ENV') == 'development'
        if not is_dev or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
            from . import scheduler
            scheduler.init_app(app)
            scheduler.scheduler.start()

        # Return Application
        return app

    except Exception as e:
        # Ensure startup exceptions get logged
        app.logger.exception(
            'Startup Error (%s): %s',
            e.__class__.__name__,
            str(e)
        )
        raise e
