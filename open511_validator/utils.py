import json

from lxml import etree

def deserialize(s):
    s = s.strip()
    try:
        return (etree.fromstring(s), 'xml')
    except etree.XMLSyntaxError:
        try:
            return (json.loads(s), 'json')
        except ValueError:
            raise Exception("Doesn't look like either JSON or XML")

def serialize(obj):
    if getattr(obj, 'tag', None) == 'open511':
        return etree.tostring(obj, pretty_print=True)
    return json.dumps(obj, indent=4)
