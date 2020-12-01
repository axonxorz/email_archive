#!/usr/bin/env python
import os
import sys
import email.utils
import base64
import quopri
from email.parser import Parser
import logging
from gzip import open as gzip_open

import bleach

from .config import Configuration
from .utils import emaildate_to_arrow, email_get_body, email_has_attachments


logger = logging.getLogger(__name__)


def create_index():
    raise NotImplementedError()


def process_message(message_path, message, writer):
    """Process a single email.Message object into the index"""
    message_id = message['Message-Id']
    if message_id is None:
        logger.warn('Skipping {}, could not find a Message-Id, probably an error parsing'.format(message_path))
        return False
    msg_subject = message.get('Subject', '')
    msg_date = emaildate_to_arrow(message['Date']).naive
    msg_from = message['From']
    msg_to = message['To']
    msg_has_attachments = email_has_attachments(message)

    msg_body = email_get_body(message)
    if msg_body is not None:
        encoding = msg_body.get('Content-Transfer-Encoding')
        charset = msg_body.get_param('charset')
        if encoding == 'quoted-printable':
            body_text = quopri.decodestring(msg_body.get_payload())
        elif encoding == 'base64':
            body_text = base64.b64decode(msg_body.get_payload())
        else:
            body_text = msg_body.get_payload()

        if charset is not None:
            try:
                body_text = body_text.decode(charset)
            except UnicodeDecodeError as e:
                logger.warn('Could not encode body_text as unicode: {}'.format(e))
                logger.warn('Message likely has incorrect charset specified, falling back to safe conversion')
                logger.warn('Context: {}'.format(body_text[e.start-20:e.end+20]))
                logger.warn('         ' + '****'*4 + '   ^^^   ' + '****'*4)
                body_text = body_text.decode(charset, 'ignore')
        else:
            # No charset specified, attempt to parse as UTF-8,
            # or fail indexing with a warning
            try:
                body_text = body_text.decode('utf8')
            except UnicodeDecodeError as e:
                logger.warn(message_path)
                logger.warn('No charset specified, and could not decode body_text as UTF-8, skipping message')
                logger.warn('Error: {}'.format(e))
                return

        if 'text/html' in msg_body.get('Content-Type', 'application/octet-stream'):
            body_text = bleach.clean(body_text, tags=[], attributes={}, styles=[], strip=True)

    else:
        logger.warn('Could not find body for {}, indexing message envelope only'.format(message_id))
        body_text = None

    writer.update_document(message_id=message_id.decode('utf8'),
                           path=message_path.decode('utf8'),
                           from_addr=msg_from.decode('utf8'),
                           to_addr=msg_to.decode('utf8'),
                           has_attachments=msg_has_attachments and 'yes' or 'no',
                           date=msg_date,
                           subject=msg_subject.decode('utf8'),
                           body=body_text)
    logger.info('Indexed {}'.format(message_id))
