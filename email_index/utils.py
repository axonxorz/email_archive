import email.utils

import arrow


def emaildate_to_arrow(date):
    return arrow.get(email.utils.mktime_tz(email.utils.parsedate_tz(date)))

