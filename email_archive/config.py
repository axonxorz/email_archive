import os


PKG_DIR = os.path.join(os.path.realpath(os.path.dirname(__file__)))

DATA_DIR = os.path.realpath(os.path.join(PKG_DIR, '..'))

ARCHIVE_DIR = os.path.join(DATA_DIR, '_archive')
INDEX_DIR = os.path.join(DATA_DIR, '_index')
DOCUMENTS_DIR = os.path.join(DATA_DIR, 'documents')
