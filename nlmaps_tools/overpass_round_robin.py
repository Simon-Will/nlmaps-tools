import random
import logging

from OSMPythonTools.overpass import Overpass

DEFAULT_ENDPOINTS = (
    'https://lz4.overpass-api.de/api/',
    'https://z.overpass-api.de/api/',
    'https://overpass.openstreetmap.ru/api/',
    'https://overpass.openstreetmap.fr/api/',
    'https://overpass.kumi.systems/api/',
)


class OverpassRoundRobin:

    def __init__(self, endpoints=DEFAULT_ENDPOINTS, **kwargs):
        self.overpass_instances = [
            Overpass(endpoint=endpoint, **kwargs)
            for endpoint in endpoints
        ]
        self.current_instance_idx = random.randint(
            0, len(self.overpass_instances) - 1)

    def _get_instance(self):
        instance = self.overpass_instances[self.current_instance_idx]
        if self.current_instance_idx < len(self.overpass_instances) - 1:
            self.current_instance_idx += 1
        else:
            self.current_instance_idx = 0
        return instance

    def query(self, *args, **kwargs):
        overpass = self._get_instance()
        logging.info('Using Overpass at {}'.format(overpass._endpoint))
        return overpass.query(*args, **kwargs)
