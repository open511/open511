# Taken from django.utils.timezone

def is_aware(value):
    """
    Determines if a given datetime.datetime is aware.

    The logic is described in Python's docs:
    http://docs.python.org/library/datetime.html#datetime.tzinfo
    """
    return value.tzinfo is not None and value.tzinfo.utcoffset(value) is not None


def is_naive(value):
    """
    Determines if a given datetime.datetime is naive.

    The logic is described in Python's docs:
    http://docs.python.org/library/datetime.html#datetime.tzinfo
    """
    return value.tzinfo is None or value.tzinfo.utcoffset(value) is None


def make_aware(value, timezone):
    """
    Makes a naive datetime.datetime in a given time zone aware.
    """
    if hasattr(timezone, 'localize'):
        # available for pytz time zones
        return timezone.localize(value, is_dst=None)
    else:
        # may be wrong around DST changes
        return value.replace(tzinfo=timezone)


def make_naive(value, timezone):
    """
    Makes an aware datetime.datetime naive in a given time zone.
    """
    value = value.astimezone(timezone)
    if hasattr(timezone, 'normalize'):
        # available for pytz time zones
        value = timezone.normalize(value)
    return value.replace(tzinfo=None)