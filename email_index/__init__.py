import logging

from . import config
from .email_schema import email_schema
from .index import create_index, update_index


logging.basicConfig(level=logging.DEBUG)
