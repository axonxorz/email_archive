#!/usr/bin/env python
import os
import sys
import time
import logging
from gzip import open as gzip_open
from email.parser import Parser

import redis
from whoosh.writing import BufferedWriter

from .config import Configuration
from .fifo import FIFOQueue
from . import index


logger = logging.getLogger(__name__)

SLEEP_INTERVAL = 0.5
RECONNECT_INTERVAL = 5.0
POP_TIMEOUT = 5


ix = None
writer = None

def configure_index():
    global ix, writer
    ix = index.get_index()
    writer = BufferedWriter(ix)

_pool = None
def configure_pool():
    """Configure a redis ConnectionPool"""
    global _pool
    _pool = redis.ConnectionPool.from_url(Configuration.REDIS_URL)


def connect():
    return redis.StrictRedis(connection_pool=_pool)


def main():
    configure_index()
    configure_pool()
    try:
        loop()
    except KeyboardInterrupt:
        print '\nExiting by user request.\n'
        if writer:
            writer.commit()
            writer.close()
        sys.exit(0)

def loop():
    message_parser = Parser()
    archive_root = Configuration.ARCHIVE_DIR
    conn = None
    queue = None
    while True:
        try:
            if not conn:
                conn = connect()
                queue = FIFOQueue('email-archive', conn)
                continue  # loop again

            item = queue.pop(timeout=POP_TIMEOUT)
            if not item:
                # Timeout occurred, loop again
                time.sleep(SLEEP_INTERVAL)
                continue

            # Fetched item is a path relative to Configuration.ARCHIVE_DIR
            file_path = os.path.join(Configuration.ARCHIVE_DIR, item)
            message_path = file_path.replace(Configuration.ARCHIVE_DIR, '').lstrip('/')  # Just in case the item spec changes
            print file_path
            print message_path

            fd = None
            try:
                if file_path.endswith('.gz'):
                    fd = gzip_open(file_path, 'rb')
                else:
                    fd = open(file_path, 'rb')
                message = message_parser.parse(fd)
                index.process_message(message_path, message, writer)
            except Exception, e:
                logger.exception('Unhandled exception processing {}'.format(file_path))
                continue
            finally:
                if fd:
                    fd.close()

            continue  # loop again without wait
        except redis.RedisError, e:
            conn = queue = None
            logger.exception('RedisError', e)
            time.sleep(RECONNECT_INTERVAL)
            continue

