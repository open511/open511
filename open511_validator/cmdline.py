import argparse
import re
import sys

from open511_validator import validate, Open511ValidationError
from .converter import open511_convert, json_doc_to_xml, FORMATS_LIST
from .utils import deserialize

def validate_cmdline():
    parser = argparse.ArgumentParser(description='Validate an Open511 document.')
    parser.add_argument('source', metavar='DOC', type=str,
        help='Document to validate: path, URL, or - to read from stdin')
    arguments = parser.parse_args()
    obj, obj_type = _load(arguments.source)
    if obj_type == 'json':
        obj = json_doc_to_xml(obj, custom_namespace='http://validator.open511.com/custom-field')
    try:
        validate(obj)
    except Open511ValidationError as e:
        sys.stderr.write(unicode(e))
        sys.stderr.write("\n")
        sys.exit(1)

def _load(source):
    if source == '-':
        content = sys.stdin.read()
    elif re.match(r'https?://', source):
            import urllib2
            content = urllib2.urlopen(source).read()
    else:
        with open(source) as f:
            content = f.read()

    return deserialize(content)

def convert_cmdline():
    parser = argparse.ArgumentParser(description='Convert an Open511 document to another format.')
    parser.add_argument('-f', '--format', type=str,
        help='Target format: ' + ', '.join(f.name for f in FORMATS_LIST))
    parser.add_argument('source', metavar='DOC', type=str,
        help='Document to validate: path, URL, or - to read from stdin')
    arguments = parser.parse_args()
    obj, obj_type = _load(arguments.source)
    if arguments.format:
        output_format = arguments.format
    else:
        output_format = 'xml' if obj_type == 'json' else 'json'
    result = open511_convert(obj, output_format, serialize=True)
    sys.stdout.write(result)
    sys.stdout.write("\n")
