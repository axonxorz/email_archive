import logging

from . import config
from .email_schema import email_schema
from .index import create_index, update_index


from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
