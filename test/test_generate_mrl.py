from nlmaps_tools.generate_mrl import (render_nwr,)

from .queries import QUERIES

def test_render_nwr():
    assert render_nwr(
        [('name', 'Springmorgen')]
    ) == "keyval('name','Springmorgen')"

    assert render_nwr(
        [('name', "Rue d'Auvours")]
    ) == "keyval('name','Rue d\\'Auvours')"

    assert render_nwr(
        [('amenity', 'place_of_worship'), ('denomination', 'catholic')]
    ) == "keyval('amenity','place_of_worship'),keyval('denomination','catholic')"

    assert render_nwr(
        [('and', ('shop', 'bakery'), ('shop', 'butcher'))]
    ) == "and(keyval('shop','bakery'),keyval('shop','butcher'))"

    assert render_nwr(
        [('amenity', 'restaurant'), ('cuisine', ('or', 'greek', 'italian'))]
    ) == "keyval('amenity','restaurant'),keyval('cuisine',or('greek','italian'))"
