#!/usr/bin/env python
import os
import sys
import time
import logging
from email.parser import Parser

import redis

from .config import Configuration
from .fifo import FIFOQueue
from . import indexer
from . import message_utils


logger = logging.getLogger(__name__)

SLEEP_INTERVAL = 0.5
RECONNECT_INTERVAL = 5.0
POP_TIMEOUT = 5


_pool = None
def configure_pool():
    """Configure a redis ConnectionPool"""
    global _pool
    _pool = redis.ConnectionPool.from_url(Configuration.REDIS['url'])


def connect():
    return redis.StrictRedis(connection_pool=_pool)


def run(priorities=None):
    configure_pool()
    try:
        loop(priorities=priorities)
    except KeyboardInterrupt:
        print('\nExiting by user request.\n')
        sys.exit(0)


def loop(priorities=None):
    message_parser = Parser()
    archive_root = Configuration.ARCHIVE_DIR
    idx = indexer.Indexer()
    conn = None
    queue = None
    while True:
        try:
            if not conn:
                conn = connect()
                queue = FIFOQueue(Configuration.REDIS['queue'], conn, priorities=priorities)
                continue  # loop again

            item = queue.pop(timeout=POP_TIMEOUT)
            if not item:
                # Timeout occurred, loop again
                time.sleep(SLEEP_INTERVAL)
                continue

            # Comes from redis as binary
            item = item.decode('utf8')

            # Fetched item is a path relative to Configuration.ARCHIVE_DIR
            file_path = os.path.join(Configuration.ARCHIVE_DIR, item)
            message_path = file_path.replace(Configuration.ARCHIVE_DIR, '').lstrip('/')  # Just in case the item spec changes

            fd = None
            try:
                fd = message_utils.gz_open(file_path)
                message = message_parser.parsestr(fd.read().decode('utf8'))
                idx.process_message(message_path, message)
            except Exception as e:
                logger.exception('Unhandled exception processing {}'.format(file_path))
                continue
            finally:
                if fd:
                    fd.close()

            continue  # loop again without wait
        except redis.RedisError as e:
            conn = queue = None
            logger.exception('RedisError', e)
            time.sleep(RECONNECT_INTERVAL)
            continue

