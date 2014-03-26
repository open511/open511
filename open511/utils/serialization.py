import json

from lxml import etree

from open511.converter import geojson_to_gml


XML_LANG = '{http://www.w3.org/XML/1998/namespace}lang'
XML_BASE = '{http://www.w3.org/XML/1998/namespace}base'
GML_NS = NS_GML = 'http://www.opengis.net/gml'
NS_KML = 'http://www.opengis.net/kml/2.2'
NS_PROTECTED = 'http://open511.org/namespaces/internal-field'
NS_ATOM = "http://www.w3.org/2005/Atom"
NS_XHTML = 'http://www.w3.org/1999/xhtml'
NS_GEORSS = 'http://www.georss.org/georss'

NSMAP = {
    'gml': NS_GML,
    'protected': NS_PROTECTED
}

def geom_to_xml_element(geom):
    """Transform a GEOS or OGR geometry object into an lxml Element
    for the GML geometry."""
    if geom.srs.srid != 4326:
        raise NotImplementedError("Only WGS 84 lat/long geometries (SRID 4326) are supported.")
    # GeoJSON output is far more standard than GML, so go through that
    return geojson_to_gml(json.loads(geom.geojson))

def get_base_open511_element(lang=None, base=None, version=None):
    elem = etree.Element("open511", nsmap={
        'gml': NS_GML,
    })
    if lang:
        elem.set(XML_LANG, lang)
    if base:
        elem.set(XML_BASE, base)
    if version:
        elem.set('version', version)
    return elem

def make_link(rel, href):
    l = etree.Element('link')
    l.set('rel', rel)
    l.set('href', href)
    return l

def deserialize(s):
    s = s.strip()
    try:
        return (etree.fromstring(s), 'xml')
    except etree.XMLSyntaxError:
        try:
            return (json.loads(s), 'json')
        except ValueError:
            raise Exception("Doesn't look like either JSON or XML")

def serialize(obj):
    if getattr(obj, 'tag', None) == 'open511':
        return etree.tostring(obj, pretty_print=True)
    return json.dumps(obj, indent=4)    