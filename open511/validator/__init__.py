try:
    unicode
except NameError:
    unicode = str

from copy import deepcopy
import os

from lxml import etree, isoschematron

from open511.converter import pluralize
from open511.converter.o5xml import json_struct_to_xml
from open511.utils.serialization import get_base_open511_element

class Open511ValidationError(Exception):
    pass

_schema_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'schema')
RELAXNG_PATH = os.path.join(_schema_dir, 'open511.rng')
SCHEMATRON_PATH = os.path.join(_schema_dir, 'open511.schematron')

RELAXNG_LXML = etree.RelaxNG(etree.parse(RELAXNG_PATH))
SCHEMATRON_LXML = isoschematron.Schematron(etree.parse(SCHEMATRON_PATH))

DEFAULT_VERSION = 'v1'

def validate(doc):
    errors = []
    for schema_name, schema in (('Schematron', SCHEMATRON_LXML), ('RELAX NG', RELAXNG_LXML)):
        try:
            schema.assertValid(doc)
        except etree.DocumentInvalid as e:
            if schema == SCHEMATRON_LXML:
                error = etree.fromstring(str(e))
                errors.extend(error.xpath('//svrl:text/text()', namespaces={'svrl': 'http://purl.oclc.org/dsdl/svrl'}))
            else:
                errors.append(u"Schema check failed: " + unicode(e))
    if errors:
        raise Open511ValidationError("\n\n".join(errors))
    return True

def _make_link(rel, href):
    l = etree.Element('link')
    l.set('rel', rel)
    l.set('href', href)
    return l

def validate_single_item(el, version=DEFAULT_VERSION, ignore_missing_urls=False):
    doc = get_base_open511_element(version=version)

    if ignore_missing_urls:
        el = deepcopy(el)
        if not el.xpath('link[rel=self]'):
            el.append(_make_link('self', '/fake/data'))
        if not el.xpath('link[rel=jurisdiction]'):
            el.append(_make_link('jurisdiction', 'http://example.com/fake/jurisdiction'))

    container = etree.Element(pluralize(el.tag))
    container.append(el)
    doc.append(container)
    return validate(doc)

def validate_single_json_item(obj, resource_type='event',
        ignore_missing_urls=False, version=DEFAULT_VERSION):
    return validate_single_item(json_struct_to_xml(obj, root=resource_type, custom_namespace='custom'),
        version=version, ignore_missing_urls=ignore_missing_urls)
