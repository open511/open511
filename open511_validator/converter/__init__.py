from collections import namedtuple

from open511_validator.converter.xml import (json_struct_to_xml,
    json_doc_to_xml, geojson_to_gml, json_link_key_to_xml_rel)
from open511_validator.converter.json import pluralize, xml_to_json

ConversionFormat = namedtuple('ConversionFormat', 'name full_name input_format func')

FORMATS = [
    ConversionFormat('xml', 'XML', 'xml', lambda x: x),
    ConversionFormat('json', 'JSON', 'json', lambda j: j)
]

_formats_dict = dict((cf.name, cf) for cf in FORMATS)

def open511_convert(input_doc, output_format):
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
        output_format_info = _formats_dict[output_format]
    except KeyError:
        raise ValueError("Unrecognized output format %s" % output_format)

    if input_format != output_format_info.input_format:
        if output_format_info.input_format == 'xml':
            input_doc = json_doc_to_xml(input_doc)
        elif output_format_info.input_format == 'json':
            input_doc = xml_to_json(input_doc)

    return output_format_info.func(input_doc)
