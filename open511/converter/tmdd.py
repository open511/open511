import logging

from lxml import etree

logger = logging.getLogger(__name__)

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

def _xpath_or_none(el, query):
    result = el.xpath(query)
    return result[0] if result else None

def _tmdd_datetime_to_iso(dt, require_offset=True):
    """
    dt is an xml Element with <date>, <time>, and optionally <offset> children.
    returns an ISO8601 string
    """
    datestring = dt.findtext('date')
    timestring = dt.findtext('time')
    assert len(datestring) == 8
    assert len(timestring) >= 6
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
    active_flag = _xpath_or_none(c.feu, 'event-indicators/event-indicator/active-flag/text()')
    return 'ARCHIVED' if active_flag in ('no', '2') else 'ACTIVE'

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

def _get_description(c):
    detail_descriptions = c.detail.xpath('event-descriptions/event-description/additional-text/description/text()')
    if detail_descriptions:
        return '\n\n'.join(detail_descriptions)
    overall_description = c.feu.xpath('full-report-texts/description/text()')
    if overall_description:
        return overall_description[0]

def _get_roads(c):
    roads = []
    for location in c.detail.xpath('event-locations/event-location'):
        main_name = _xpath_or_none(location, 'location-on-link/link-name/text()')
        primary_name = _xpath_or_none(location, 'location-on-link/primary-location/link-name/text()')
        if not (main_name or primary_name):
            logger.warning("No name for link in %s" % etree.tostring(location))
            continue
        road = dict(name=primary_name or main_name)

        road_from = (
            _xpath_or_none(location, 'location-on-link/primary-location/cross-street-name/cross-street-name-item/text()')
            or
            _xpath_or_none(location, 'location-on-link/primary-location/linear-reference/text()')
        )
        if road_from:
            road['from'] = road_from

        if location.xpath('location-on-link/secondary-location'):
            secondary_road_name = _xpath_or_none(location, 'location-on-link/secondary-location/link-name/text()')
            if secondary_road_name and secondary_road_name != road['name']:
                # FIXME add a new road
                pass
            else:
                road_to = _xpath_or_none(location, 'location-on-link/secondary-location/cross-street-name/cross-street-name-item/text()')
                if road_to:
                    road['to'] = road_to

        direction = _xpath_or_none(location, 'location-on-link/link-direction/text()')
        if direction:
            road['direction'] = direction.upper() # FIXME validate

        # FIXME lanes

        roads.append(road)
    return roads


_OPEN511_FIELDS = [
    ('id', _get_id),
    ('self_url', lambda c: c.base_url + c.data['id']),
    ('jurisdiction_url', lambda c: c.jurisdiction_url),
    ('status', _get_status),
    ('updated', _get_updated),
    ('headline', _get_headline),
    ('description', _get_description),
    ('roads', _get_roads),
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
            val = func(self)
            if val:
                self.data[field_name] = val

        return self.data
