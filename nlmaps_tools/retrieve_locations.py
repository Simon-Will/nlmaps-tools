import argparse
from collections import namedtuple
import sys

import jinja2
import requests

BoundingBox = namedtuple('BoundingBox',
                         ['lat_start', 'lon_start', 'lat_end', 'lon_end'])

OVERPASS_URL = 'https://overpass-api.de/api/interpreter'

DEFAULT_BOUNDING_BOXES = (
    BoundingBox(52, 7, 55, 10),  # Lower Saxony
    BoundingBox(48, 10, 50, 12),  # Nuremberg
    BoundingBox(51, -1, 53, 1),  # London
    BoundingBox(47, 2, 49, 4),  # Paris
    BoundingBox(49, 14, 51, 16),  # Praha
    BoundingBox(40, -5, 42, -3),  # Madrid
    BoundingBox(58, 17, 60, 19),  # Stockholm
    BoundingBox(56, 23, 58, 25),  # Riga
    BoundingBox(51, 20, 53, 22),  # Warsaw
    BoundingBox(44, 25, 46, 27),  # Bucharest
    BoundingBox(45, 8, 47, 10),  # Milan
    BoundingBox(47, 18, 49, 20),  # Budapest
    BoundingBox(59, 24, 61, 26),  # Helsinki
    BoundingBox(-25, -48, -23, -46),  # São Paulo
)

AREA_TEMPLATE = jinja2.Template("""
[bbox:{{ bbox.lat_start }},{{ bbox.lon_start }},{{ bbox.lat_end }},{{ bbox.lon_end }}]
[out:json];
(
  rel["type"="boundary"]["name"];
  rel["admin_level"]["name"];
);
out tags;
""")

POI_TEMPLATE = jinja2.Template("""
[bbox:{{ bbox.lat_start }},{{ bbox.lon_start }},{{ bbox.lat_end }},{{ bbox.lon_end }}]
[out:json];
(
  nwr["amenity"]["name"];
  nwr["landuse"]["name"];
  nwr["shop"]["name"];
  nwr["tourism"]["name"];
);
out tags;
""")


def get_names(template=AREA_TEMPLATE, bounding_boxes=DEFAULT_BOUNDING_BOXES,
              url=OVERPASS_URL):
    areas = set()
    for bbox in bounding_boxes:
        query = template.render(bbox=bbox)
        resp = requests.post(url, data=query)
        if resp.status_code == 200:
            j = resp.json()
            areas.update({element['tags']['name'] for element in j['elements']})
        else:
            print('Error: {resp.status_code}\n{resp.text}'.format(resp=resp),
                  file=sys.stderr)

    return areas


def main(action):
    if action == 'areas':
        for area in sorted(get_names(template=AREA_TEMPLATE)):
            print(area)
    elif action == 'pois':
        for poi in sorted(get_names(template=POI_TEMPLATE)):
            print(poi)


def parse_args():
    description = 'Retrieve area or POI names from OpenStreetMap'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('action', choices=['areas', 'pois'])
    return parser.parse_args()


if __name__ == '__main__':
    ARGS = parse_args()
    main(**vars(ARGS))
