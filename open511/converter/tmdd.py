import itertools
import logging
import os

from lxml import etree

logger = logging.getLogger(__name__)

def tmdd_to_json(doc):
    converters = TMDDEventConverter.list_from_document(doc)
    events = [converter.to_json() for converter in converters]
    return {
        "meta": dict(version='v1'),
        "events": events
    }

def _xpath_or_none(el, query):
    result = el.xpath(query)
    return result[0] if result else None

def _tmdd_datetime_to_iso(dt, include_offset=True, include_seconds=True):
    """
    dt is an xml Element with <date>, <time>, and optionally <offset> children.
    returns an ISO8601 string
    """
    datestring = dt.findtext('date')
    timestring = dt.findtext('time')
    assert len(datestring) == 8
    assert len(timestring) >= 6
    iso = datestring[0:4] + '-' + datestring[4:6] + '-' + datestring[6:8] + 'T' \
        + timestring[0:2] + ':' + timestring[2:4]
    if include_seconds:
        iso += ':' + timestring[4:6]
    if include_offset:
        offset = dt.findtext('offset')
        if offset:
            assert len(offset) == 5
            iso += offset[0:3] + ':' + offset[3:5]
        else:
            raise Exception("TMDD date is not timezone-aware: %s" % etree.tostring(dt))
    return iso

def _get_status(c):
    """Returns ACTIVE or ARCHIVED, the Open511 <status> field."""
    # FIXME incomplete
    active_flag = _xpath_or_none(c.feu, 'event-indicators/event-indicator/active-flag/text()')
    return 'ARCHIVED' if active_flag in ('no', '2') else 'ACTIVE'

def _get_id(c):
    id = c.source_id = c.feu.xpath('event-reference/event-id/text()')[0]
    if c.id_suffix:
        id += '-%s' % c.id_suffix
    return '/'.join((c.jurisdiction_id, id))

def _get_updated(c):
    return _tmdd_datetime_to_iso(c.feu.xpath('event-reference/update-time')[0])

def _get_headline(c):
    names = c.detail.xpath('event-name/text()')
    if names:
        return names[0]
    return _generate_automatic_headline(c)

def _generate_automatic_headline(c):
    """The only field that maps closely to Open511 <headline>, a required field, is optional
    in TMDD. So we sometimes need to generate our own."""
    # Start with the event type, e.g. "Incident"
    headline = c.data['event_type'].replace('_', ' ').title()
    if c.data['roads']:
        # Add the road name
        headline += ' on ' + c.data['roads'][0]['name']
        direction = c.data['roads'][0].get('direction')
        if direction and direction not in ('BOTH', 'NONE'):
            headline += ' ' + direction
    return headline

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
            direction = _convert_direction(direction)
            if direction:
                road['direction'] = direction

        roads.append(road)

    if len(roads) == 1:
        _update_road_with_lanes(c, roads[0])
    return roads

def _convert_direction(direction):
    direction = direction.upper()
    if direction in ('N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'):
        return direction
    elif direction.startswith('NOT'):
        return 'NONE'
    elif direction.startswith('BOTH'):
        return 'BOTH'
    else:
        logger.warning("Unrecognized direction %s" % direction)

def _update_road_with_lanes(c, road):
    lane_els = c.detail.xpath('event-lanes/event-lane[lane-status/text()]')
    if not lane_els:
        return

    directions = set()
    for lane_el in lane_els:
        for direction in lane_el.xpath('link-direction/text()'):
            directions.add(direction)
    if len(directions) > 1:
        return logger.warning("Multiple link-directions in lanes, cannot process")
    elif len(directions) == 0 and not road.get('direction'):
        return logger.warning("No direction provided, either in road or lane data")

    if len(directions) == 1 and road.get('direction'):
        # Make sure directions match
        direction = next(iter(directions)).upper()
        if not (direction == road.get('direction')
                or (road.get('direction') == 'BOTH' and direction.startswith('BOTH'))):
            return logger.warning("Road direction does not match lane direction %s" % direction)
    elif len(directions) == 1 and not road.get('direction'):
        road['direction'] = _convert_direction(direction)

    lanes_open = 0
    lanes_closed = 0

    for lane_el in lane_els:
        status = lane_el.findtext('lane-status').lower()

        if status.startswith('reduced-to'):
            if len(lane_els) > 1:
                return logger.warning("Cannot process lane status of %s with multiple event-lanes" % status)
            if status.startswith('reduced-to-one'):
                lanes_open = 1
            elif status.startswith('reduced-to-two'):
                lanes_open = 2
            elif status.startswith('reduce-to-three'):
                lanes_open = 3
            else:
                raise NotImplementedError
        else:
            lanes_affected = _xpath_or_none(lane_el, 'lanes-total-affected/text()')
            total_lanes = _xpath_or_none(lane_el, 'lanes-total-original/text()')
            if not lanes_affected and total_lanes:
                return logger.warning("Cannot process lane data without lanes-total-affected and lanes-total-original")
            lanes_affected = int(lanes_affected)
            total_lanes = int(total_lanes)
            assert total_lanes >= lanes_affected

            if status.starswith('closed') or status.startswith('blocked') or status == 'collapse' or status == 'out':
                lanes_closed += lanes_affected
                lanes_open += (total_lanes - lanes_affected)
            elif status.startswith('open') or status == 'cleared-from-road' or status.startswith('reopened'):
                lanes_open += lanes_affected
            else:
                return logger.warning("Unrecognize lane-status %s" % status)

            if lanes_closed == lanes_open == 0:
                return logger.warning("Couldn't find any affected lanes")

            if lanes_open >= lanes_closed:
                road['state'] = 'ALL_LANES_OPEN'
            elif lanes_open == 0:
                road['state'] = 'CLOSED'
            else:
                road['state'] = 'SOME_LANES_CLOSED'
                road['lanes_closed'] = lanes_closed
                road['lanes_open'] = lanes_open


