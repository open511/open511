from lxml.builder import ElementMaker

NS_KML = 'http://www.opengis.net/kml/2.2'

K = ElementMaker(namespace=NS_KML, nsmap={None: NS_KML})

def convert_to_kml(input):

    placemarks = []
    for event in input.get('events', []):
        e = K('Placemark',
            K('name', event.get('headline', '')),
            K('description', event.get('description', '')),
            _geojson_to_kml(event['geography'])
        )

        data = {
            'Severity': event.get('severity').title(),
            'Status': event.get('status').title(),
            'Type': event.get('event_type').title()
        }
        if 'detour' in event:
            data['Detour'] = event['detour']

        if data:
            e.append(K('ExtendedData', *[
                K('Data', K('value', value), name=key) for key, value in data.iteritems()
            ]))

        placemarks.append(e)

    return K('kml', K('Document', *placemarks))

def _geojson_to_kml(geog):
    t = geog['type']
    if t == 'Point':
        coords = '%s,%s' % tuple(geog['coordinates'])
    elif t == 'LineString':
        coords = ' '.join('%s,%s' % tuple(c) for c in geog['coordinates'])
    else:
        raise NotImplementedError
    return K(t, K('coordinates', coords))

