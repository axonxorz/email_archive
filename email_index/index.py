#!/usr/bin/env python
import os
import sys
import email.utils
import base64
import quopri
from email.parser import Parser

import whoosh.index
from whoosh.writing import BufferedWriter

from . import config
from .email_schema import email_schema
from .utils import emaildate_to_arrow, email_get_body, email_has_attachments


def create_index():
    if not os.path.exists(config.INDEX_DIR):
        os.mkdir(config.INDEX_DIR)
    if whoosh.index.exists_in(config.INDEX_DIR):
        print 'Index already exists in {}, refusing to clear it.'.format(config.INDEX_DIR)
        return False
    ix = whoosh.index.create_in(config.INDEX_DIR, email_schema)
    print 'Created index in {}'.format(config.INDEX_DIR)


def get_index():
    if not whoosh.index.exists_in(config.INDEX_DIR):
        print 'Index does not exist in {}'.format(config.INDEX_DIR)
        return False
    ix = whoosh.index.open_dir(config.INDEX_DIR)
    return ix


def update_index():
    message_parser = Parser()
    ix = get_index()

    writer = ix.writer()
    try:
        documents_path = config.DOCUMENTS_DIR
        for root, dirs, files in os.walk(documents_path):
            for filename in files:
                file_path = os.path.join(root, filename)
                message_path = file_path.replace(config.DOCUMENTS_DIR, '').lstrip('/').decode('utf8')

                with open(file_path, 'rb') as fd:
                    message = message_parser.parse(fd)
                    headers = message.keys()

                    try:
                        message_id = message['Message-Id']
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
                                except UnicodeDecodeError, e:
                                    print file_path
                                    print 'Could not encode body_text as unicode:', e
                                    print 'Message likely has incorrect charset specified, falling back to safe conversion'
                                    print 'Context: {}'.format(body_text[e.start-20:e.end+20])
                                    print '         ' + '****'*4 + '   ^^^   ' + '****'*4
                                    body_text = body_text.decode(charset, 'ignore')
                            else:
                                # No charset specified, attempt to parse as UTF-8,
                                # or fail indexing with a warning
                                try:
                                    body_text = body_text.decode('utf8')
                                except UnicodeDecodeError:
                                    print file_path
                                    print 'No charset specified, could not decode body_text as UTF-8, skipping', e
                                    continue
                        else:
                            print 'Could not find body for {}'.format(message_id)
                            body_text = None
                    except ValueError, e:
                        print 'Unhandled exception', file_path
                        raise e

                    try:
                        writer.update_document(message_id=message_id.decode('utf8'),
                                            path=message_path,
                                            from_addr=msg_from.decode('utf8'),
                                            to_addr=msg_to.decode('utf8'),
                                            has_attachments=msg_has_attachments and u'yes' or u'no',
                                            date=msg_date,
                                            subject=msg_subject.decode('utf8'),
                                            body=body_text)
                    except ValueError, e:
                        print file_path
                        raise e

                    print 'Indexed {}'.format(message_id)
    finally:
        writer.commit()
