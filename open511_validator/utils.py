import json

from lxml import etree

def deserialize(s):
    s = s.strip()
    if s.startswith('{'):
        return (json.loads(s), 'json')
    elif s.startswith('<'):
        return (etree.fromstring(s),  'xml')
    raise Exception("Doesn't look like either JSON or XML")

def serialize(obj):
    if isinstance(obj, dict):
        return json.dumps(obj, indent=4)
    else:
        return etree.tostring(obj, pretty_print=True)