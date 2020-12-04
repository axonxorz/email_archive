import os
import email.utils
import email.parser
from gzip import GzipFile

import arrow


def addr_tokenize(header_value):
    """
    Tokenize an email From/To/CC/BCC header value into distinct email parts.
    If the "name" portion matches "localpart" exactly, only "email" is tokenized:
      - 'matthewc <matthewc@cpdist.ca>' => ['matthewc', 'matthewc@cpdist.ca']
      - '"\'Bob Dole\'" <bob.dole@example.com>' => ['bob', 'dole', 'bob.dole@example.com']
    """
    if header_value is None:
        return None
    values = header_value.split('\r\n')
    values = [x.strip() for x in values]
    values = filter(None, values)
    tokenized = []
    for value in values:
        parsed = email.utils.parseaddr(value)
        if parsed == ('', ''): continue  # unparseable
        parsed = [x.strip("'") for x in parsed]
        if parsed[1]:
            localpart = parsed[1].split('@')[0]
            if parsed[0] == localpart:
                parsed = [parsed[1]]
        tokenized.extend(filter(None, parsed))
    return tokenized


def emaildate_to_arrow(date):
    return arrow.get(email.utils.mktime_tz(email.utils.parsedate_tz(date)))


def email_get_body(message):
    """
    Make a best-effort guess at which part of an email message is the body and return it.
    Prefers text/html over text/plain. Non-multipart messages will be returned in full.
    Always returns a Message or MIME* object
    """
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


def email_attachment_details(message):
    """
    Make a best-effort list of attachment filenames and mimetypes,
    return a list of 2-tuples: [(<filename>, <mime>), ...]
    """
    if not message.is_multipart():
        parts = [message]
    else:
        parts = message.walk()

    attachments = []
    for part in parts:
        filename = part.get_filename('unknown.bin')
        content_type = part.get_content_type()
        if 'text/html' in content_type or 'text/plain' in content_type or content_type.startswith('multipart/'):
            continue
        attachments.append((filename, content_type))
    return attachments


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


def gz_open(path):
    """Transparently open regular and Gzipped files"""
    fd = open(path, 'rb')
    if fd.read(2) == b'\x1f\x8b':
        fd.seek(0)
        return GzipFile(fileobj=fd)
    else:
        fd.seek(0)
        return fd
