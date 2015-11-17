try:
    unicode
except NameError:
    unicode = str

import argparse
import sys

from open511.validator import validate, Open511ValidationError
from open511.converter import json_doc_to_xml
from open511.utils.input import load_path

def validate_cmdline():
    parser = argparse.ArgumentParser(description='Validate an Open511 document.')
    parser.add_argument('source', metavar='DOC', type=str,
        help='Document to validate: path, URL, or - to read from stdin')
    arguments = parser.parse_args()
    obj, obj_type = load_path(arguments.source)
    if obj_type == 'json':
        obj = json_doc_to_xml(obj, custom_namespace='http://validator.open511.org/custom-field')
    try:
        validate(obj)
    except Open511ValidationError as e:
        sys.stderr.write(unicode(e))
        sys.stderr.write("\n")
        sys.exit(1)