#!/usr/bin/env python
import sys
import os
import email
import email.utils
import email.parser
import datetime
from gzip import open as gzip_open
import logging
import uuid

import redis

from .config import Configuration
from .fifo import FIFOQueue


logger = logging.getLogger(__name__)

ARCHIVE_DIR = Configuration.ARCHIVE_DIR
ARCHIVED_DOMAINS = [x.lower() for x in Configuration.ARCHIVED_DOMAINS]


def check_archived_domain(addresses):
    """Check addresses to see if any of them fall in the archived domain list.
    This is lazy as a matched domain could appear in the local-part of the address
    and trigger a match"""
    if addresses is None: return
    addresses = addresses.lower()
    for address in addresses.split(','):
        for domain in ARCHIVED_DOMAINS:
            if domain in address:
                return True


def archive_message(message):
    """Parse an email.Message object and archive it if eligible"""
    do_archive = False

    if 'Message-ID' in message:
        message_id = message['Message-ID']

        for addresses in [message.get('To'), message.get('From'), message.get('CC'), message.get('BCC')]:
            if check_archived_domain(addresses):
                do_archive = True
    else:
        logger.debug('No Message-ID, skipping archiving')
        return None

    if do_archive:
        conn = redis.StrictRedis.from_url(Configuration.REDIS_URL)
        queue = FIFOQueue('email-archive', conn)
        archive_date = message['Date']
        if archive_date is not None:
            archive_date = email.utils.parsedate(archive_date)
            archive_date = datetime.datetime(*archive_date[:6])
        else:
            archive_date = datetime.datetime.now()

        minute = int(archive_date.strftime('%M'))
        minute = minute - (minute % 10)
        archive_path = os.path.join(ARCHIVE_DIR,
                                    archive_date.strftime('%Y'),
                                    archive_date.strftime('%m'),
                                    archive_date.strftime('%d'),
                                    '{}{}'.format(archive_date.strftime('%H'), str(minute).zfill(2)))
        try:
            os.makedirs(archive_path)
        except OSError as e:
            # Ignore EEXIST
            if e.errno != 17:
                raise Exception('Unable to create directories')

        messagetime = archive_date.strftime('%H%M')
        hash_id = str(uuid.uuid4())
        archive_path = os.path.join(archive_path, messagetime + '-' + hash_id + '.eml.gz')
        logger.debug('Archiving to {}'.format(archive_path))
        with gzip_open(archive_path, 'wb') as fd:
            fd.write(str(message))

        queue.push(archive_path.replace(ARCHIVE_DIR, '').lstrip('/'))

        return archive_path


def main():
    """Process a message coming from stdin. Postfix delivery will send it this way"""
    str_message = sys.stdin.read()
    parser = email.parser.HeaderParser()
    message = parser.parsestr(str_message)
    archive_message(message)


if __name__ == '__main__':
    main()
