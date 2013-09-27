import re
import sys


from open511_validator import validate, Open511ValidationError
from .converter import xml_to_json, json_doc_to_xml
from .utils import deserialize, serialize

def validate_cmdline():
    obj, obj_type = _load()
    if obj_type == 'json':
        obj = json_doc_to_xml(obj, custom_namespace='http://validator.open511.com/custom-field')
    try:
        validate(obj)
    except Open511ValidationError as e:
        sys.stderr.write(unicode(e))
        sys.stderr.write("\n")
        sys.exit(1)

def _load():
    if len(sys.argv) > 1:
        if re.match(r'https?://', sys.argv[1]):
            import urllib2
            content = urllib2.urlopen(sys.argv[1]).read()
        else:
            with open(sys.argv[1]) as f:
                content = f.read()
    else:
        content = sys.stdin.read()

    return deserialize(content)

def convert_cmdline():
    obj, obj_type = _load()
    if obj_type == 'xml':
        result = xml_to_json(obj)
    elif obj_type == 'json':
        result = json_doc_to_xml(obj)
    sys.stdout.write(serialize(result))
    sys.stdout.write("\n")
