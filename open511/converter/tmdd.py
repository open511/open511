from lxml import etree

def is_tmdd(doc):
    # Does a given etree Element represent a TMDD document?
    return bool(doc.xpath('//FEU'))

def tmdd_to_json(doc):
    converters = TMDDEventConverter.list_from_document(doc)
    events = [converter.to_json() for converter in converters]
    return {
        "meta": dict(version='v0'),
        "events": events
    }

def _tmdd_datetime_to_iso(dt, require_offset=True):
    """
    dt is an xml Element with <date>, <time>, and optionally <offset> children.
    returns an ISO8601 string
    """
    datestring = dt.findtext('date')
    timestring = dt.findtext('time')
    assert len(datestring) == 8
    assert len(timestring) == 6
    iso = datestring[0:4] + '-' + datestring[4:6] + '-' + datestring[6:8] + 'T' \
        + timestring[0:2] + ':' + timestring[2:4] + ':' + timestring[4:6]
    offset = dt.findtext('offset')
    if offset:
        assert len(offset) == 5
        iso += offset[0:3] + ':' + offset[3:5]
    elif require_offset:
        raise Exception("TMDD date is not timezone-aware: %s" % etree.tostring(dt))
    return iso

def _get_status(c):
    """Returns ACTIVE or ARCHIVED, the Open511 <status> field."""
    # FIXME incomplete
    active_flag = c.feu.xpath('event-indicators/event-indicator/active-flag/text()')[0]
    return 'ACTIVE' if active_flag == 'yes' else 'ARCHIVED'

def _get_id(c):
    source_id = c.feu.xpath('event-reference/event-id/text()')[0]
    if c.id_suffix:
        source_id += '-%s' % c.id_suffix
    return '/'.join((c.jurisdiction_id, source_id))

def _get_updated(c):
    return _tmdd_datetime_to_iso(c.feu.xpath('event-reference/update-time')[0])

def _get_headline(c):
    names = c.detail.xpath('event-name/text()')
    if names:
        return names[0]
    return "NO HEADLINE"

_OPEN511_FIELDS = [
    ('id', _get_id),
    ('self_url', lambda c: c.base_url + c.data['id']),
    ('jurisdiction_url', lambda c: c.jurisdiction_url),
    ('status', _get_status),
    ('updated', _get_updated),
    ('headline', _get_headline)
]

class TMDDEventConverter(object):

    jurisdiction_url = 'http://fake-jurisdiction'
    jurisdiction_id = 'fake.jurisdiction'
    base_url = 'http://fake-jurisdiction/events/'

    def __init__(self, feu, detail, id_suffix=None):
        self.feu = feu
        self.detail = detail
        self.id_suffix = id_suffix

    @classmethod
    def list_from_document(cls, doc):
        """Returns a list of TMDDEventConverter elements.

        doc is an XML Element containing one or more <FEU> events
        """
        objs = []
        for feu in doc.xpath('//FEU'):
            for idx, detail in enumerate(feu.xpath('event-element-details/event-element-detail')):
                objs.append(cls(feu, detail, id_suffix=idx))
        return objs

    def to_json(self):
        self.data = {}

        for field_name, func in _OPEN511_FIELDS:
            self.data[field_name] = func(self)

        return self.data
