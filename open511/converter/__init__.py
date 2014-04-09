from collections import namedtuple
import json

from lxml import etree

from open511.converter.o5xml import (json_doc_to_xml, json_struct_to_xml,
    geom_to_xml_element, json_link_key_to_xml_rel, geojson_to_gml)
from open511.converter.o5json import xml_to_json, pluralize
from open511.converter.atom import convert_to_atom
from open511.converter.kml import convert_to_kml

ConversionFormat = namedtuple('ConversionFormat', 'name full_name input_format func content_type serializer')

noop = lambda x: x
_serialize_xml = lambda x: etree.tostring(x, pretty_print=True)

FORMATS_LIST = [
    ConversionFormat('xml', 'XML', 'xml', noop, 'application/xml', _serialize_xml),
    ConversionFormat('json', 'JSON', 'json', noop, 'application/json', lambda j: json.dumps(j, indent=4).encode('utf8')),
    ConversionFormat('atom', 'Atom (GeoRSS, MASAS)', 'xml', convert_to_atom, 'application/atom+xml', _serialize_xml),
    ConversionFormat('kml', 'KML', 'json', convert_to_kml, 'application/vnd.google-earth.kml+xml', _serialize_xml),
]

FORMATS = dict((cf.name, cf) for cf in FORMATS_LIST)

def ensure_format(doc, format):
    """
    Ensures that the provided document is an lxml Element or json dict.
    """
    assert format in ('xml', 'json')
    if getattr(doc, 'tag', None) == 'open511':
        if format == 'json':
            return xml_to_json(doc)
    elif isinstance(doc, dict) and 'meta' in doc:
        if format == 'xml':
            return json_doc_to_xml(doc)
    else:
        raise ValueError("Unrecognized input document")
    return doc


def open511_convert(input_doc, output_format, serialize=True, **kwargs):
    """
    Convert an Open511 document between formats.
    input_doc - either an lxml open511 Element or a deserialized JSON dict
    output_format - short string name of a valid output format, as listed above
    """

    try:
        output_format_info = FORMATS[output_format]
    except KeyError:
        raise ValueError("Unrecognized output format %s" % output_format)

    input_doc = ensure_format(input_doc, output_format_info.input_format)

    result = output_format_info.func(input_doc, **kwargs)
    if serialize:
        result = output_format_info.serializer(result)
    return result

# Silence warnings
geom_to_xml_element, json_struct_to_xml, pluralize, json_link_key_to_xml_rel, geojson_to_gml
