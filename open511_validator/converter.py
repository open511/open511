from lxml import etree
from lxml.builder import ElementMaker

NS_PROTECTED = 'http://open511.org/namespaces/internal-field'
NS_GML = 'http://www.opengis.net/gml'
NS_GML_PREFIX = '{' + NS_GML + '}'
XML_LANG = '{http://www.w3.org/XML/1998/namespace}lang'

NSMAP = {
    'gml': NS_GML
}

G = ElementMaker(namespace=NS_GML)


#########
# XML -> JSON
#########

def _maybe_intify(t):
    return int(t) if hasattr(t, 'isdigit') and t.isdigit() else t

def pluralize(s):
    return s[:-1] + 'ies' if s.endswith('y') else s + 's'

def xml_to_json(root):
    """Convert an Open511 XML document or document fragment to JSON.

    Takes an lxml Element object. Returns a dict ready to be JSON-serialized."""
    j = {}

    if len(root) == 0:  # Tag with no children, return str/int
        return _maybe_intify(root.text)

    if len(root) == 1 and root[0].tag.startswith('{' + NS_GML):  # GML
        return gml_to_geojson(root[0])

    if root.tag == 'open511':
        j['meta'] = {'version': root.get('version')}

    for elem in root:
        name = elem.tag
        if name == 'link' and elem.get('rel'):
            name = elem.get('rel') + '_url'
            if name == 'self_url':
                name = 'url'
            if root.tag == 'open511':
                j['meta'][name] = elem.get('href')
                continue
        elif name.startswith('{' + NS_PROTECTED):
            name = '!' + name[name.index('}') + 1:] 
        elif name[0] == '{':
            # Namespace!
            name = '+' + name[name.index('}') + 1:]

        if name in j:
            continue  # duplicate
        elif elem.tag == 'link' and not elem.text:
            j[name] = elem.get('href')
        elif len(elem):
            if name in ('attachments', 'grouped_events'):
                j[name] = [xml_link_to_json(child, to_dict=(name == 'attachments')) for child in elem]
            elif all((name == pluralize(child.tag) for child in elem)):
                # <something><somethings> serializes to a JSON array
                j[name] = [xml_to_json(child) for child in elem]
            else:
                j[name] = xml_to_json(elem)
        else:
            if root.tag == 'open511' and name.endswith('s') and not elem.text:
                # Special case: an empty e.g. <events /> container at the root level
                # should be serialized to [], not null
                j[name] = []
            else:
                j[name] = _maybe_intify(elem.text)

    return j


def xml_link_to_json(link, to_dict=False):
    if to_dict:
        d = {'url': link.get('href')}
        for attr in ('type', 'title', 'length', 'hreflang'):
            if link.get(attr):
                d[attr] = link.get(attr)
        return d
    else:
        return link.get('href')

#########
# JSON -> XML
#########

def json_doc_to_xml(json_obj, lang='en', custom_namespace=None):
    """Converts a Open511 JSON document to XML.

    lang: the appropriate language code

    Takes a dict deserialized from JSON, returns an lxml Element.

    Accepts only the full root-level JSON object from an Open511 response."""
    if 'meta' not in json_obj:
        raise Exception("This function requires a conforming Open511 JSON document with a 'meta' section.")
    json_obj = dict(json_obj)
    meta = json_obj.pop('meta')
    elem = etree.Element("open511", nsmap={
        'gml': NS_GML,
    })
    if lang:
        elem.set(XML_LANG, lang)
    elem.set('version', meta.pop('version'))
    pagination = json_obj.pop('pagination', None)

    json_struct_to_xml(json_obj, elem, custom_namespace=custom_namespace)

    if pagination:
        elem.append(json_struct_to_xml(pagination, 'pagination', custom_namespace=custom_namespace))

    json_struct_to_xml(meta, elem)

    return elem

