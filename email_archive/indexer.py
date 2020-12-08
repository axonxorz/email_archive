import hashlib
import logging
import quopri
from functools import wraps
import mimetypes

import magic
import chardet
import bleach
import elasticsearch
from elasticsearch.exceptions import NotFoundError

from .message_utils import (
    addr_tokenize,
    emaildate_to_arrow,
    email_get_body,
    email_attachment_details,
    safe_b64decode
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
        msg_subject = str(message.get('Subject', ''))
        msg_headers = ['{}: {}'.format(x, y) for x, y in message.items()]
        msg_date = emaildate_to_arrow(message['Date'])
        msg_from = addr_tokenize(message['From'])
        msg_cc = addr_tokenize(message.get('CC'))
        msg_bcc = addr_tokenize(message.get('BCC'))
        msg_to = addr_tokenize(message['To'])
        msg_attachments = email_attachment_details(message)

        has_valid_body = False
        msg_body = email_get_body(message)
        if msg_body is not None:
            content_type = msg_body.get('Content-Type', 'application/octet-stream')
            if content_type.startswith('text/'):
                encoding = msg_body.get('Content-Transfer-Encoding')
                charset = msg_body.get_param('charset')
                if encoding == 'quoted-printable':
                    try:
                        body_text = quopri.decodestring(msg_body.get_payload())
                    except ValueError as e:
                        # Likely non-ascii characters encountered in msg_body.get_payload(), try again by
                        # stripping them out
                        body_text = quopri.decodestring(msg_body.get_payload().encode('utf8', 'ignore'))
                elif encoding == 'base64':
                    body_text = safe_b64decode(msg_body.get_payload())
                else:
                    body_text = msg_body.get_payload()

                # Certain charsets are provided in a non-"python codecs module"-compliant form. (cp850 can come in
                # as cp-850, CP-850, Cp-850. Attempt to normalize. This is not tested with all charsets, just
                # the ones we've often encountered
                if charset is not None and 'cp' in charset.lower() and '-' in charset:
                    charset = charset.replace('-', '').lower()

                # Attempt to determine charset with chardet
                if not isinstance(body_text, str) and charset is None:
                    charset = chardet.detect(body_text)['encoding']

                # Explicitly handle unresolvable charsets
                charset_maps = {
                    'WE8ISO8859P1': 'iso8859-1'  # Oracle
                }
                if charset in charset_maps:
                    charset = charset_maps[charset]

                if isinstance(body_text, bytes):
                    try:
                        body_text = body_text.decode(charset and charset or 'utf8')
                    except UnicodeDecodeError as e:
                        # Try to see if this _might_ not be a "text/*" message part
                        magic_mime = magic.from_buffer(body_text[:4096], mime=True)
                        if magic_mime is not None:
                            maybe_filename = msg_body.get_filename()
                            if not maybe_filename:
                                maybe_filename = 'body{}'.format(mimetypes.guess_extension(magic_mime) or '.bin')
                            msg_attachments.append((maybe_filename, magic_mime))
                            body_text = ''
                            logger.warning('Message body was not text/*, instead detected as {}, indexing as attachment "{}"'.format(magic_mime, maybe_filename))
                        else:
                            logger.warning('Could not decode body_text as unicode: {}'.format(e))
                            logger.warning('Message likely has incorrect charset specified, falling back to safe conversion')
                            logger.warning('Context: {}'.format(body_text[e.start-20:e.end+20]))
                            logger.warning('         ' + '****'*4 + '   ^^^   ' + '****'*4)
                            body_text = body_text.decode(charset and charset or 'utf8', 'ignore')

                if 'text/html' in content_type:
                    body_text = bleach.clean(body_text, tags=[], attributes={}, styles=[], strip=True)
                has_valid_body = True

        if not has_valid_body:
            logger.warning('Could not index message body for {}, indexing envelope only'.format(message_id))
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
        document_id_parts = [str(message_id),
                             ';'.join(msg_from or 'None'),
                             ';'.join(msg_to or 'None'),
                             msg_subject]
        document_id_parts = ''.join(document_id_parts).encode('utf8')
        document_id = hashlib.sha256(document_id_parts).hexdigest()

        def _try_index():
            self.es.index(index=index_name,
                          id=document_id,
                          body=message_index_body)

        try:
            _try_index()
        except NotFoundError:
            self.create_message_index(index_name)
            _try_index()

        logger.info('Indexed {}'.format(message_id))
