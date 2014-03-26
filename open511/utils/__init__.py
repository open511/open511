from functools import partial
import json
import re
import sys

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

def load_path(source):
    if source == '-':
        content = sys.stdin.read()
    elif re.match(r'https?://', source):
            import urllib2
            content = urllib2.urlopen(source).read()
    else:
        with open(source) as f:
            content = f.read()

    return deserialize(content)

class memoize_method(object):
    """Memoize an instance method.
    
    Return values are cached on the relevant object.
    
    http://code.activestate.com/recipes/577452-a-memoize-decorator-for-instance-methods/"""
    def __init__(self, func):
        self.func = func
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self.func
        return partial(self, obj)
    def __call__(self, *args, **kw):
        obj = args[0]
        try:
            cache = obj.__cache
        except AttributeError:
            cache = obj.__cache = {}
        key = (self.func, args[1:], frozenset(kw.items()))
        try:
            res = cache[key]
        except KeyError:
            res = cache[key] = self.func(*args, **kw)
        return res    
