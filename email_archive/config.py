import os
from functools import wraps

import yaml


class ConfigurationError(Exception):
    """Error finding or reading configuration"""


def wrap_load(fn):
    """Decorator to cause a configuration parse if a Configuration attribute
    is accessed before the configuration is loaded"""

    @wraps(fn)
    def new_fn(instance):
        if not instance._loaded:
            instance.configure()
        return fn(instance)

    return new_fn


class _Configuration(object):
    """Represents the runtime configuration of the application"""

    paths = None

    _loaded = False

    _ARCHIVE_DIR = None
    _ARCHIVED_DOMAINS = None
    _ELASTIC = None
    _REDIS = None

    def __init__(self):
        self.paths = [os.path.join(os.getcwd(), 'email_archive.yml'),
                      '/etc/email_archive.yml']

    def set_paths(self, paths):
        """Override default configuration file paths. Raises a ValueError if configuration has already been loaded."""
        if self._loaded:
            raise ValueError('Cannot change configuration file paths, configuration already loaded')
        self.paths = paths

    def configure(self):
        """Attempt to configure the application using various configuration paths. The first found path is used."""
        for path in self.paths:
            if os.path.isfile(path):
                return self.read_conf(path)
        raise ConfigurationError('No valid configuration found', self.paths)

    def read_conf(self, path):
        with open(path, 'rb') as fd:
            conf = yaml.load(fd, Loader=yaml.SafeLoader)
        self._ARCHIVE_DIR = conf['main']['archive_dir']
        self._ARCHIVED_DOMAINS = conf['main'].get('archived_domains', [])
        self._ELASTIC = conf['main'].get('elastic', {})
        self._REDIS = conf['main'].get('redis', {})
        self._loaded = path

    def __repr__(self):
        if self._loaded:
            return '<{} {}>'.format(self.__class__.__name__, self._loaded)
        else:
            return '<{} unconfigured>'.format(self.__class__.__name__)

    @property
    @wrap_load
    def ARCHIVE_DIR(self):
        return self._ARCHIVE_DIR

    @property
    @wrap_load
    def ARCHIVED_DOMAINS(self):
        return self._ARCHIVED_DOMAINS

    @property
    @wrap_load
    def ELASTIC(self):
        return self._ELASTIC

    @property
    @wrap_load
    def REDIS(self):
        return self._REDIS


Configuration = _Configuration()
