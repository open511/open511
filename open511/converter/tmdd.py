import itertools
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

        for geo_xp in [
                'location-on-link/primary-location/geo-location',
                'location-on-link/secondary-location/geo-location',
                'geo-location']:
            for loc in location.xpath(geo_xp):
                c.add_geo(loc)

        if location.xpath('location-on-link/secondary-location'):
            secondary_road_name = _xpath_or_none(location, 'location-on-link/secondary-location/link-name/text()')
            if secondary_road_name and secondary_road_name != road['name']:
                secondary_road = dict(name=secondary_road_name)
                secondary_road_from = _xpath_or_none(location, 'location-on-link/secondary-location/cross-street-name/cross-street-name-item/text()')
                if secondary_road_from:
                    secondary_road['from'] = secondary_road_from
                roads.append(secondary_road)
            else:
                road_to = _xpath_or_none(location, 'location-on-link/secondary-location/cross-street-name/cross-street-name-item/text()')
                if road_to:
                    road['to'] = road_to

        direction = _xpath_or_none(location, 'location-on-link/link-direction/text()')
        if direction:
            direction = direction.upper()
            if direction in ('N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'):
                road['direction'] = direction
            elif direction.startswith('NOT'):
                road['direction'] = 'NONE'
            elif direction.startswith('BOTH'):
                road['direction'] = 'BOTH'
            else:
                logger.warning("Unrecognized direction %s" % direction)

        # FIXME lanes

        roads.append(road)
    return roads

def _get_geometry(c):
    if not c.points:
        return None
    if len(c.points) == 1:
        return {
            "type": "Point",
            "coordinates": list(c.points)[0]
        }
    return {
        "type": "MultiPoint",
        "coordinates": list(c.points)
    }

convert_severity = {
    'none': 1,
    'minor': 1,
    'major': 3,
    'natural-disaster': 3,
    'other': 0
}
convert_impact = {
    '0': 0, '1': 1, '2': 1, '3': 1, '4': 2, '5': 2, '6': 2, '7': 2, '8': 3, '9': 3, '10': 3
}
def _get_severity(c):
    """
    1. Collect all <severity> and <impact-level> values.
    2. Convert impact-level of 1-3 to MINOR, 4-7 to MODERATE, 8-10 to MAJOR
    3. Map severity -> none to MINOR, natural-disaster to MAJOR, other to UNKNOWN
    4. Pick the highest severity.
    """
    severities = c.feu.xpath('event-indicators/event-indicator/event-severity/text()|event-indicators/event-indicator/severity/text()')
    impacts = c.feu.xpath('event-indicators/event-indicator/event-impact/text()|event-indicators/event-indicator/impact/text()')

    severities = [convert_severity[s] for s in severities]
    impacts = [convert_impact[i] for i in impacts]

    return ['UNKNOWN', 'MINOR', 'MODERATE', 'MAJOR'][max(itertools.chain(severities, impacts))]


_OPEN511_FIELDS = [
    ('id', _get_id),
    ('self_url', lambda c: c.base_url + c.data['id']),
    ('jurisdiction_url', lambda c: c.jurisdiction_url),
    ('status', _get_status),
    ('updated', _get_updated),
    ('headline', _get_headline),
    ('description', _get_description),
    ('roads', _get_roads),
    ('geometry', _get_geometry),
    ('severity', _get_severity),
]

class TMDDEventConverter(object):

    jurisdiction_url = 'http://fake-jurisdiction'
    jurisdiction_id = 'fake.jurisdiction'
    base_url = 'http://fake-jurisdiction/events/'

    def __init__(self, feu, detail, id_suffix=None):
        self.feu = feu
        self.detail = detail
        self.id_suffix = id_suffix
        self.points = set()

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

    def add_geo(self, geo_location):
        """
        Saves a <geo-location> Element, to be incoporated into the Open511
        geometry field.
        """
        if not geo_location.xpath('latitude') and geo_location.xpath('longitude'):
            raise Exception("Invalid geo-location %s" % etree.tostring(geo_location))
        if _xpath_or_none(geo_location, 'horizontal-datum/text()') not in ('wgs84', None):
            logger.warning("Unsupported horizontal-datum in %s" % etree.tostring(geo_location))
            return
        point = (
            float(_xpath_or_none(geo_location, 'longitude/text()')) / 1000000,
            float(_xpath_or_none(geo_location, 'latitude/text()')) / 1000000
        )
        self.points.add(point)
