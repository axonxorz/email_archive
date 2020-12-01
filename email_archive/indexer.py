import logging
import base64
import quopri
from functools import wraps

import bleach
import elasticsearch
from elasticsearch.exceptions import NotFoundError

from .message_utils import (
    addr_tokenize,
    emaildate_to_arrow,
    email_get_body,
    email_attachment_details
)
from .config import Configuration


logger = logging.getLogger(__name__)


class Indexer:

    es = None

    def connect(self):
        config = Configuration.ELASTIC
        elasticsearch.Elasticsearch()
        logger.info('Connecting to ES host {}'.format(config['hosts']))
        if config.get('verify_certs') is False:
            import urllib3
            urllib3.disable_warnings()
        self.es = elasticsearch.Elasticsearch(**config)

    def _ensure_connection(method):
        @wraps(method)
        def wrapper(self, *args, **kwargs):
            if self.es is None:
                self.connect()
            return method(self, *args, **kwargs)
        return wrapper

    @staticmethod
    def get_index_name(msg_date):
        """
        Return our ES index name baed on `msg_date`
        """
        return 'email-message-index-{}'.format(msg_date.format('YYYYMM'))

    @_ensure_connection
    def create_message_index(self, index_name):
        """
        Create an Email messagestore index at `index_name
        """
        def _email_addr_multifield():
            return {"type": "text",
                    "analyzer": "email_address",
                    "fields": {"keyword": {"type": "keyword"}}}

        def _text_multifield():
            return {"type": "text",
                    "fields": {"keyword": {"type": "keyword"}}}

        index_body = {
            "settings": {
                "analysis": {
                    "analyzer": {
                        "email_address": {
                            "tokenizer": "uax_url_email",
                            "filter": ["email", "lowercase", "unique"]
                        },
                        "email_body": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "stop"],
                            "char_filter": "html_strip"
                        }
                    },
                    "filter": {
                        "email": {
                            "type": "pattern_capture",
                            "preserve_original": True,
                            "patterns": [
                                "([^@]+)",
                                "(\\p{L}+)",
                                "(\\d+)",
                                "@(.+)",
                                "([^-@]+)"
                            ]
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "message_id": {"type": "keyword"},
                    "path": {"type": "keyword", "index": False},
                    "headers": {"type": "text", "index": False},
                    "from_addr": _email_addr_multifield(),
                    "to_addr": _email_addr_multifield(),
                    "cc_addr": _email_addr_multifield(),
                    "bcc_addr": _email_addr_multifield(),
                    "attachments": _text_multifield(),
                    "subject": _text_multifield(),
                    "body": {"type": "text", "analyzer": "email_body"}
                }
            }
        }
        self.es.indices.create(index_name, body=index_body)

    @_ensure_connection
    def process_message(self, message_path, message):
        """
        Process a single email.Message object into the index. Message path is expected to be the relative path
        from the root of the on-disk message storage.
        """
        message_id = message['Message-Id']
        if message_id is None:
            logger.warn('Skipping {}, could not find a Message-Id, probably an error parsing'.format(message_path))
            return False
        msg_subject = message.get('Subject', '')
        msg_headers = ['{}: {}'.format(x, y) for x, y in message.items()]
        msg_date = emaildate_to_arrow(message['Date'])
        msg_from = addr_tokenize(message['From'])
        msg_cc = addr_tokenize(message.get('CC'))
        msg_bcc = addr_tokenize(message.get('BCC'))
        msg_to = addr_tokenize(message['To'])
        msg_attachments = email_attachment_details(message)

        msg_body = email_get_body(message)
        if msg_body is not None:
            encoding = msg_body.get('Content-Transfer-Encoding')
            charset = msg_body.get_param('charset')
            if encoding == 'quoted-printable':
                body_text = quopri.decodestring(msg_body.get_payload())
            elif encoding == 'base64':
                body_text = base64.b64decode(msg_body.get_payload())
            else:
                body_text = msg_body.get_payload()

            if isinstance(body_text, bytes):
                try:
                    body_text = body_text.decode(charset and charset or 'utf8')
                except UnicodeDecodeError as e:
                    logger.warning('Could not encode body_text as unicode: {}'.format(e))
                    logger.warning('Message likely has incorrect charset specified, falling back to safe conversion')
                    logger.warning('Context: {}'.format(body_text[e.start-20:e.end+20]))
                    logger.warning('         ' + '****'*4 + '   ^^^   ' + '****'*4)
                    body_text = body_text.decode(charset, 'ignore')

            if 'text/html' in msg_body.get('Content-Type', 'application/octet-stream'):
                body_text = bleach.clean(body_text, tags=[], attributes={}, styles=[], strip=True)

        else:
            logger.warning('Could not find body for {}, indexing message envelope only'.format(message_id))
            body_text = None

        message_index_body = dict(message_id=message_id,
                                  path=message_path,
                                  headers=msg_headers,
                                  from_addr=msg_from,
                                  to_addr=msg_to,
                                  cc_addr=msg_cc,
                                  bcc_addr=msg_bcc,
                                  attachments=msg_attachments,
                                  subject=msg_subject,
                                  body=body_text)
        message_index_body['@timestamp'] = msg_date.naive

        index_name = self.get_index_name(msg_date)

        def _try_index():
            self.es.index(index=index_name,
                          id=message_id,
                          body=message_index_body)

        try:
            _try_index()
        except NotFoundError:
            self.create_message_index(index_name)
            _try_index()

        logger.info('Indexed {}'.format(message_id))
