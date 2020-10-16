from nlmaps_tools.parse_mrl import Symbol

QUERIES = [
    {
        'mrl': "query(around(center(area(keyval('name','Dortmund')),nwr(keyval('name','Springmorgen'))),search(nwr(keyval('railway','abandoned'))),maxdist(WALKING_DIST)),qtype(latlong))",
        'features': {'area': 'Dortmund', 'center_nwr': [('name', 'Springmorgen')], 'target_nwr': [('railway', 'abandoned')], 'maxdist': Symbol('WALKING_DIST'), 'query_type': 'around_query', 'qtype': (Symbol('latlong'),)},
    },
    {
        'mrl': "query(around(center(nwr(keyval('name','Frankfurt am Main'))),search(nwr(keyval('building','hall'))),maxdist(DIST_INTOWN)),qtype(least(topx(1))))",
        'features': {'center_nwr': [('name', 'Frankfurt am Main')], 'target_nwr': [('building', 'hall')], 'maxdist': Symbol('DIST_INTOWN'), 'query_type': 'around_query', 'qtype': (('least', ('topx', Symbol('1'))),)},
    },
    {
        'mrl': "query(around(center(area(keyval('name','Lyon')),nwr(keyval('name','Rue Claude-Joseph Bonnet'))),search(nwr(keyval('amenity','doctors'))),maxdist(DIST_INTOWN),topx(1)),qtype(latlong))",
        'features': {'area': 'Lyon', 'center_nwr': [('name', 'Rue Claude-Joseph Bonnet')], 'target_nwr': [('amenity', 'doctors')], 'maxdist': Symbol('DIST_INTOWN'), 'around_topx': Symbol('1'), 'query_type': 'around_query', 'qtype': (Symbol('latlong'),)},
    },
    {
        'mrl': "query(area(keyval('name','Dresden')),nwr(keyval('building','greenhouse')),qtype(latlong))",
        'features': {'area': 'Dresden', 'target_nwr': [('building', 'greenhouse')], 'query_type': 'in_query', 'qtype': (Symbol('latlong'),)},
    },
    {
        'mrl': "query(west(area(keyval('name','Dresden')),nwr(keyval('building','greenhouse'))),qtype(latlong))",
        'features': {'cardinal_direction': 'west', 'area': 'Dresden', 'target_nwr': [('building', 'greenhouse')], 'query_type': 'in_query', 'qtype': (Symbol('latlong'),)},
    },
    {
        'mrl': "query(area(keyval('name','Heidelberg')),nwr(keyval('amenity','restaurant')),qtype(nodup(findkey('cuisine'))))",
        'features': {'area': 'Heidelberg', 'target_nwr': [('amenity', 'restaurant')], 'query_type': 'in_query', 'qtype': (('nodup', ('findkey', 'cuisine')),)},
    },
    {
        'mrl': "query(area(keyval('name','Heidelberg')),nwr(keyval('amenity','restaurant')),qtype(nodup(findkey(and('cuisine','name')))))",
        'features': {'area': 'Heidelberg', 'target_nwr': [('amenity', 'restaurant')], 'query_type': 'in_query', 'qtype': (('nodup', ('findkey', ('and', 'cuisine', 'name'))),)},
    },
    {
        'mrl': "query(area(keyval('name','Heidelberg')),nwr(keyval('amenity','car_sharing')),qtype(count))",
        'features': {'area': 'Heidelberg', 'target_nwr': [('amenity', 'car_sharing')], 'query_type': 'in_query', 'qtype': (Symbol('count'),)},
    },
    {
        'mrl': "query(area(keyval('name','Paris')),nwr(and(keyval('shop','bakery'),keyval('shop','butcher'))),qtype(latlong))",
        'features': {'area': 'Paris', 'target_nwr': [('and', ('shop', 'bakery'), ('shop', 'butcher'))], 'query_type': 'in_query', 'qtype': (Symbol('latlong'),)},
    },
    {
        'mrl': "query(area(keyval('name','Heidelberg')),nwr(keyval('amenity','place_of_worship'),keyval('denomination','catholic')),qtype(latlong))",
        'features': {'area': 'Heidelberg', 'target_nwr': [('amenity', 'place_of_worship'), ('denomination', 'catholic')], 'query_type': 'in_query', 'qtype': (Symbol('latlong'),)},
    },
    {
        'mrl': "query(area(keyval('name','Berlin')),nwr(keyval('highway',or('secondary','secondary_link'))),qtype(count))",
        'features': {'area': 'Berlin', 'target_nwr': [('highway', ('or', 'secondary', 'secondary_link'))], 'query_type': 'in_query', 'qtype': (Symbol('count'),)},
    },
    {
        'mrl': "query(nwr(keyval('monitoring:bicycle','yes')),qtype(findkey('name')))",
        'features': {'target_nwr': [('monitoring:bicycle', 'yes')], 'query_type': 'in_query', 'qtype': (('findkey', 'name'),)},
    },
    {
        'mrl': "query(around(center(area(keyval('name','Heidelberg')),nwr(keyval('name','Yorckstraße'))),search(nwr(and(keyval('amenity','bank'),keyval('amenity','pharmacy')))),maxdist(DIST_INTOWN),topx(1)),qtype(latlong))",
        'features': {'area': 'Heidelberg', 'center_nwr': [('name', 'Yorckstraße')], 'target_nwr': [('and', ('amenity', 'bank'), ('amenity', 'pharmacy'))], 'maxdist': Symbol('DIST_INTOWN'), 'around_topx': Symbol('1'), 'query_type': 'around_query', 'qtype': (Symbol('latlong'),)},
    },
    {
        'mrl': "query(around(center(area(keyval('name','Heidelberg')),nwr(keyval('name','INF 325'))),search(nwr(keyval('shop','supermarket'),or(keyval('organic','only'),keyval('organic','yes')))),maxdist(5000)),qtype(latlong))",
        'features': {'area': 'Heidelberg', 'center_nwr': [('name', 'INF 325')], 'target_nwr': [('shop', 'supermarket'), ('or', ('organic', 'only'), ('organic', 'yes'))], 'maxdist': Symbol('5000'), 'query_type': 'around_query', 'qtype': (Symbol('latlong'),)},
    },
    {
        'mrl': "query(north(around(center(area(keyval('name','Paris'))),search(nwr(keyval('religion','muslim'))),maxdist(DIST_OUTTOWN))),qtype(least(topx(1))))",
        'features': {'cardinal_direction': 'north', 'area': 'Paris', 'deprecations': {'deprecated_lone_area_in_center'}, 'target_nwr': [('religion', 'muslim')], 'maxdist': Symbol('DIST_OUTTOWN'), 'query_type': 'around_query', 'qtype': (('least', ('topx', Symbol('1'))),)},
    },
    {
        'mrl': "query(area(keyval('name','Edinburgh')),nwr(keyval('amenity','fuel')),qtype(latlong,nodup(findkey('brand'))))",
        'features': {'area': 'Edinburgh', 'target_nwr': [('amenity', 'fuel')], 'query_type': 'in_query', 'qtype': (Symbol('latlong'), ('nodup', ('findkey', 'brand')))},
    },
    {
        'mrl': "query(area(keyval('name','Heidelberg')),nwr(keyval('amenity','restaurant'),keyval('cuisine',or('greek','italian'))),qtype(findkey('name')))",
        'features': {'area': 'Heidelberg', 'target_nwr': [('amenity', 'restaurant'), ('cuisine', ('or', 'greek', 'italian'))], 'query_type': 'in_query', 'qtype': (('findkey', 'name'),)},
    },
    {
        'mrl': "query(area(keyval('name','Edinburgh')),nwr(keyval('tourism','hotel'),keyval('stars','4')),qtype(findkey('name',topx(1))))",
        'features': {'area': 'Edinburgh', 'target_nwr': [('tourism', 'hotel'), ('stars', '4')], 'query_type': 'in_query', 'deprecations': {'topx_in_findkey'}, 'qtype': (('findkey', 'name', ('topx', Symbol('1'))),)},
    },
    {
        'mrl': "dist(query(area(keyval('name','Edinburgh')),nwr(keyval('name','Palace of Holyroodhouse')),qtype(latlong)),query(area(keyval('name','Edinburgh')),nwr(keyval('name','Camera Obscura')),qtype(latlong)))",
        'features': {'sub': [{'area': 'Edinburgh', 'target_nwr': [('name', 'Palace of Holyroodhouse')], 'query_type': 'in_query', 'qtype': (Symbol('latlong'),)}, {'area': 'Edinburgh', 'target_nwr': [('name', 'Camera Obscura')], 'query_type': 'in_query', 'qtype': (Symbol('latlong'),)}], 'query_type': 'dist'},
    },
    {
        'mrl': "dist(query(around(center(area(keyval('name','Edinburgh')),nwr(keyval('name','Palace of Holyroodhouse'))),search(nwr(keyval('name','Edinburgh Waverley'),keyval('railway','station'))),maxdist(DIST_INTOWN)),qtype(latlong)))",
        'features': {'sub': [{'area': 'Edinburgh', 'center_nwr': [('name', 'Palace of Holyroodhouse')], 'target_nwr': [('name', 'Edinburgh Waverley'), ('railway', 'station')], 'maxdist': Symbol('DIST_INTOWN'), 'query_type': 'around_query', 'qtype': (Symbol('latlong'),)}], 'query_type': 'dist'},
    },
    {
        'mrl': "dist(query(area(keyval('name','Heidelberg')),nwr(keyval('name','Heidelberger Schloss')),qtype(latlong)),query(area(keyval('name','Heidelberg')),nwr(keyval('name','Heidelberg Hbf')),qtype(least(topx(1)))),for('walk'))",
        'features': {'sub': [{'area': 'Heidelberg', 'target_nwr': [('name', 'Heidelberger Schloss')], 'query_type': 'in_query', 'qtype': (Symbol('latlong'),)}, {'area': 'Heidelberg', 'target_nwr': [('name', 'Heidelberg Hbf')], 'query_type': 'in_query', 'qtype': (('least', ('topx', Symbol('1'))),)}], 'for': 'walk', 'query_type': 'dist'},
    },
]
