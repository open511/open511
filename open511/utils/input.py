import re
import sys

from open511.utils.serialization import deserialize

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