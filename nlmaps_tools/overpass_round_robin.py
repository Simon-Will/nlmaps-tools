import random
import logging
import traceback

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
        tries = kwargs.pop('tries', 2)
        while tries > 0:
            tries -= 1
            overpass = self._get_instance()
            logging.info('Using Overpass at {}'.format(overpass._endpoint))
            try:
                result = overpass.query(*args, **kwargs)
                return result
            except Exception as e:
                logging.error('Error when querying {}:'
                              .format(overpass._endpoint))
                logging.error(traceback.format_exc())
                if tries > 0:
                    logging.info('Trying again.')
                else:
                    raise e
