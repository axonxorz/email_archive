#!/usr/bin/env python
import os
import sys
import email.utils
from email.parser import Parser

import whoosh.index
from whoosh.writing import BufferedWriter

from . import config
from .email_schema import email_schema
from .utils import emaildate_to_arrow


def create_index():
    if not os.path.exists(config.INDEX_DIR):
        os.mkdir(config.INDEX_DIR)
    if whoosh.index.exists_in(config.INDEX_DIR):
        print 'Index already exists in {}, refusing to clear it.'.format(config.INDEX_DIR)
        sys.exit(1)
    ix = whoosh.index.create_in(config.INDEX_DIR, email_schema)
    print 'Created index in {}'.format(config.INDEX_DIR)


def perform_index():
    message_parser = Parser()
    ix = whoosh.index.open_dir(config.INDEX_DIR)

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

                    message_id = message['Message-Id']
                    msg_subject = message.get('Subject', '')
                    msg_date = emaildate_to_arrow(message['Date']).naive
                    msg_from = message['From']
                    msg_to = message['To']

                    writer.update_document(message_id=message_id.decode('utf8'),
                                           path=message_path,
                                           from_addr=msg_from.decode('utf8'),
                                           to_addr=msg_to.decode('utf8'),
                                           date=msg_date,
                                           subject=msg_subject.decode('utf8'),
                                           body=u'Foo')

                    print 'Indexed {}'.format(message_id)
    finally:
        writer.commit()
