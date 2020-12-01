from whoosh.fields import *
from whoosh.analysis import StemmingAnalyzer

from .analyzers import EmailAddressAnalyzer


email_schema = Schema(message_id=ID(stored=True, unique=True),
                      path=ID(stored=True, unique=True),
                      from_addr=KEYWORD(stored=True, analyzer=EmailAddressAnalyzer()),
                      to_addr=KEYWORD(stored=True, analyzer=EmailAddressAnalyzer()),
                      has_attachments=ID(stored=True),
                      date=DATETIME(stored=True),
                      subject=TEXT(stored=True),
                      body=TEXT(analyzer=StemmingAnalyzer()))
