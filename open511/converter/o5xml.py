try:
    unicode
except NameError:
    unicode = str

import json

from lxml import etree
from lxml.builder import ElementMaker

from open511.utils.serialization import (NS_GML, NS_PROTECTED,
    get_base_open511_element)

NS_GML_PREFIX = '{' + NS_GML + '}'

G = ElementMaker(namespace=NS_GML)

def json_doc_to_xml(json_obj, lang='en', custom_namespace=None):
    """Converts a Open511 JSON document to XML.

    lang: the appropriate language code

    Takes a dict deserialized from JSON, returns an lxml Element.

    Accepts only the full root-level JSON object from an Open511 response."""
    if 'meta' not in json_obj:
        raise Exception("This function requires a conforming Open511 JSON document with a 'meta' section.")
    json_obj = dict(json_obj)
    meta = json_obj.pop('meta')
    elem = get_base_open511_element(lang=lang, version=meta.pop('version'))

    pagination = json_obj.pop('pagination', None)

    json_struct_to_xml(json_obj, elem, custom_namespace=custom_namespace)

    if pagination:
        elem.append(json_struct_to_xml(pagination, 'pagination', custom_namespace=custom_namespace))

    json_struct_to_xml(meta, elem)

    return elem

def json_struct_to_xml(json_obj, root, custom_namespace=None):
    """Converts a Open511 JSON fragment to XML.

    Takes a dict deserialized from JSON, returns an lxml Element.

    This won't provide a conforming document if you pass in a full JSON document;
    it's for translating little fragments, and is mostly used internally."""
    if isinstance(root, (str, unicode)):
        if root.startswith('!'):
            root = etree.Element('{%s}%s' % (NS_PROTECTED, root[1:]))
        elif root.startswith('+'):
            if not custom_namespace:
                raise Exception("JSON fields starts with +, but no custom namespace provided")
            root = etree.Element('{%s}%s' % (custom_namespace, root[1:]))
        else:
            root = etree.Element(root)
    if root.tag in ('attachments', 'grouped_events', 'media_files'):
        for link in json_obj:
            root.append(json_link_to_xml(link))
    elif isinstance(json_obj, (str, unicode)):
        root.text = json_obj
    elif isinstance(json_obj, (int, float)):
        root.text = unicode(json_obj)
    elif isinstance(json_obj, dict):
        if frozenset(json_obj.keys()) == frozenset(('type', 'coordinates')):
            root.append(geojson_to_gml(json_obj))
        else:
            for key, val in json_obj.items():
                if key == 'url' or key.endswith('_url'):
                    el = json_link_to_xml(val, json_link_key_to_xml_rel(key))
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

def json_link_key_to_xml_rel(key):
    if key == 'url':
        return 'self'
    elif key.endswith('_url'):
        return key[:-4]
    return key


def json_link_to_xml(val, rel='related'):
    tag = etree.Element('link')
    tag.set('rel', rel)
    if hasattr(val, 'get') and 'url' in val:
        tag.set('href', val['url'])
        for attr in ('type', 'title', 'length', 'hreflang'):
            if val.get(attr):
                tag.set(attr, unicode(val[attr]))
    else:
        tag.set('href', val)
    return tag

def _reverse_geojson_coords(coords):
    return "%s %s" % (coords[1], coords[0])

def geojson_to_gml(gj, set_srs=True):
    """Given a dict deserialized from a GeoJSON object, returns an lxml Element
    of the corresponding GML geometry."""
    tag = G(gj['type'])
    if set_srs:
        tag.set('srsName', 'urn:ogc:def:crs:EPSG::4326')

    if gj['type'] == 'Point':
        tag.append(G.pos(_reverse_geojson_coords(gj['coordinates'])))
    elif gj['type'] == 'LineString':
        tag.append(G.posList(' '.join(_reverse_geojson_coords(ll) for ll in gj['coordinates'])))
    elif gj['type'] == 'Polygon':
        rings = [
            G.LinearRing(
                G.posList(' '.join(_reverse_geojson_coords(ll) for ll in ring))
            ) for ring in gj['coordinates']
        ]
        tag.append(G.exterior(rings.pop(0)))
        for ring in rings:
            tag.append(G.interior(ring))
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

def geom_to_xml_element(geom):
    """Transform a GEOS or OGR geometry object into an lxml Element
    for the GML geometry."""
    if geom.srs.srid != 4326:
        raise NotImplementedError("Only WGS 84 lat/long geometries (SRID 4326) are supported.")
    # GeoJSON output is far more standard than GML, so go through that
    return geojson_to_gml(json.loads(geom.geojson))  