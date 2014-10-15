import datetime
import re
try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin

from lxml import etree
from lxml.builder import ElementMaker
import pytz

from open511.utils.schedule import Schedule
from open511.utils.serialization import NS_ATOM, NS_AGE, NS_XHTML, NS_GEORSS, NS_GML, XML_LANG, XML_BASE
from open511.utils.timezone import now

MASAS_EFFECTIVE = '{masas:experimental:time}effective'

def _get_lang(tag):
    if tag is None:
        return None
    lang = tag.get(XML_LANG)
    return lang if lang else _get_lang(tag.getparent())

def _el_to_html(source_el):
    div = etree.Element('{%s}div' % NS_XHTML)
    lang = _get_lang(source_el)
    for graf in re.split(r'\n+', source_el.text):
        p = etree.Element('{%s}div' % NS_XHTML)
        p.set(XML_LANG, lang)
        p.text = graf
        div.append(p)
    return div

def convert_to_atom(input, feed_url="http://example.org/open511-feed", feed_title="Open511 Example Feed",
        include_expires=False, default_timezone_name='UTC'):

    A = ElementMaker(namespace=NS_ATOM, nsmap={None: NS_ATOM, 'html': NS_XHTML, 'georss': NS_GEORSS})
    feed = A('feed',
        A('id', feed_url),
        A('link', href=feed_url, rel='self'),
        A('title', feed_title, type='text'),
        A('updated', datetime.datetime.utcnow().isoformat() + 'Z')
    )

    base_url = input.get(XML_BASE, feed_url)

    for event in input.xpath('events/event'):
        entry = A('entry',
            A('id', urljoin(base_url, event.xpath('link[@rel="self"]/@href')[0]))
        )
        active = event.findtext('status') == 'ACTIVE'

        if include_expires:
            tz = event.findtext('timezone')
            tz = pytz.timezone(tz) if tz else pytz.timezone(default_timezone_name)
            schedule = Schedule.from_element(event.find('schedules'), tz)
            timestamp = now()
            next_period = schedule.next_interval(timestamp)
            if next_period is None:
                active = False
            else:
                if next_period.start > timestamp:
                    # Add effective tag for future events
                    effective = etree.Element(MASAS_EFFECTIVE)
                    effective.text = next_period.start.isoformat()
                    entry.append(effective)
                if next_period.end - timestamp < datetime.timedelta(days=14):
                    expires = etree.Element('{%s}expires' % NS_AGE)
                    expires.text = next_period.end.isoformat()
                    entry.append(expires)


        entry.extend([
            A('category', label='Status', scheme='masas:category:status', 
                term='Actual' if active else 'Draft'),
            A('category', label='Severity', scheme='masas:category:severity',
                term=_cap_severity(event.findtext('severity'))),
            A('category', label='Category', scheme='masas:category:category',
                term=_cap_category(event.findtext('event_type'))),
            A('category', label='Open511 ID', scheme='open511:event:id',
                term=event.findtext('id'))
        ])

        if event.xpath('certainty'):
            entry.append(A('category', label='Certainty', scheme='masas:category:certainty',
                term=event.findtext('certainty').title()))
        
        title = A('title', type='xhtml')
        for headline in event.xpath('headline'):
            title.append(_el_to_html(headline))
        entry.append(title)

        if event.xpath('description'):
            content = A('content', type='xhtml')
            for description in event.xpath('description'):
                # FIXME HTML conversion?
                content.append(_el_to_html(description))
            entry.append(content)

        entry.append(_gml_to_georss(event.xpath('geography')[0][0]))

        feed.append(entry)

    return feed

def _gml_to_georss(gml):
    gml_name = gml.tag.partition('}')[2]
    name = '{%s}' % NS_GEORSS
    if gml_name == 'Point':
        name += 'point'
        coords = gml.findtext('{%s}pos' % NS_GML)
    elif gml_name == 'LineString':
        name += 'line'
        coords = gml.findtext('{%s}posList' % NS_GML)
    else:
        # TODO split multi geometries
        raise NotImplementedError("Cannot convert %s to GeoRSS" % gml_name)
    el = etree.Element(name)
    el.text = coords
    return el

def _cap_severity(sev):
    return 'Severe' if sev == 'MAJOR' else sev.title()

def _cap_category(evtype):
    return 'Met' if evtype == 'WEATHER_CONDITION' else 'Transport'