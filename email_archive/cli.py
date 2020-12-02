import os
import sys
import email
import email.utils
import email.parser
import logging
from pathlib import Path

import click
import redis

from . import archive
from . import index_daemon as daemon_module
from .fifo import FIFOQueue
from .config import Configuration


logger = logging.getLogger(__name__)


@click.group()
def main():
    logging.basicConfig(level=logging.DEBUG)
    pass


@main.command()
@click.option('--path', required=False)
def archive_message(path=None):
    if path is None:
        str_message = sys.stdin.read()
    else:
        with open(path) as fd:
            str_message = fd.read()

    parser = email.parser.HeaderParser()
    message = parser.parsestr(str_message)
    archive.archive_message(message)


@main.command()
def index_daemon():
    daemon_module.run()


@main.command()
@click.argument('path')
def bulk_index(path):
    """Update the index or a subtree of the index in bulk"""
    # Check that the subtree is actually contained within the index path
    archive_dir = Path(Configuration.ARCHIVE_DIR)
    path = Path(path).absolute()
    try:
        path.relative_to(archive_dir)
    except ValueError:
        logger.warning('Specified path {} is not within archive: {}'.format(path, archive_dir))
        sys.exit(1)

    conn = redis.StrictRedis.from_url(Configuration.REDIS.get('url'))
    queue = FIFOQueue(Configuration.REDIS['queue'], conn)

    for root, dirs, files in os.walk(path):
        for filename in files:
            full_file_path = Path(root) / Path(filename)
            path_to_index = str(full_file_path).replace(str(archive_dir), '').lstrip('/')
            queue.push(path_to_index, priority=3)
            logger.info('Queueing indexing of {}'.format(full_file_path))


if __name__ == '__main__':
    main()