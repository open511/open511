from open511.utils.serialization import NS_GML, NS_PROTECTED, NSMAP

def _maybe_intify(t):
    return int(t) if hasattr(t, 'isdigit') and t.isdigit() else t

def pluralize(s):
    return s[:-1] + 'ies' if s.endswith('phy') else s + 's'

def xml_to_json(root):
    """Convert an Open511 XML document or document fragment to JSON.

    Takes an lxml Element object. Returns a dict ready to be JSON-serialized."""
    j = {}

    if len(root) == 0:  # Tag with no children, return str/int
        return _maybe_intify(root.text)

    if len(root) == 1 and root[0].tag.startswith('{' + NS_GML):  # GML
        return gml_to_geojson(root[0])

    if root.tag == 'open511':
        j['meta'] = {'version': root.get('version')}

    for elem in root:
        name = elem.tag
        if name == 'link' and elem.get('rel'):
            name = elem.get('rel') + '_url'
            if name == 'self_url':
                name = 'url'
            if root.tag == 'open511':
                j['meta'][name] = elem.get('href')
                continue
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
            if name == 'grouped_events':
                # An array of URLs
                j[name] = [xml_link_to_json(child, to_dict=False) for child in elem]
            elif name in ('attachments', 'media_files'):
                # An array of JSON objects
                j[name] = [xml_link_to_json(child, to_dict=True) for child in elem]
            elif all((name == pluralize(child.tag) for child in elem)):
                # <something><somethings> serializes to a JSON array
                j[name] = [xml_to_json(child) for child in elem]
            else:
                j[name] = xml_to_json(elem)
        else:
            if root.tag == 'open511' and name.endswith('s') and not elem.text:
                # Special case: an empty e.g. <events /> container at the root level
                # should be serialized to [], not null
                j[name] = []
            else:
                j[name] = _maybe_intify(elem.text)

    return j


def xml_link_to_json(link, to_dict=False):
    if to_dict:
        d = {'url': link.get('href')}
        for attr in ('type', 'title', 'length', 'hreflang'):
            if link.get(attr):
                d[attr] = link.get(attr)
        return d
    else:
        return link.get('href')

##########
# GEOSPATIAL
##########

def _reverse_gml_coords(s):
    coords = s.split(' ')
    gj = []
    for i in range(0, len(coords), 2):
        gj.append((float(coords[i+1]), float(coords[i])))
    return gj

def gml_to_geojson(el):
    """Given an lxml Element of a GML geometry, returns a dict in GeoJSON format."""
    if el.get('srsName') not in ('urn:ogc:def:crs:EPSG::4326', None):
        if el.get('srsName') == 'EPSG:4326':
            return _gmlv2_to_geojson(el)
        else:
            raise NotImplementedError("Unrecognized srsName %s" % el.get('srsName'))
    tag = el.tag.replace('{%s}' % NS_GML, '')
    if tag == 'Point':
        coordinates = _reverse_gml_coords(el.findtext('{%s}pos' % NS_GML))[0]
    elif tag == 'LineString':
        coordinates = _reverse_gml_coords(el.findtext('{%s}posList' % NS_GML))
    elif tag == 'Polygon':
        coordinates = []
        for ring in el.xpath('gml:exterior/gml:LinearRing/gml:posList', namespaces=NSMAP) \
                + el.xpath('gml:interior/gml:LinearRing/gml:posList', namespaces=NSMAP):
            coordinates.append(_reverse_gml_coords(ring.text))
    elif tag in ('MultiPoint', 'MultiLineString', 'MultiPolygon'):
        single_type = tag[5:]
        member_tag = single_type[0].lower() + single_type[1:] + 'Member'
        coordinates = [
            gml_to_geojson(member)['coordinates']
            for member in el.xpath('gml:%s/gml:%s' % (member_tag, single_type), namespaces=NSMAP)
        ]
    else:
        raise NotImplementedError

    return {
        'type': tag,
        'coordinates': coordinates
    }

def _gmlv2_to_geojson(el):
    """Translates a deprecated GML 2.0 geometry to GeoJSON"""
    tag = el.tag.replace('{%s}' % NS_GML, '')
    if tag == 'Point':
        coordinates = [float(c) for c in el.findtext('{%s}coordinates' % NS_GML).split(',')]
    elif tag == 'LineString':
        coordinates = [
            [float(x) for x in pair.split(',')]
            for pair in el.findtext('{%s}coordinates' % NS_GML).split(' ')
        ]
    elif tag == 'Polygon':
        coordinates = []
        for ring in el.xpath('gml:outerBoundaryIs/gml:LinearRing/gml:coordinates', namespaces=NSMAP) \
                + el.xpath('gml:innerBoundaryIs/gml:LinearRing/gml:coordinates', namespaces=NSMAP):
            coordinates.append([
                [float(x) for x in pair.split(',')]
                for pair in ring.text.split(' ')
            ])
    elif tag in ('MultiPoint', 'MultiLineString', 'MultiPolygon', 'MultiCurve'):
        if tag == 'MultiCurve':
            single_type = 'LineString'
            member_tag = 'curveMember'
        else:
            single_type = tag[5:]
            member_tag = single_type[0].lower() + single_type[1:] + 'Member'
        coordinates = [
            gml_to_geojson(member)['coordinates']
            for member in el.xpath('gml:%s/gml:%s' % (member_tag, single_type), namespaces=NSMAP)
        ]
    else:
        raise NotImplementedError

    return {
        'type': tag,
        'coordinates': coordinates
    }
