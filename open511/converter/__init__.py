from collections import namedtuple
import json

from lxml import etree

from open511.converter.o5xml import (json_struct_to_xml,
    json_doc_to_xml, geojson_to_gml, json_link_key_to_xml_rel)
from open511.converter.o5json import pluralize, xml_to_json
from open511.converter.atom import convert_to_atom
from open511.converter.kml import convert_to_kml

ConversionFormat = namedtuple('ConversionFormat', 'name full_name input_format func content_type serializer')

noop = lambda x: x
_serialize_xml = lambda x: etree.tostring(x, pretty_print=True)

FORMATS_LIST = [
    ConversionFormat('xml', 'XML', 'xml', noop, 'application/xml', _serialize_xml),
    ConversionFormat('json', 'JSON', 'json', noop, 'application/json', lambda j: json.dumps(j, indent=4)),
    ConversionFormat('atom', 'Atom (GeoRSS, MASAS)', 'xml', convert_to_atom, 'application/atom+xml', _serialize_xml),
    ConversionFormat('kml', 'KML', 'json', convert_to_kml, 'application/vnd.google-earth.kml+xml', _serialize_xml),
]

FORMATS = dict((cf.name, cf) for cf in FORMATS_LIST)

def open511_convert(input_doc, output_format, serialize=True):
    """
    Convert an Open511 document between formats.
    input_doc - either an lxml open511 Element or a deserialized JSON dict
    output_format - short string name of a valid output format, as listed above
    """

    if getattr(input_doc, 'tag', None) == 'open511':
        input_format = 'xml'
    elif isinstance(input_doc, dict):
        input_format = 'json'
    else:
        raise ValueError("Unrecognized input document in open511_convert")

    try:
        output_format_info = FORMATS[output_format]
    except KeyError:
        raise ValueError("Unrecognized output format %s" % output_format)

    if input_format != output_format_info.input_format:
        if output_format_info.input_format == 'xml':
            input_doc = json_doc_to_xml(input_doc)
        elif output_format_info.input_format == 'json':
            input_doc = xml_to_json(input_doc)

    result = output_format_info.func(input_doc)
    if serialize:
        result = output_format_info.serializer(result)
    return result
