import argparse
import logging
import sys

from open511.converter import open511_convert, FORMATS_LIST
from open511.utils.input import load_path

def convert_cmdline():
    logging.basicConfig()
    parser = argparse.ArgumentParser(description='Convert an Open511 document to another format.')
    parser.add_argument('-f', '--format', type=str,
        help='Target format: ' + ', '.join(f.name for f in FORMATS_LIST))
    parser.add_argument('source', metavar='DOC', type=str,
        help='Document to validate: path, URL, or - to read from stdin')
    arguments = parser.parse_args()
    obj, obj_type = load_path(arguments.source)
    if arguments.format:
        output_format = arguments.format
    else:
        output_format = 'xml' if obj_type == 'json' else 'json'
    result = open511_convert(obj, output_format, serialize=True)
    stdout = sys.stdout
    if hasattr(stdout, 'detach'):
        stdout = stdout.detach()
    stdout.write(result)
    sys.stdout.write("\n")
