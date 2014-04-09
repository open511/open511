import os

from lxml import etree, isoschematron

class Open511ValidationError(Exception):
    pass

_schema_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'schema')
RELAXNG_PATH = os.path.join(_schema_dir, 'open511.rng')
SCHEMATRON_PATH = os.path.join(_schema_dir, 'open511.schematron')

RELAXNG_LXML = etree.RelaxNG(etree.parse(RELAXNG_PATH))
SCHEMATRON_LXML = isoschematron.Schematron(etree.parse(SCHEMATRON_PATH))

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