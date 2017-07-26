import email.utils

import bleach
from whoosh.analysis import RegexTokenizer, LowercaseFilter
from whoosh.analysis.tokenizers import default_pattern


def clean_str(value):
    return value.strip('\'"').strip()


def flatten_addrs(addrs):
    tokens = []
    for addr in addrs:
        for token in addr:
            if '@' in token:
                tokens.extend([clean_str(x) for x in token.split('@')])
            else:
                tokens.append(clean_str(token))
    return ' '.join(tokens).strip()


def EmailAddressAnalyzer():
    return EmailAddressTokenizer() | LowercaseFilter()


class EmailAddressTokenizer(RegexTokenizer):
    """Splits email address lists from raw email headers into individual tokens.
    Names are split, as well as address/domain combinations"""

    email_default_pattern = r"[^ \t\r\n]+"

    def __init__(self, pattern=email_default_pattern, gaps=False):
        super(EmailAddressTokenizer, self).__init__(pattern, gaps=gaps)

    def __call__(self, addresses, **kwargs):
        addresses = addresses.split(',')
        addresses = [email.utils.parseaddr(x.strip()) for x in addresses]
        addresses = [x for x in addresses if x != ('', '')]
        addresses = flatten_addrs(addresses)
        return super(EmailAddressTokenizer, self).__call__(addresses, positions=True)

