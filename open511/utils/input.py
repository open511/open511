import re
import sys

try:
    import urllib2
except ImportError:
    import urllib.request as urllib2

from open511.utils.serialization import deserialize

def load_path(source):
    if source == '-':
        content = sys.stdin.read()
    elif re.match(r'https?://', source):
            content = urllib2.urlopen(source).read()
    else:
        with open(source) as f:
            content = f.read()

    return deserialize(content)

def get_jurisdiction_settings(jurisdiction_url):
    from lxml import etree
    req = urllib2.Request(jurisdiction_url)
    req.add_header('Accept', 'application/xml')
    resp = urllib2.urlopen(req)

    root = etree.fromstring(resp.read())
    opts = {
        'timezone': root.findtext('jurisdictions/jurisdiction/timezone'),
        'distance_unit': root.findtext('jurisdictions/jurisdiction/distance_unit')
    }
    if not opts['distance_unit']:
        opts['distance_unit'] = 'KILOMETRES'
    return opts
