from lxml.builder import E

NS_PROTECTED = 'http://open511.org/namespaces/internal-field'
NS_GML = 'http://www.opengis.net/gml'

def _maybe_intify(t):
    return int(t) if hasattr(t, 'isdigit') and t.isdigit() else t

def xml_to_json(open511_el):
    assert open511_el.tag == 'open511'
    

def _xml_to_json(root):
    j = {}

    if len(root) == 0:
        return _maybe_intify(root.text)

    if len(root) == 1 and root[0].tag.startswith('{' + NS_GML):
        return gml_to_geojson(root[0])

    for elem in root:
        name = elem.tag
        if name == 'link' and elem.get('rel'):
            name = elem.get('rel') + '_url'
            if name == 'self_url':
                name = 'url'
        elif name.startswith('{' + NS_PROTECTED):
            name = '!' + name[name.index('}') + 1:] 
        elif name[0] == '{':
            # Namespace!
            name = '+' + name[name.index('}') + 1:]

        if name in j:
            continue  # duplicate
        elif elem.tag == 'link' and not elem.text:
            j[name] = elem.get('href')
        elif len(elem):
            if name in ('attachments', 'grouped_events'):
                j[name] = [xml_link_to_json(child, to_dict=(name == 'attachments')) for child in elem]
            elif all((name == child.tag + 's' for child in elem)):
                # <something><somethings> serializes to a JSON array
                j[name] = [_xml_to_json(child) for child in elem]
            else:
                j[name] = _xml_to_json(elem)
        else:
            j[name] = _maybe_intify(elem.text)

    return j


def xml_link_to_json(link, to_dict=False):
    if to_dict:
        d = {'url': link.get('href')}
        for attr in ('type', 'title', 'length'):
            if link.get(attr):
                d[attr] = link.get(attr)
        return d
    else:
        return link.get('href')

def gml_to_geojson(el):
    """Given an lxml Element of a GML geometry, returns a dict in GeoJSON format."""
    coords = el.findtext('{%s}coordinates' % NS_GML)
    if el.tag.endswith('Point'):
        return {
            'type': 'Point',
            'coordinates': [float(c) for c in coords.split(',')]
        }
    elif el.tag.endswith('LineString'):
        return {
            'type': 'LineString',
            'coordinates': [
            [float(x) for x in pair.split(',')]
            for pair in coords.split(' ')
            ]
        }
    else:
        raise NotImplementedError