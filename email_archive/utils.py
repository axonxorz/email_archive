import os
import email.utils
import email.parser
from gzip import GzipFile

import arrow

from .config import Configuration


def emaildate_to_arrow(date):
    return arrow.get(email.utils.mktime_tz(email.utils.parsedate_tz(date)))


def msg_from_hit(hit):
    """Return an email.Message based on the path in a given Whoosh Hit object"""
    path = os.path.join(Configuration.ARCHIVE_DIR, hit['path'])
    parser = email.parser.Parser()
    fd = None
    try:
        fd = open(path, 'rb')
        return parser.parse(fd)
    finally:
        if fd:
            fd.close()


def email_get_body(message):
    """Make a best-effort guess at which part of an email message is the body and return it.
    Prefers text/html over text/plain. Non-multipart messages will be returned in full.
    Always returns a Message or MIME* object"""
    if not message.is_multipart():
        return message
    else:
        html_part = None
        text_part = None
        for part in message.walk():
            content_type = part.get('Content-Type', 'application/octet-stream')
            if not part.is_multipart():
                if 'text/html' in content_type:
                    html_part = part
                if 'text/plain' in content_type:
                    text_part = part
        return html_part or text_part or None


def email_has_attachments(message):
    """Make a best-effort guess if an email has attachments. Skips text/html and text/plain"""
    if not message.is_multipart():
        return False

    found = False
    for part in message.walk():
        content_type = part.get('Content-Type', 'application/octet-stream')
        if 'text/html' in content_type or \
        'text/plain' in content_type:
            continue
        found = True

    return found

open_real = open  # We will shadow the original open shortly
def open(path, mode='rb'):
    """Transparently open regular and Gzipped files"""
    fd = open_real(path, mode)
    if fd.read(2) == '\x1f\x8b':
        fd.seek(0)
        return GzipFile(fileobj=fd)
    else:
        fd.seek(0)
        return fd
