import os


PKG_DIR = os.path.join(os.path.realpath(os.path.dirname(__file__)))

DATA_DIR = os.path.realpath(os.path.join(PKG_DIR, '..'))
INDEX_DIR = os.path.join(DATA_DIR, '_index')
DOCUMENTS_DIR = os.path.join(DATA_DIR, 'documents')
