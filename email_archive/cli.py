import os
import sys

from . import index
from .config import Configuration


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
    pass
