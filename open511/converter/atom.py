import datetime
import re
from urlparse import urljoin

from lxml import etree
from lxml.builder import ElementMaker

NS_ATOM = "http://www.w3.org/2005/Atom"
NS_XHTML = 'http://www.w3.org/1999/xhtml'
NS_GEORSS = 'http://www.georss.org/georss'
NS_GML = 'http://www.opengis.net/gml'
XML_LANG = '{http://www.w3.org/XML/1998/namespace}lang'

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

def convert_to_atom(input, feed_url="http://example.org/open511-feed", feed_title="Open511 Example Feed"):

    A = ElementMaker(namespace=NS_ATOM, nsmap={None: NS_ATOM, 'html': NS_XHTML, 'georss': NS_GEORSS})
    feed = A('feed',
        A('id', feed_url),
        A('link', href=feed_url, rel='self'),
        A('title', feed_title, type='text'),
        A('updated', datetime.datetime.utcnow().isoformat() + 'Z')
    )

    base_url = input.get('{http://www.w3.org/XML/1998/namespace}base', feed_url)

    for event in input.xpath('events/event'):
        entry = A('entry',
            A('id', urljoin(base_url, event.xpath('link[@rel="self"]/@href')[0])),
            A('category', label='Status', scheme='masas:category:status', 
                term='Actual' if event.findtext('status') == 'ACTIVE' else 'Draft'),
            A('category', label='Severity', scheme='masas:category:severity',
                term=_cap_severity(event.findtext('severity'))),
            A('category', label='Category', scheme='masas:category:category',
                term=_cap_category(event.findtext('event_type'))),
            A('category', label='Open511 ID', scheme='open511:event:id',
                term=event.findtext('id'))
        )

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