def json_struct_to_xml(json_obj, root, custom_namespace=None):
    """Converts a Open511 JSON fragment to XML.

    Takes a dict deserialized from JSON, returns an lxml Element.

    This won't provide a confirming document if you pass in a full JSON document;
    it's for translating little fragments, and is mostly used internally."""
    if isinstance(root, basestring):
        if root.startswith('!'):
            root = etree.Element('{%s}%s' % (NS_PROTECTED, root[1:]))
        elif root.startswith('+'):
            if not custom_namespace:
                raise Exception("JSON fields starts with +, but no custom namespace provided")
            root = etree.Element('{%s}%s' % (custom_namespace, root[1:]))
        else:
            root = etree.Element(root)
    if root.tag in ('attachments', 'grouped_events'):
        for link in json_obj:
            root.append(json_link_to_xml(link))
    elif isinstance(json_obj, basestring):
        root.text = json_obj
    elif isinstance (json_obj, (int, float, long)):
        root.text = unicode(json_obj)
    elif isinstance(json_obj, dict):
        if frozenset(json_obj.keys()) == frozenset(('type', 'coordinates')):
            root.append(geojson_to_gml(json_obj))
        else:
            for key, val in json_obj.items():
                if key == 'url':
                    el = json_link_to_xml(val, 'self')
                elif key.endswith('_url'):
                    el = json_link_to_xml(val, key.replace('_url', ''))
                else:
                    el = json_struct_to_xml(val, key, custom_namespace=custom_namespace)
                if el is not None:
                    root.append(el)
    elif isinstance(json_obj, list):
        tag_name = root.tag
        if tag_name.endswith('ies'):
            tag_name = tag_name[:-3] + 'y'
        elif tag_name.endswith('s'):
            tag_name = tag_name[:-1]
        for val in json_obj:
            el = json_struct_to_xml(val, tag_name, custom_namespace=custom_namespace)
            if el is not None:
                root.append(el)
    elif json_obj is None:
        return None
    else:
        raise NotImplementedError
    return root

def json_link_to_xml(val, rel='related'):
    tag = etree.Element('link')
    tag.set('rel', rel)
    if hasattr(val, 'get') and 'url' in val:
        tag.set('href', val['url'])
        for attr in ('type', 'title', 'length'):
            if val.get(attr):
                tag.set(attr, unicode(val[attr]))
    else:
        tag.set('href', val)
    return tag

##########
# GEOSPATIAL
##########

def geojson_to_gml(gj, set_srs=True):
    """Given a dict deserialized from a GeoJSON object, returns an lxml Element
    of the corresponding GML geometry."""
    tag = G(gj['type'])
    if set_srs:
        tag.set('srsName', 'EPSG:4326')

    if gj['type'] == 'Point':
        tag.append(G.coordinates(','.join(str(c) for c in gj['coordinates'])))
    elif gj['type'] == 'LineString':
        tag.append(G.coordinates(' '.join(
            ','.join(str(c) for c in ll)
            for ll in gj['coordinates']
        )))
    elif gj['type'] == 'Polygon':
        rings = [
            G.LinearRing(
                G.coordinates(' '.join(
                    ','.join(str(c) for c in ll)
                    for ll in ring
                ))
            ) for ring in gj['coordinates']
        ]
        tag.append(G.outerBoundaryIs(rings.pop(0)))
        for ring in rings:
            tag.append(G.innerBoundaryIs(ring))
    elif gj['type'] in ('MultiPoint', 'MultiLineString', 'MultiPolygon'):
        single_type = gj['type'][5:]
        member_tag = single_type[0].lower() + single_type[1:] + 'Member'
        for coord in gj['coordinates']:
            tag.append(
                G(member_tag, geojson_to_gml({'type': single_type, 'coordinates': coord}, set_srs=False))
            )
    else:
        raise NotImplementedError

    return tag

def gml_to_geojson(el):
    """Given an lxml Element of a GML geometry, returns a dict in GeoJSON format."""
    tag = el.tag.replace('{%s}' % NS_GML, '')
    if tag == 'Point':
        coordinates = [float(c) for c in el.findtext('{%s}coordinates' % NS_GML).split(',')]
    elif tag == 'LineString':
        coordinates = [
            [float(x) for x in pair.split(',')]
            for pair in el.findtext('{%s}coordinates' % NS_GML).split(' ')
        ]
    elif tag == 'Polygon':
        coordinates = []
        for ring in el.xpath('gml:outerBoundaryIs/gml:LinearRing/gml:coordinates', namespaces=NSMAP) \
                + el.xpath('gml:innerBoundaryIs/gml:LinearRing/gml:coordinates', namespaces=NSMAP):
            coordinates.append([
                [float(x) for x in pair.split(',')]
                for pair in ring.text.split(' ')
            ])
    elif tag in ('MultiPoint', 'MultiLineString', 'MultiPolygon'):
        single_type = tag[5:]
        member_tag = single_type[0].lower() + single_type[1:] + 'Member'
        coordinates = [
            gml_to_geojson(member)['coordinates']
            for member in el.xpath('gml:%s/gml:%s' % (member_tag, single_type), namespaces=NSMAP)
        ]
    else:
        raise NotImplementedError

    return {
        'type': tag,
        'coordinates': coordinates
    }
