import re
import sys

from lxml import etree

from open511_validator import validate, Open511ValidationError
from open511_validator.converter import xml_to_json

def validate_cmdline():
    if len(sys.argv) > 1:
        if re.match(r'https?://', sys.argv[1]):
            import urllib2
            doc = etree.fromstring(urllib2.urlopen(sys.argv[1]).read())
        else:
            doc = etree.parse(sys.argv[1])
    else:
        doc = etree.fromstring(sys.stdin.read())
    try:
        validate(doc)
    except Open511ValidationError as e:
        sys.stderr.write(unicode(e))
        sys.stderr.write("\n")
        sys.exit(1)

def convert_cmdline():
    doc = etree.parse(sys.argv[1])
    import json
    json.dump(xml_to_json(doc.getroot()), sys.stdout, indent=4)
    sys.stdout.write("\n")
