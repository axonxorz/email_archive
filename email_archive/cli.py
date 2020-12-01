import os
import sys
import email
import email.utils
import email.parser

import click

from . import archive
from . import indexer
from . import index_daemon as daemon_module
from .config import Configuration


@click.group()
def main():
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


def update_index():
    """Update the index or a subtree of the index in the current process"""
    try:
        subtree = sys.argv[1]
    except IndexError:
        subtree = None

    if subtree is not None:
        # Check that the subtree is actually contained within the index path
        archive_dir = Configuration.ARCHIVE_DIR
        subtree_real = os.path.realpath(os.path.join(os.getcwd(), subtree))
        if not subtree_real.startswith(archive_dir):
            print('Path {} is not within archive: {}'.format(subtree_real, archive_dir))
            sys.exit(1)
        print(subtree_real)

    index.update_index(subtree=subtree)


if __name__ == '__main__':
    main()