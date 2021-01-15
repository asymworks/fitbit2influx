# Fitbit2Influx Error Classes

class Error(Exception):
    '''Base Class for Fitbit2Influx Errors'''
    default_code = 500

    def __init__(self, *args, **kwargs):
        self.status_code = kwargs.pop(
            'status_code', self.__class__.default_code
        )
        super(Error, self).__init__(*args, **kwargs)


class AuthError(Error):
    '''Base Class for Authentication/Authorization Errors'''
    pass


class Unauthorized(AuthError):
    '''Exception raised when access to a resource is not allowed'''
    pass


class ConfigError(Error):
    '''
    Exception raised for invalid or missing configuration values.

    .. attribute:: config_key
        :type: str

        Configuration key which is missing or invalid

    '''
    def __init__(self, *args, config_key=None):
        super(ConfigError, self).__init__(*args)
        self.config_key = config_key


class ApiError(Error):
    '''Exception Raised when the Fitbit API returns an error'''
    @classmethod
    def from_response(cls, json):
        '''Construct an API Error from a JSON Response'''
        if 'success' not in json:
            return ApiError('Unexpected Response')

        if json['success']:
            return ApiError('Success')

        if 'errors' not in json:
            return ApiError('Unknown Error')

        if len(json['errors']) == 1:
            err_type = json['errors'][0].get('errorType', 'unknown')
            err_msg = json['errors'][0].get('message', '(no message)')
            return ApiError(f'{err_msg} ({err_type})')

        errs = '\n'.join([
            f'{e.get("message", "[no message]")} '
            f'({e.get("errorType", "unknown")})'
            for e in json['errors']
        ])
        return ApiError(f'Multiple API Errors: {errs}')


class NeedAuthError(Error):
    '''Exception Raised when the client has not authorized with Fitbit'''
    pass
