import os
import email.utils
import email.parser

import arrow

from . import config


def emaildate_to_arrow(date):
    return arrow.get(email.utils.mktime_tz(email.utils.parsedate_tz(date)))


def msg_from_hit(hit):
    """Return an email.Message based on the path in a given Whoosh Hit object"""
    path = os.path.join(config.DOCUMENTS_DIR, hit['path'])
    parser = email.parser.Parser()
    with open(path, 'rb') as fd:
        return parser.parse(fd)

