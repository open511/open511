import json

from lxml import etree

XML_LANG = '{http://www.w3.org/XML/1998/namespace}lang'
XML_BASE = '{http://www.w3.org/XML/1998/namespace}base'
GML_NS = NS_GML = 'http://www.opengis.net/gml'
NS_KML = 'http://www.opengis.net/kml/2.2'
NS_PROTECTED = 'http://open511.org/namespaces/internal-field'
NS_ATOM = "http://www.w3.org/2005/Atom"
NS_AGE = "http://purl.org/atompub/age/1.0"
NS_XHTML = 'http://www.w3.org/1999/xhtml'
NS_GEORSS = 'http://www.georss.org/georss'

NSMAP = {
    'gml': NS_GML,
    'protected': NS_PROTECTED,
    'kml': NS_KML,
    'atom': NS_ATOM,
    'age': NS_AGE,
    'html': NS_XHTML,
    'georss': NS_GEORSS
}

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

def is_tmdd(doc):
    # Does a given etree Element represent a TMDD document?
    return doc.tag != 'open511' and bool(doc.xpath('//FEU'))

def deserialize(s):
    s = s.strip()
    try:
        doc = etree.fromstring(s)
        if is_tmdd(doc):
            # Transparently convert the TMDD on deserialize
            from ..converter.tmdd import tmdd_to_json
            return (tmdd_to_json(doc), 'json')
        return (doc, 'xml')
    except etree.XMLSyntaxError:
        try:
            return (json.loads(s), 'json')
        except ValueError:
            raise Exception("Doesn't look like either JSON or XML")

def serialize(obj):
    if getattr(obj, 'tag', None):
        return etree.tostring(obj, pretty_print=True)
    return json.dumps(obj, indent=4)    