def _get_geography(c):
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

def _get_event_type(c):
    planned_class = _xpath_or_none(c.feu, 'event-indicators/event-indicator/planned-event-class/text()')
    return {
        'incident': 'INCIDENT',
        'construction': 'CONSTRUCTION',
        'event': 'SPECIAL_EVENT',
        'other': 'SPECIAL_EVENT' # is this right?
    }.get(planned_class)

def _get_certainty(c):
    certainty = _xpath_or_none(c.detail, 'confidence-level/text()')
    if certainty is None:
        return None
    if certainty.isdigit():
        certainty = int(certainty)
    else:
        certainty = dict(zip(
                ('unconfirmed-report', 'two-unconfirmed-reports', 'three-unconfirmed-reports',
                'four-or-more-unconfirmed-reports', 'provisional-plan', 'firm-plan',
                'official-report-from-scene', 'detailed-official-report-from-scene',
                'detailed-official-reports-covering-whole-area', 'legally-enforced-decision'),
                range(1, 10)
            ))[certainty.lower()]
    if certainty == 1:
        return 'POSSIBLE'
    elif certainty <= 4:
        return 'LIKELY'
    else:
        return 'OBSERVED'

def _get_grouped(c):
    other_ids = set()
    if c.number_in_group > 1:
        for n in range(c.number_in_group):
            if n != c.id_suffix:
                other_ids.add(c.source_id + '-%s' % n)
    for reference_type in ['responsible-event', 'related-event', 'merged-event', 'sibling-event']:
        for other_id in c.feu.xpath('other-references/' + reference_type + '/event-id/text()'):
            other_ids.add(other_id)
    if not other_ids:
        return None
    return [
        c.base_url + c.jurisdiction_id + '/' + other_id
        for other_id in other_ids
    ]

def _get_event_subtypes(c):
    subtypes = set()
    for subtype in c.feu.xpath('event-headline/headline/accidents-and-incidents/text()'):
        if 'accident' in subtype:
            subtypes.add('ACCIDENT')
        if 'spill' in subtype:
            subtypes.add('SPILL')
    return list(subtypes)

def _get_schedule(c):
    start_time = (
        c.detail.xpath('event-times/start-time[date/text()]')
        or c.detail.xpath('event-times/expected-start-time[date/text()]')
        or c.detail.xpath('event-times/alternate-start-time[date/text()]')
        or c.detail.xpath('event-times/update-time[date/text()]')
        or c.feu.xpath('event-reference/update-time[date/text()]')
    )
    assert start_time
    start_time = _tmdd_datetime_to_iso(start_time[0], include_offset=False, include_seconds=False)

    end_time = (
        c.detail.xpath('event-times/expected-end-time[date/text()]')
        or c.detail.xpath('event-times/valid-period/expected-end-time[date/text()]')
        or c.detail.xpath('event-times/alternate-end-time[date/text()]')
    )
    end_time = _tmdd_datetime_to_iso(end_time[0], include_offset=False, include_seconds=False) if end_time else ''

    return {
        'intervals': [start_time + '/' + end_time]
    }

_OPEN511_FIELDS = [
    ('id', _get_id),
    ('url', lambda c: c.base_url + c.data['id']),
    ('jurisdiction_url', lambda c: c.jurisdiction_url),
    ('status', _get_status),
    ('updated', _get_updated),
    ('created', _get_updated), # We don't have a separate created timestamp
    ('description', _get_description),
    ('roads', _get_roads),
    ('geography', _get_geography),
    ('severity', _get_severity),
    ('event_type', _get_event_type),
    ('certainty', _get_certainty),
    ('grouped_events', _get_grouped),
    ('event_subtypes', _get_event_subtypes),
    ('schedule', _get_schedule),
    ('headline', _get_headline),
]

class TMDDEventConverter(object):

    jurisdiction_url = os.environ.get('OPEN511_JURISDICTION_URL', 'https://example.org/example-jurisdiction')
    jurisdiction_id = os.environ.get('OPEN511_JURISDICTION_ID', 'example.jurisdiction')
    base_url = os.environ.get('OPEN511_EVENTS_URL', 'https://example.org/events/')

    def __init__(self, feu, detail, id_suffix=None, number_in_group=1):
        self.feu = feu
        self.detail = detail
        self.id_suffix = id_suffix
        self.number_in_group = number_in_group
        self.points = set()

    @classmethod
    def list_from_document(cls, doc):
        """Returns a list of TMDDEventConverter elements.

        doc is an XML Element containing one or more <FEU> events
        """
        objs = []
        for feu in doc.xpath('//FEU'):
            detail_els = feu.xpath('event-element-details/event-element-detail')
            for idx, detail in enumerate(detail_els):
                objs.append(cls(feu, detail, id_suffix=idx, number_in_group=len(detail_els)))
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
