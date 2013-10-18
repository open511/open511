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
    if isinstance(obj, dict):
        return json.dumps(obj, indent=4)
    else:
        return etree.tostring(obj, pretty_print=True)